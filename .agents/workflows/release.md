---
description: PR-driven Version bump, test, format, and publish workflow
---

# /release

This project strictly utilizes a PR-driven **Git Flow**. Direct merging to `main` is prohibited to ensure GitHub Actions triggers properly against testing environments.

## Steps

1. **Initialize Release Branch**:
   ```bash
   git checkout develop
   git pull origin develop
   git checkout -b release/vX.Y.Z
   ```

2. **The Triple Bump (Configuration Sync)**:
   - Bump version identically in `settings.ini`
   - Bump version identically in `nextflow/nextflow.config`
   - Bump version identically in `kreview/__init__.py`

3. **Nbdev Engine Sync**:
   Execute export *after* bumping `settings.ini` to allow dynamic `__init__.py` hook propagation:
   ```bash
   nbdev_clean
   nbdev_export
   ```

4. **Formatting Compliance**:
   Execute standard black formatting globally across both source notebooks and generated `.py` codebase:
   ```bash
   python -m black .
   ```

5. **Changelog Bridge**:
   - Update `CHANGELOG.md` with release notes.
   - Synchronize Mkdocs:
     ```bash
     cp CHANGELOG.md docs/changelog.md
     ```

6. **Publish to Release Branch**:
   ```bash
   git add -A
   git commit -m "release: vX.Y.Z"
   git push origin release/vX.Y.Z
   ```

7. **Production PR Sequence & Tagging**:
   - Open Pull Request: `release/vX.Y.Z` -> `main`
   - **Wait** for GH Actions Pipeline and Code Review.
   - Once merged:
     ```bash
     git checkout main
     git pull origin main
     git tag vX.Y.Z
     git push origin vX.Y.Z --no-verify
     ```

8. **Back-merge**:
   - Open a final PR mapping `main` back into `develop` natively.
