"""DB access layer (SQLAlchemy + GeoAlchemy2) for all PostGIS tables --
engine/session factory plus CRUD helpers used by boundary_resolver.py,
the GEE caching layer, and the risk/report nodes.
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from src.config import settings
from src.data.models import (
    AdminBoundary,
    GisResultRow,
    JobHistory,
    RasterCacheIndex,
    RiskResultRow,
)

# NullPool: avoids the asyncpg "another operation is in progress" class of
# bug that shows up when a pooled connection is reused across event loop
# instances (e.g. under pytest-asyncio). Negligible cost at this project's
# scale (a handful of jobs at a time).
engine = create_async_engine(settings.database_url, echo=False, poolclass=NullPool)
async_session_factory = async_sessionmaker(engine, expire_on_commit=False)


# --- Admin boundaries ---


async def insert_boundary(
    session: AsyncSession,
    *,
    gadm_uid: str,
    name: str,
    name_normalized: str,
    admin_level: int,
    parent_name: str | None,
    geometry,
) -> AdminBoundary:
    from geoalchemy2.shape import from_shape

    boundary = AdminBoundary(
        gadm_uid=gadm_uid,
        name=name,
        name_normalized=name_normalized,
        admin_level=admin_level,
        parent_name=parent_name,
        geom=from_shape(geometry, srid=4326),
    )
    session.add(boundary)
    await session.commit()
    await session.refresh(boundary)
    return boundary


async def exact_match_boundaries(session: AsyncSession, name_normalized: str) -> list[AdminBoundary]:
    """Returns ALL rows matching the normalized name, not just the first --
    Nepal has real same-name-different-district collisions (see
    boundary_resolver.py), so callers must be able to detect ambiguity even
    on an "exact" name match, not only on fuzzy matches.
    """
    result = await session.execute(
        select(AdminBoundary).where(AdminBoundary.name_normalized == name_normalized)
    )
    return list(result.scalars().all())


async def all_boundaries(session: AsyncSession, admin_level: int | None = None) -> list[AdminBoundary]:
    query = select(AdminBoundary)
    if admin_level is not None:
        query = query.where(AdminBoundary.admin_level == admin_level)
    result = await session.execute(query)
    return list(result.scalars().all())


# --- Raster cache ---


async def lookup_raster_cache(
    session: AsyncSession, *, dataset_id: str, aoi_hash: str, date_start: str, date_end: str
) -> RasterCacheIndex | None:
    result = await session.execute(
        select(RasterCacheIndex).where(
            RasterCacheIndex.dataset_id == dataset_id,
            RasterCacheIndex.aoi_hash == aoi_hash,
            RasterCacheIndex.date_start == date_start,
            RasterCacheIndex.date_end == date_end,
        )
    )
    return result.scalars().first()


async def record_raster_cache(
    session: AsyncSession,
    *,
    dataset_id: str,
    aoi_hash: str,
    date_start: str,
    date_end: str,
    resolution_m: float | None,
    file_path: str,
) -> RasterCacheIndex:
    row = RasterCacheIndex(
        dataset_id=dataset_id,
        aoi_hash=aoi_hash,
        date_start=date_start,
        date_end=date_end,
        resolution_m=resolution_m,
        file_path=file_path,
    )
    session.add(row)
    await session.commit()
    await session.refresh(row)
    return row


# --- GIS / risk results ---


async def record_gis_result(
    session: AsyncSession,
    *,
    job_id: str,
    zone_name: str,
    forest_loss_ha: float,
    forest_loss_pct: float,
    landcover_stats: dict,
) -> GisResultRow:
    row = GisResultRow(
        job_id=job_id,
        zone_name=zone_name,
        forest_loss_ha=forest_loss_ha,
        forest_loss_pct=forest_loss_pct,
        landcover_stats_json=landcover_stats,
    )
    session.add(row)
    await session.commit()
    return row


async def record_risk_result(
    session: AsyncSession,
    *,
    job_id: str,
    zone_name: str,
    risk_score: float,
    risk_class: str,
    contributions: dict,
    model_version: str,
) -> RiskResultRow:
    row = RiskResultRow(
        job_id=job_id,
        zone_name=zone_name,
        risk_score=risk_score,
        risk_class=risk_class,
        feature_contributions_json=contributions,
        model_version=model_version,
    )
    session.add(row)
    await session.commit()
    return row


# --- Job history ---


async def upsert_job_history(session: AsyncSession, job_id: str, **fields) -> JobHistory:
    job = await session.get(JobHistory, job_id)
    if job is None:
        job = JobHistory(id=job_id, raw_query=fields.pop("raw_query", ""), **fields)
        session.add(job)
    else:
        for key, value in fields.items():
            setattr(job, key, value)
    await session.commit()
    await session.refresh(job)
    return job
