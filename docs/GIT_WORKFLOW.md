# Git Workflow

Remote repository: `https://github.com/Atharva322/ReconAI.git`

## Rule

Work locally first. Push to GitHub only after the relevant output/functionality has been tested.

## Default Cadence

1. Make the smallest coherent local change.
2. Run the matching verification:
   - docs-only changes: confirm files render/read cleanly;
   - domain changes: run unit tests;
   - API/UI changes: run local app checks and relevant tests;
   - benchmark changes: regenerate/validate expected outputs.
3. Commit locally with a specific message.
4. Push to `origin/main` only after tests/checks pass.
5. If a check cannot be run, record that before pushing.

## Current Policy

Do not push unfinished or untested work to the remote. Local commits are acceptable after the change has been checked.
