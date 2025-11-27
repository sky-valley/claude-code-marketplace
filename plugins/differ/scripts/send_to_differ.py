#!/usr/bin/env python3
"""
Differ Claude Code Plugin - Hook Event Capture Script
Captures hook events and sends them to Differ.app via differ-cli
"""

import sys
import json
import os
import subprocess
import time
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any

MAX_FAILED_FILE_BYTES = 10 * 1024 * 1024  # 10MB rotation threshold
MAX_ROLLED_FILES = 10
FAILED_EVENTS_FILENAME = "failed-events.jsonl"


def get_plugin_version() -> str:
    """
    Read plugin version from plugin.json.

    Returns:
        Plugin semantic version string, or "unknown" if not found
    """
    try:
        script_dir = Path(__file__).parent
        plugin_json = script_dir.parent / ".claude-plugin" / "plugin.json"
        if plugin_json.is_file():
            with open(plugin_json) as f:
                data = json.load(f)
                return data.get("version", "unknown")
    except Exception:
        pass
    return "unknown"


def find_differ_cli() -> Optional[str]:
    """
    Find differ-cli binary in common installation locations.

    Returns:
        Path to differ-cli executable, or None if not found
    """
    # Try project-specific installation first
    project_dir = os.environ.get("CLAUDE_PROJECT_DIR")
    if project_dir:
        # Prioritize debug build (for development)
        debug_cli = Path(project_dir) / ".differ-debug" / "differ-cli"
        if debug_cli.is_file() and os.access(debug_cli, os.X_OK):
            return str(debug_cli)

        # Fall back to release build
        project_cli = Path(project_dir) / ".differ" / "differ-cli"
        if project_cli.is_file() and os.access(project_cli, os.X_OK):
            return str(project_cli)

    # Try common installation locations
    common_paths = [
        Path.home() / ".differ" / "bin" / "differ-cli",
        Path("/usr/local/bin/differ-cli"),
        Path("/opt/homebrew/bin/differ-cli"),
    ]

    for cli_path in common_paths:
        if cli_path.is_file() and os.access(cli_path, os.X_OK):
            return str(cli_path)

    return None


def extract_claude_response(transcript_path: str) -> Optional[str]:
    """
    Extract Claude's most recent response from the transcript.

    Args:
        transcript_path: Path to the conversation JSONL file

    Returns:
        Claude's latest response text, or None if not found
    """
    try:
        if not transcript_path or not Path(transcript_path).is_file():
            return None

        # Read the last few lines of the transcript (most recent messages)
        # We only need the latest assistant response
        with open(transcript_path, "r") as f:
            lines = f.readlines()

        # Process lines in reverse to find the most recent assistant message
        for line in reversed(lines[-20:]):  # Check last 20 lines
            try:
                entry = json.loads(line.strip())

                # Look for assistant messages with text content
                if entry.get("type") == "assistant":
                    message = entry.get("message", {})
                    if message.get("role") == "assistant":
                        content_blocks = message.get("content", [])

                        # Collect all text blocks from this response
                        text_parts = []
                        for block in content_blocks:
                            if block.get("type") == "text":
                                text_parts.append(block.get("text", ""))

                        # Return the combined text if we found any
                        if text_parts:
                            return "\n".join(text_parts)

            except json.JSONDecodeError:
                continue

        return None

    except Exception:
        # Silently fail if transcript reading fails (non-blocking)
        return None


def build_payload(hook_input: Dict[str, Any]) -> Dict[str, Any]:
    """
    Build HookData payload matching WireProtocol.swift structure.

    Args:
        hook_input: Raw JSON input from Claude Code hook

    Returns:
        Formatted payload ready to send to differ-cli
    """
    hook_event = hook_input.get("hook_event_name", "unknown")

    # Base payload with common fields
    payload = {
        "version": "1.0.0",
        "plugin_version": get_plugin_version(),
        "session_id": hook_input.get("session_id", "unknown"),
        "hook_event_name": hook_event,
        "timestamp": time.time(),
        "cwd": hook_input.get("cwd", ""),
        "transcript_path": hook_input.get("transcript_path", ""),
        "permission_mode": hook_input.get("permission_mode", ""),
    }

    # Add event-specific fields based on hook type
    if hook_event in ("PreToolUse", "PostToolUse"):
        payload["tool_name"] = hook_input.get("tool_name")
        payload["tool_input"] = hook_input.get("tool_input")
        if hook_event == "PostToolUse":
            payload["tool_response"] = hook_input.get("tool_response")

    elif hook_event == "UserPromptSubmit":
        payload["prompt"] = hook_input.get("prompt")

    elif hook_event in ("Stop", "SubagentStop"):
        payload["reason"] = hook_input.get("reason")

        # Extract Claude's response from the transcript
        transcript_path = hook_input.get("transcript_path", "")
        claude_response = extract_claude_response(transcript_path)
        if claude_response:
            payload["claude_response"] = claude_response

    elif hook_event == "Notification":
        payload["notification_type"] = hook_input.get("notification_type")
        payload["message"] = hook_input.get("message")

    elif hook_event == "PermissionRequest":
        payload["tool_name"] = hook_input.get("tool_name")
        payload["decision"] = hook_input.get("decision")

    return payload


def roll_failed_events(directory: Path, active_file: Path) -> None:
    """
    Rotate the active failed-events file when it exceeds the size cap and prune old rolls.
    """
    try:
        if not active_file.exists():
            return

        if active_file.stat().st_size < MAX_FAILED_FILE_BYTES:
            return

        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        rolled_file = directory / f"failed-events.{timestamp}.jsonl"

        # Avoid collisions if two rotations happen within the same second
        suffix = 1
        while rolled_file.exists():
            rolled_file = directory / f"failed-events.{timestamp}-{suffix:02d}.jsonl"
            suffix += 1

        active_file.rename(rolled_file)
        prune_rolled_files(directory)
    except Exception:
        # Rotation issues should never block hook capture
        pass


def prune_rolled_files(directory: Path) -> None:
    """
    Keep only the newest MAX_ROLLED_FILES rolled files to cap disk usage.
    """
    try:
        rolled_files = [
            path for path in directory.glob("failed-events.*.jsonl")
            if path.name != FAILED_EVENTS_FILENAME
        ]
        rolled_files.sort(key=lambda p: p.name)

        while len(rolled_files) > MAX_ROLLED_FILES:
            oldest = rolled_files.pop(0)
            try:
                oldest.unlink()
            except FileNotFoundError:
                continue
    except Exception:
        pass


def send_to_differ(payload: Dict[str, Any], differ_cli: str) -> bool:
    """
    Send payload to differ-cli.

    Args:
        payload: JSON payload to send
        differ_cli: Path to differ-cli binary

    Returns:
        True if successful, False otherwise
    """
    try:
        # Convert payload to JSON string
        payload_json = json.dumps(payload)

        # Invoke differ-cli with JSON as positional argument
        result = subprocess.run(
            [differ_cli, "send-event", payload_json],
            capture_output=True,
            text=True,
            timeout=5,
        )

        return result.returncode == 0

    except subprocess.TimeoutExpired:
        print("Differ plugin: differ-cli timed out", file=sys.stderr)
        return False
    except Exception as e:
        print(f"Differ plugin: Error calling differ-cli: {e}", file=sys.stderr)
        return False


def log_failed_event(payload: Dict[str, Any]) -> None:
    """
    Log failed event to .differ/failed-events.jsonl for debugging.

    Args:
        payload: The payload that failed to send
    """
    try:
        project_dir = os.environ.get("CLAUDE_PROJECT_DIR")
        if not project_dir:
            return

        failed_dir = Path(project_dir) / ".differ"
        active_file = failed_dir / FAILED_EVENTS_FILENAME

        # Create .differ directory if it doesn't exist
        failed_dir.mkdir(parents=True, exist_ok=True)

        roll_failed_events(failed_dir, active_file)

        # Append failed event as JSON line
        with open(active_file, "a") as f:
            json.dump(payload, f)
            f.write("\n")

    except Exception:
        # Silently ignore logging failures (non-blocking)
        pass


def main() -> int:
    """
    Main execution function.

    Returns:
        Exit code (always 0 for non-blocking behavior)
    """
    try:
        # Read JSON input from stdin
        hook_input = json.load(sys.stdin)

        # Build the payload
        payload = build_payload(hook_input)

        # Find differ-cli
        differ_cli = find_differ_cli()
        if not differ_cli:
            return 0

        # Send to differ-cli
        if send_to_differ(payload, differ_cli):
            # Success - exit silently
            return 0
        else:
            # Failed to send, but don't block user's workflow
            print("Differ plugin: Failed to send event to differ-cli", file=sys.stderr)
            log_failed_event(payload)
            return 0

    except json.JSONDecodeError as e:
        print(f"Differ plugin: Invalid JSON input: {e}", file=sys.stderr)
        return 0
    except Exception as e:
        print(f"Differ plugin: Unexpected error: {e}", file=sys.stderr)
        return 0


if __name__ == "__main__":
    sys.exit(main())
