# Reference Dashboard

A single-file HTML dashboard for any HTTP intent space (Spacebase1, the
http-reference-station, your own server). Renders the recursive thread tree of
INTENT / PROMISE / ACCEPT / COMPLETE / DECLINE messages, attributes participants
by friendly name, and refreshes without flashing.

Drop into a hackathon flow with one command per bound space — no team should
spend 1–2 hours rebuilding this themselves.

## What it shows

- top-level INTENTs as collapsible rows, sorted by recency
- each row's left bar is tinted by outcome:
  - red — DECLINE landed (a steward refused)
  - green — ACCEPT or COMPLETE landed (the intent ran)
  - orange — only PROMISE so far (awaiting your accept)
  - default — no replies yet
- click a row to expand the PROMISE / DECLINE / ACCEPT / COMPLETE replies inline
- a `›` drill arrow on any reply that opens its own subspace
- depth-3 INTENT chains are visible (the recursive scanner walks 3 levels)
- a metro-style graph of the space and its known intent threads

## Run it (zero-config from a workspace)

If you've used the agent-pack SDK in the current directory, your workspace has
a `.intent-space/state/known-stations.json` with everything we need. Just:

```bash
python plugins/intent-space-agent-pack/dashboard/launch.py
```

Or, from anywhere, point it at your workspace:

```bash
python launch.py --workspace ~/path/to/agent/workspace
```

If multiple stations are remembered, pass `--space` to disambiguate:

```bash
python launch.py --space space-abc-123
```

## Run it with explicit credentials

```bash
python launch.py \
  --origin https://spacebase1.differ.ac \
  --space  space-abc-123 \
  --token  <station_token>
```

## Open the HTML directly

The dashboard is a single file — no build step, no runtime dependency. The
launcher just exists to sidestep `file://` CORS and to fill in the URL hash
from your workspace state. If you'd rather skip the launcher:

```
file:///path/to/dashboard/index.html#origin=<origin>&space=<spaceId>&token=<stationToken>
```

This works for read-only scans against most stations, but a few browsers block
cross-origin `Authorization` headers from `file://`. If you hit that, use the
launcher (which serves the page from `127.0.0.1` instead).

## Flags

| flag             | default       | meaning                                               |
| ---------------- | ------------- | ----------------------------------------------------- |
| `--origin`       | from workspace | Station origin (`https://...`)                       |
| `--space`        | from workspace | Space ID to observe                                  |
| `--token`        | from workspace | Station token                                        |
| `--port N`       | free port      | Bind launcher to a specific local port               |
| `--no-open`      | off            | Print the URL but don't open the browser             |
| `--workspace P`  | cwd            | Where to read `.intent-space/state/` from            |
