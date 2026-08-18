"""SQLAlchemy + GeoAlchemy2 models for PostGIS-backed storage. See plan.md
section 9 for the full data-model rationale.
"""

import uuid
from datetime import datetime

from geoalchemy2 import Geometry
from pgvector.sqlalchemy import Vector
from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

# Dimension of sentence-transformers/all-MiniLM-L6-v2 (see src/rag/embeddings.py).
EMBEDDING_DIM = 384


class Base(DeclarativeBase):
    pass


class AdminBoundary(Base):
    __tablename__ = "admin_boundaries"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    gadm_uid: Mapped[str] = mapped_column(String, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    name_normalized: Mapped[str] = mapped_column(String, nullable=False, index=True)
    admin_level: Mapped[int] = mapped_column(Integer, nullable=False)
    parent_name: Mapped[str | None] = mapped_column(String, nullable=True)
    geom = mapped_column(Geometry(geometry_type="MULTIPOLYGON", srid=4326), nullable=False)


class RasterCacheIndex(Base):
    __tablename__ = "raster_cache_index"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    dataset_id: Mapped[str] = mapped_column(String, nullable=False)
    aoi_hash: Mapped[str] = mapped_column(String, nullable=False, index=True)
    date_start: Mapped[str] = mapped_column(String, nullable=False)
    date_end: Mapped[str] = mapped_column(String, nullable=False)
    resolution_m: Mapped[float | None] = mapped_column(Float, nullable=True)
    file_path: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class VectorCacheIndex(Base):
    __tablename__ = "vector_cache_index"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source: Mapped[str] = mapped_column(String, nullable=False)
    aoi_hash: Mapped[str] = mapped_column(String, nullable=False, index=True)
    file_path: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class GisResultRow(Base):
    __tablename__ = "gis_results"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    zone_name: Mapped[str] = mapped_column(String, nullable=False)
    forest_loss_ha: Mapped[float] = mapped_column(Float, nullable=False)
    forest_loss_pct: Mapped[float] = mapped_column(Float, nullable=False)
    landcover_stats_json: Mapped[dict] = mapped_column(JSON, default=dict)
    computed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class RiskResultRow(Base):
    __tablename__ = "risk_results"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    zone_name: Mapped[str] = mapped_column(String, nullable=False)
    risk_score: Mapped[float] = mapped_column(Float, nullable=False)
    risk_class: Mapped[str] = mapped_column(String, nullable=False)
    feature_contributions_json: Mapped[dict] = mapped_column(JSON, default=dict)
    model_version: Mapped[str] = mapped_column(String, nullable=False)


class JobHistory(Base):
    __tablename__ = "job_history"

    id: Mapped[str] = mapped_column(String, primary_key=True)  # job_id (uuid string)
    raw_query: Mapped[str] = mapped_column(Text, nullable=False)
    parsed_intent_json: Mapped[dict] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String, default="parsing")
    report_path: Mapped[str | None] = mapped_column(String, nullable=True)
    map_paths_json: Mapped[dict] = mapped_column(JSON, default=dict)
    errors_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class RagDocument(Base):
    __tablename__ = "rag_documents"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_title: Mapped[str] = mapped_column(String, nullable=False)
    source_type: Mapped[str] = mapped_column(String, nullable=False)
    ingested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class RagChunk(Base):
    __tablename__ = "rag_chunks"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("rag_documents.id"), nullable=False
    )
    chunk_text: Mapped[str] = mapped_column(Text, nullable=False)
    embedding = mapped_column(Vector(EMBEDDING_DIM), nullable=False)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
