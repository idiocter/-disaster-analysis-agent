"""Phase 3 CLI: creates all PostGIS-backed tables (admin_boundaries,
raster_cache_index, vector_cache_index, gis_results, risk_results,
job_history, rag_documents, rag_chunks) via SQLAlchemy metadata.

Usage:
    uv run python scripts/init_postgis_schema.py
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.data.models import Base  # noqa: E402
from src.data.postgis_repo import engine  # noqa: E402


async def main() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("schema created")


if __name__ == "__main__":
    asyncio.run(main())
