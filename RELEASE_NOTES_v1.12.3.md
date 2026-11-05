# Omni Tuya Local v1.12.3

Updates CI workflow dependencies and validation matrix:
- Bumps `ruff` to `0.17.4` and `HAP-python` to `5.1.0` in `.github/workflows/validate.yml`.
- Adds Home Assistant Core `2026.11.0` to the automated compatibility test matrix.
- Re-verifies `tinytuya==1.20.0` and its full cryptographic dependency tree with 0 known CVEs.
