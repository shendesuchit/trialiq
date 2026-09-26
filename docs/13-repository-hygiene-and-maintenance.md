# TrialIQ Repository Hygiene and Maintenance

## Purpose

This page defines what belongs in the TrialIQ Git repository, what should remain local/generated, and how maintainers should preserve a clean reproducible history.

## Source directories that belong in Git

Typical source-controlled content includes:

```text
frontend/
src/
tests/
scripts/
docs/
.github/
.env.example
.gitignore
compose.yaml
pyproject.toml
requirements.txt
uv.lock
frontend/package.json
frontend/package-lock.json
README.md
```

## Generated content that should not normally be tracked

The current `.gitignore` protects common generated paths such as:

```text
.venv/
__pycache__/
.pytest_cache/
.pytest-cache/
.pytest_tmp/
.pytest-tmp/
.coverage*
htmlcov/
.build_validation/
*.egg-info/
*.whl
frontend/node_modules/
frontend/dist/
frontend/.vite/
data/
artifacts/
*.log
*.tmp
*.patch
*.diff
.env
.env.*
```

`!.env.example` is intentionally allowed.

## Important nuance: qualification reports

`data/` is ignored because it can contain large local datasets and generated outputs. However, selected small release evidence may be worth preserving deliberately.

If a generated profile/report is needed as historical evidence:

1. verify it contains no secrets or large raw source data;
2. decide explicitly that it is release evidence;
3. either force-add that specific file or copy a concise release summary into `docs/`;
4. do not remove the blanket `data/` ignore rule just to preserve one report.

## Cleaning already-tracked generated paths

Ignore rules do not remove files that were committed earlier.

The Batch 21 cleanup script can untrack known generated/cache paths without deleting local copies:

```powershell
.\scripts\cleanup_batch21_repository_hygiene.ps1 -GitRoot F:\github\trialiq\trialiq
```

The operation should use `git rm --cached`, not indiscriminate deletion.

## Runtime copy vs Git checkout

During development, TrialIQ has been run from a source/runtime folder and backed up from a separate Git checkout.

Example historical layout:

```text
Runtime working copy: F:\trialiq
Git checkout:         F:\github\trialiq\trialiq
```

Maintainers must know which directory is authoritative before running `git add`, `commit`, `diff` or `push`.

Recommended long-term simplification: run directly from the Git checkout unless there is a deliberate reason to maintain a separate runtime copy.

## Branch discipline

For incremental batches:

1. start from current `main`;
2. create a focused feature/batch branch;
3. apply changes;
4. run the appropriate verification gate;
5. review `git status --short` and staged diff;
6. commit only intended files;
7. push the feature branch;
8. merge to `main` after successful verification;
9. leave `main` clean.

## Safe staging

Prefer explicit file staging for focused patches:

```powershell
git add README.md docs/
```

Avoid `git add -A` when the working tree contains local reports, generated data or unrelated experiments unless you have inspected the entire status first.

## Patch discipline

Patch bundles should contain:

- one patch;
- apply script;
- verify script;
- rollback script;
- concise README/notes.

Portable PowerShell helper scripts should avoid encoding-sensitive punctuation when Windows PowerShell 5.1 is a target.

## Commit messages

Use messages that describe the product/system change rather than the chat session that produced it.

Examples:

```text
Batch 21: qualify and freeze stable demo release
Docs: publish TrialIQ architecture and recovery runbooks
Fix: keep Connections graph counters aligned with visible scope
```

## Release tags

Once clean-clone reproducibility and documentation are verified, create an annotated tag such as:

```text
trialiq-v0.1-demo
```

The tag should point to the exact commit whose README/runbooks and dependency manifests were verified from a clean clone.

## Maintenance rule

Do not let the docs point to one architecture while `main` runs another. Any material change to:

- graph relationship semantics;
- MCP transport policy;
- HITL threshold/contract;
- LLM call contract;
- API endpoints;
- stable-demo qualification;
- rebuild steps;

must update the relevant numbered docs in the same change set.
