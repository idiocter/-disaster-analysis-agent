"""Dataset registry: maps analysis needs to real Earth Engine asset IDs,
bands, and valid date ranges. Centralizing this here means gee_client.py
just looks up what it needs rather than hardcoding asset strings inline.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class GeeDataset:
    asset_id: str
    band: str
    valid_from: str  # ISO date
    valid_to: str | None  # None = ongoing
    native_resolution_m: float
    description: str


# Hansen needs two bands read together: lossyear says *when* a pixel was
# cleared, treecover2000 establishes what counted as forest to begin with.
HANSEN_TREECOVER_BAND = "treecover2000"

HANSEN_GFC = GeeDataset(
    asset_id="UMD/hansen/global_forest_change_2023_v1_11",
    band="lossyear",
    valid_from="2000-01-01",
    valid_to=None,
    native_resolution_m=30.0,
    description=(
        "Hansen Global Forest Change -- per-pixel year of forest loss, 2000-present. "
        "Authoritative source for forest-loss-specific queries."
    ),
)

DYNAMIC_WORLD = GeeDataset(
    asset_id="GOOGLE/DYNAMICWORLD/V1",
    band="label",
    valid_from="2015-06-27",
    valid_to=None,
    native_resolution_m=10.0,
    description=(
        "Near-real-time 10-class land cover, available from mid-2015 onward. Not reliable "
        "for date ranges starting before ~2015 -- see select_dataset_for_analysis."
    ),
)

ESA_WORLDCOVER = GeeDataset(
    asset_id="ESA/WorldCover/v200",
    band="Map",
    valid_from="2021-01-01",
    valid_to="2021-12-31",
    native_resolution_m=10.0,
    description="Single-year (2021) global land-cover map, 11 classes.",
)

SRTM_DEM = GeeDataset(
    asset_id="USGS/SRTMGL1_003",
    band="elevation",
    valid_from="2000-02-11",
    valid_to="2000-02-22",
    native_resolution_m=30.0,
    description="SRTM 30m digital elevation model -- static, used for slope derivation.",
)

CHIRPS_RAINFALL = GeeDataset(
    asset_id="UCSB-CHG/CHIRPS/DAILY",
    band="precipitation",
    valid_from="1981-01-01",
    valid_to=None,
    native_resolution_m=5566.0,  # ~0.05 degree
    description="Daily precipitation estimates, 1981-present.",
)


def select_dataset_for_analysis(analysis_type: str, date_start: str) -> GeeDataset:
    """Picks the right dataset for the requested analysis, enforcing the
    date-availability constraint explicitly rather than silently returning
    unreliable data -- see plan.md's note on Dynamic World's 2015 cutoff.
    """
    if analysis_type == "forest_loss":
        return HANSEN_GFC
    if analysis_type == "land_cover_change":
        if date_start < DYNAMIC_WORLD.valid_from:
            raise ValueError(
                f"land_cover_change requested from {date_start}, but Dynamic World only "
                f"covers {DYNAMIC_WORLD.valid_from} onward. Hansen Global Forest Change is "
                f"the authoritative source for forest-specific loss before that; general "
                f"land-cover-class comparisons before 2015 aren't reliably available."
            )
        return DYNAMIC_WORLD
    raise ValueError(f"unknown analysis_type: {analysis_type}")
