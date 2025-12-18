from __future__ import annotations

"""
Small helper script to export the FastAPI OpenAPI schema to disk.

Usage (from backend/):

  uv run python -m app.openapi_export
"""

from pathlib import Path

from app.main import create_app


def main() -> None:
    app = create_app()
    schema = app.openapi()
    out_path = Path(__file__).resolve().parents[1] / "openapi.json"
    out_path.write_text(
        __import__("json").dumps(schema, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    print(f"Wrote OpenAPI schema to {out_path}")


if __name__ == "__main__":
    main()


