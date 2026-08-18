"""Content-hash based local raster cache. PostGIS's raster_cache_index
table is the source of truth for "what have we already fetched" -- disk is
just blob storage; a cache hit requires both the DB row AND the file to
still exist.
"""

import hashlib
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from src.config import settings
from src.data.postgis_repo import lookup_raster_cache, record_raster_cache


def aoi_hash(bounds: tuple[float, float, float, float]) -> str:
    key = ",".join(f"{v:.6f}" for v in bounds)
    return hashlib.sha256(key.encode()).hexdigest()[:16]


def cache_file_path(
    dataset_id: str, bounds: tuple[float, float, float, float], date_start: str, date_end: str
) -> str:
    safe_dataset = dataset_id.replace("/", "_")
    key = aoi_hash(bounds)
    return f"{settings.data_cache_dir}/{safe_dataset}_{key}_{date_start}_{date_end}.tif"


async def get_cached_raster(
    session: AsyncSession,
    *,
    dataset_id: str,
    bounds: tuple[float, float, float, float],
    date_start: str,
    date_end: str,
) -> str | None:
    row = await lookup_raster_cache(
        session,
        dataset_id=dataset_id,
        aoi_hash=aoi_hash(bounds),
        date_start=date_start,
        date_end=date_end,
    )
    if row is not None and Path(row.file_path).exists():
        return row.file_path
    return None


async def cache_raster(
    session: AsyncSession,
    *,
    dataset_id: str,
    bounds: tuple[float, float, float, float],
    date_start: str,
    date_end: str,
    resolution_m: float,
    file_path: str,
) -> None:
    await record_raster_cache(
        session,
        dataset_id=dataset_id,
        aoi_hash=aoi_hash(bounds),
        date_start=date_start,
        date_end=date_end,
        resolution_m=resolution_m,
        file_path=file_path,
    )
