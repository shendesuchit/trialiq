# TrialIQ Git Workflow

This document defines the standard TrialIQ source-control workflow after the Batch 18 baseline.

## Authoritative locations

- Tested/running working copy: `F:\trialiq`
- GitHub Desktop repository: `F:\github\trialiq\trialiq`
- GitHub remote: `https://github.com/shendesuchit/trialiq.git`

## Protected baseline

- Default stable branch: `main`
- Legacy backup branch: `backup/pre-batch18-old`
- Legacy backup tag: `pre-batch18-old-github`
- Verified Batch 18 tag: `trialiq-batch18-demo-baseline`

`main` should always represent the latest verified stable TrialIQ state.

## Development rule

Never develop directly on `main`.

For each new batch:

```powershell
cd F:\github\trialiq\trialiq

git switch main
git pull origin main

git switch -c batchNN-short-description
```

Example:

```powershell
git switch -c batch19-connections-final-polish
```

## Tested-source rule

Implementation/testing happens in:

```text
F:\trialiq
```

Do not replace this directory during Git operations. Treat it as the current tested working application.

After a batch passes verification, synchronize only source/rebuildable files into:

```text
F:\github\trialiq\trialiq
```

Never copy:

```text
.git/
.env
.venv/
node_modules/
__pycache__/
.pytest_cache/
.pytest-tmp/
build/
dist/
*.pyc
*.log
*.tsbuildinfo
*.patch
combined_files*.txt
*inspection_bundle*.txt
```

Do not copy PostgreSQL or Neo4j physical database files.

## Incremental commit workflow

After synchronizing a verified batch:

```powershell
cd F:\github\trialiq\trialiq

git status --short
git diff --stat
git add -A
git diff --cached --stat
git status
```

Review the staged files before committing.

Then:

```powershell
git commit -m "Batch NN: short description"
git push -u origin batchNN-short-description
```

## Merge into main

Only merge after the batch verification passes.

```powershell
git switch main
git pull origin main

git merge --no-ff batchNN-short-description `
    -m "Merge Batch NN: short description"

git push origin main
```

Do not delete the feature branch immediately if it is useful for audit/history.

## Tagging

Do not tag every small commit.

Create tags for significant verified recovery points only.

Example:

```powershell
git tag -a trialiq-batchNN-demo-baseline `
    -m "Verified TrialIQ Batch NN demo baseline"

git push origin trialiq-batchNN-demo-baseline
```

## Verification before merge

At minimum:

```powershell
cd F:\trialiq

$env:PYTHONPATH = "F:\trialiq\src"
& "F:\trialiq\.venv\Scripts\python.exe" -m pytest -q

cd F:\trialiq\frontend
npm run build
```

Also run the batch-specific verification script when one exists.

Example:

```powershell
cd F:\trialiq

powershell -ExecutionPolicy Bypass `
    -File .\scripts\run_batch19_verification.ps1
```

## Secret/generated-file check

Before every push:

```powershell
git status
git diff --cached
```

Confirm that the following are not staged:

```text
.env
real API keys
PostgreSQL passwords
Neo4j passwords
*.pem
*.key
.venv/
node_modules/
__pycache__/
.pytest-tmp/
build/
dist/
```

## Recovery

To return to the verified Batch 18 baseline:

```powershell
git fetch --all --tags
git checkout trialiq-batch18-demo-baseline
```

To return to the original pre-Batch-18 GitHub state:

```powershell
git checkout pre-batch18-old-github
```

## Standard Batch Pattern

Use this sequence for all future TrialIQ batches:

```text
main
  ↓
create batchNN feature branch
  ↓
implement/test in F:\trialiq
  ↓
batch verification passes
  ↓
sync tested source to GitHub clone
  ↓
review Git diff
  ↓
commit feature branch
  ↓
push feature branch
  ↓
merge into main
  ↓
push main
  ↓
tag only if this is an important recovery/demo baseline
```
