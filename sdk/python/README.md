# Python SDK — see repo root `pyproject.toml`

Install from **praam-platform** root with [uv](https://docs.astral.sh/uv/):

```bash
uv sync --all-extras
uv run python -c "from praam_platform import PlatformClient; print(PlatformClient('findoc-ai').load(apply_env=False).database_url)"
```

Legacy pip (optional): `pip install -e ".[api]"` from repo root.

Runtime config via the platform-config API — no `.env.platform.generated` required.
