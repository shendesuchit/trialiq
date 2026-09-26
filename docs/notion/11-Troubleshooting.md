# Troubleshooting

## Common TrialIQ failure classes

### Stale Python installation

Check where `import trialiq` resolves. Reinstall editable package from the active checkout if needed.

### API alive but not ready

`/health` only means the process is running. Inspect Neo4j, MCP and LLM readiness.

### Neo4j memory during qualification

Use the Batch 21.1 memory-safe qualifier. Do not hide an unbounded query by only raising transaction memory.

### Guided result returns `REVIEW_REQUIRED`

This is expected for more than six candidates. Continue through the HITL endpoint.

### Grounding rejects synthesis claims

This is a protection mechanism. Investigate final contract failure, not the existence of rejection logs alone.

### Git says “not a repository”

Confirm whether commands are being run in the actual Git checkout rather than the runtime copy.

### PowerShell parser issues

Run complete conditional blocks together and prefer ASCII-safe helper scripts for Windows PowerShell 5.1.

### Frontend clean install fails

Check `package.json` / `package-lock.json` consistency before trusting existing `node_modules`.

## Source page

Use repository `docs/12-troubleshooting.md` for the full troubleshooting matrix.
