"""Static PNG map for report embedding. contextily basemaps require Web
Mercator (EPSG:3857) -- everything gets reprojected on the way in, separate
from the equal-area CRS used for area calculations elsewhere. Boundary
fill color matches map_builder.py's risk-class palette so the interactive
and static maps read as the same system, not two different designs.
"""

from pathlib import Path

import contextily as cx
import geopandas as gpd
import matplotlib.patches as mpatches
import matplotlib.pyplot as plt

from src.utils.geo_utils import WEB_MERCATOR_CRS

_RISK_COLORS = {
    "Low": "#16a34a",
    "Medium": "#ca8a04",
    "High": "#ea580c",
    "Very High": "#dc2626",
}
_DEFAULT_COLOR = "#6b7280"


def build_static_map(
    boundary: gpd.GeoDataFrame,
    change_polygons_path: str | None,
    out_path: str,
    risk_by_zone: dict[str, dict] | None = None,
) -> str | None:
    boundary_merc = boundary.to_crs(WEB_MERCATOR_CRS)
    risk_by_zone = risk_by_zone or {}

    fig, ax = plt.subplots(figsize=(8, 8))

    for _, row in boundary_merc.iterrows():
        zone_name = row.get("name", "unknown")
        risk = risk_by_zone.get(zone_name)
        color = _RISK_COLORS.get(risk["risk_class"], _DEFAULT_COLOR) if risk else _DEFAULT_COLOR
        gpd.GeoSeries([row.geometry], crs=WEB_MERCATOR_CRS).plot(
            ax=ax, facecolor=color, edgecolor=color, alpha=0.35, linewidth=2
        )

    if change_polygons_path and Path(change_polygons_path).exists():
        change_gdf = gpd.read_file(change_polygons_path).to_crs(WEB_MERCATOR_CRS)
        if not change_gdf.empty:
            change_gdf.plot(ax=ax, color="#1f2937", alpha=0.6)

    try:
        cx.add_basemap(ax, source=cx.providers.CartoDB.Positron)
    except Exception:
        # Basemap tiles require network access; degrade gracefully (boundary
        # + change polygons still render) rather than failing the whole report.
        pass

    if risk_by_zone:
        handles = [
            mpatches.Patch(color=color, label=label, alpha=0.6) for label, color in _RISK_COLORS.items()
        ]
        ax.legend(handles=handles, loc="lower right", fontsize=9, title="Disaster risk")

    ax.set_axis_off()
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return out_path
