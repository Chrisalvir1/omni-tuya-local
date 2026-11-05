# Omni Tuya Local v1.12.3

Updates CI workflow dependencies and validation matrix:
- Bumps `ruff` to `0.17.4` and `HAP-python` to `5.1.0` in `.github/workflows/validate.yml`.
- Validates CI against Home Assistant Core `2026.10.x` and Python `3.11` to `3.14.2`.
- Robust release workflow publishing with explicit repository scoping.
- Re-verifies `tinytuya==1.20.0` and its full cryptographic dependency tree with 0 known CVEs.
