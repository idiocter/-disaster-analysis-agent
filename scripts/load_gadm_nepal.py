"""Phase 3: loads a small SYNTHETIC set of Nepal-like municipality
boundaries into PostGIS, standing in for the real GADM v4.1 Nepal download
(a large external shapefile asset, not fetched in this build -- see
plan.md's note on data sources). Includes two municipalities with the same
normalized name in different districts specifically to exercise the
ambiguity-detection path in boundary_resolver.py -- a real collision risk
for Nepal post-2017 restructuring, directly relevant to "Madhuban".

Usage:
    uv run python scripts/load_gadm_nepal.py
"""

import asyncio
import sys
from pathlib import Path

from shapely.geometry import box

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.data.postgis_repo import async_session_factory, insert_boundary  # noqa: E402

# (name, district, admin_level, bbox) -- Madhuban's first bbox matches
# tests/fixtures/sample_boundary.geojson's AOI so Phase 1/2 sample-data runs
# stay consistent with the Phase 3 PostGIS-backed boundary.
_SYNTHETIC_MUNICIPALITIES = [
    ("Madhuban", "Saptari", 3, (87.20, 26.60, 87.30, 26.68)),
    ("Madhuban", "Bardiya", 3, (81.30, 28.20, 81.40, 28.28)),  # deliberate name collision
    ("Itahari", "Sunsari", 3, (87.25, 26.63, 87.35, 26.71)),
    ("Butwal", "Rupandehi", 3, (83.42, 27.66, 83.50, 27.74)),
    ("Dhangadhi", "Kailali", 3, (80.55, 28.68, 80.65, 28.76)),
]


async def main() -> None:
    async with async_session_factory() as session:
        for name, district, admin_level, bbox in _SYNTHETIC_MUNICIPALITIES:
            geometry = box(*bbox)
            await insert_boundary(
                session,
                gadm_uid=f"synthetic-{name.lower()}-{district.lower()}",
                name=name,
                name_normalized=name.strip().lower(),
                admin_level=admin_level,
                parent_name=district,
                geometry=geometry,
            )
            print(f"inserted {name} ({district})")


if __name__ == "__main__":
    asyncio.run(main())
