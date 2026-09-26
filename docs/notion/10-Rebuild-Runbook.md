# Rebuild Runbook

## Goal

A future maintainer should be able to rebuild TrialIQ from a clean machine rather than relying on hidden local state.

## High-level recovery order

1. Checkout exact TrialIQ release tag/commit.
2. Record toolchain versions.
3. Restore AACT PostgreSQL.
4. Configure `.env`.
5. Recreate Python environment.
6. Start Neo4j.
7. Run bounded canonical verification load.
8. Run full canonical graph load/reconciliation.
9. Install frontend from clean dependency manifests.
10. Start API/frontend.
11. Run readiness + preflight.
12. Run stable-demo release gate.
13. Run four generated UI scenarios and PDF smoke.
14. Record the recovered environment.

## Reproducibility warning

Before a final long-term release tag, reconcile the frontend `package.json` / `package-lock.json` drift and prove `npm ci` + `npm run build` from a clean clone.

## Source page

Use repository `docs/09-rebuild-and-recovery.md` for commands and details.
