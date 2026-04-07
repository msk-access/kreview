---
description: Version bump, test, and publish kreview
---

# /release

## Steps

1. **Run pre-release checks**:
   ```bash
   nbdev-prepare   # export + test + clean notebooks
   ```

2. **Bump version** in `settings.ini` and `pyproject.toml`

3. **Update CHANGELOG.md**

4. **Commit and tag**:
   ```bash
   git add -A
   git commit -m "release: vX.Y.Z"
   git tag vX.Y.Z
   git push origin main --tags
   ```

5. **Publish** (optional):
   ```bash
   nbdev-pypi
   ```
