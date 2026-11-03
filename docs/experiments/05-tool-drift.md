# 05 — Tool drift: a changed description and a new tool

**Date:** 2026-11-02 · **Answers:** Q4, Q3 (rest) · **Versions:** Microsoft 365 admin center (Agents → Tools, preview), LiteLLM v1.106.6

## Goal

See whether Agent 365 notices when an approved MCP server changes: a tool's description changes, and a tool is added. Also see how a new tool is treated after the server was blocked and unblocked in [04](04-block-and-allow.md).

## Setup

- The state left by 04: the notes server under an **enforced allowlist** written by Agent 365 (`add_note`, `list_notes`).
- `src/05_tools_seen.py`: the server's tools, with descriptions, in the admin view Agent 365 reads (including disabled tools) and as offered to the team's key.
- `src/04_probe.py drift` ([csv](assets/04-probe-drift.csv)) and `src/04_snapshot.py` ([before](assets/04-snapshot-before-drift.json), [after enabling count_notes](assets/04-snapshot-after-enable-count.json), [after disabling add_note](assets/04-snapshot-after-disable-add.json)).

## Steps

1. Change the server: `list_notes`'s description gets "Changed in experiment 05: also say how many notes you listed."; add a read tool `count_notes`. Deploy (new revision live at 13:58:34 UTC).
2. Compare both views; call `count_notes` with the team's key.
3. In the portal: look at the server, then enable `count_notes` (15:10 local), then disable `add_note` (15:12 local).

## Result

| Time (UTC) | Observed |
|---|---|
| 13:58:34 | new server revision live |
| 14:06 | admin view (Agent 365): `add_note`, `count_notes`, `list_notes` with the **new** description; team's key: `add_note`, `list_notes` with the **new** description; `count_notes` called with the team's key → 403 "Tool count_notes is not allowed for server notes" |
| portal | `count_notes` listed with its toggle **disabled**; `list_notes` shows the new description |
| 14:09:26.4 | enabling `count_notes` saved ("Changes saved."): `allowed_tools` → `add_note`, `list_notes`, `count_notes` (by `agent365`) |
| 14:09:34 | probe: the team's key is offered `notes-count_notes` |
| 14:12:38.5 | disabling `add_note` saved: `allowed_tools` → `list_notes`, `count_notes` (by `agent365`) |
| 14:12:44 | probe: the team's key no longer has `notes-add_note` |

## Conclusion

- **Q4 (drift):** a changed tool description reaches every client at once, and Agent 365 shows the new text. A **new tool** follows the enforced allowlist: once Agent 365 has blocked and unblocked a server, LiteLLM enforces the allowlist it wrote, so a tool added later is refused (403) until an admin enables it; on a server Agent 365 never blocked, a new tool would be available at once (no allowlist enforced).
- **Q3 (granularity), completed:** per-tool toggles apply within seconds (enable 8 s, disable 6 s) once the server is under an enforced allowlist; on a server LiteLLM treats as "all tools allowed" (an empty, unenforced list, as in 04) saving a toggle sent no write. Practical rule: block and unblock a server once to put it under Agent 365's tool control; every tool added afterwards then needs an explicit allow.
