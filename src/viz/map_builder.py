"""Interactive Folium map: risk-colored boundary choropleth + change
polygons + a legend, saved as a standalone HTML file (no server required).
"""

from pathlib import Path

import folium
import geopandas as gpd

from src.utils.geo_utils import to_wgs84

_RISK_COLORS = {
    "Low": "#16a34a",
    "Medium": "#ca8a04",
    "High": "#ea580c",
    "Very High": "#dc2626",
}
_DEFAULT_COLOR = "#6b7280"  # no risk data for this zone yet

_LEGEND_HTML = """
<div style="
    position: fixed; bottom: 30px; left: 30px; z-index: 9999;
    background: white; padding: 10px 14px; border-radius: 6px;
    box-shadow: 0 1px 4px rgba(0,0,0,0.3); font-family: sans-serif; font-size: 13px;">
  <div style="font-weight: 600; margin-bottom: 6px;">Disaster risk</div>
  {rows}
</div>
"""
_LEGEND_ROW = (
    '<div style="display:flex; align-items:center; margin:2px 0;">'
    '<span style="width:12px; height:12px; background:{color}; display:inline-block; '
    'margin-right:6px; border-radius:2px;"></span>{label}</div>'
)


def _risk_color(risk_class: str | None) -> str:
    return _RISK_COLORS.get(risk_class, _DEFAULT_COLOR)


def build_interactive_map(
    boundary: gpd.GeoDataFrame,
    change_polygons_path: str | None,
    risk_by_zone: dict[str, dict],
    out_path: str,
) -> str:
    boundary_wgs84 = to_wgs84(boundary)
    centroid = boundary_wgs84.geometry.union_all().centroid
    fmap = folium.Map(location=[centroid.y, centroid.x], zoom_start=12, tiles="CartoDB positron")

    for _, row in boundary_wgs84.iterrows():
        zone_name = row.get("name", "unknown")
        risk = risk_by_zone.get(zone_name)
        color = _risk_color(risk["risk_class"] if risk else None)

        if risk:
            contributions = "".join(
                f"<div>{feat}: {val:.1f}</div>" for feat, val in risk["contributions"].items()
            )
            popup_html = (
                f"<b>{zone_name}</b><br>"
                f"Risk: <b>{risk['risk_class']}</b> ({risk['risk_score']:.1f}/100)"
                f"<br><small>{contributions}</small>"
            )
        else:
            popup_html = f"<b>{zone_name}</b><br>(no risk data)"

        folium.GeoJson(
            row.geometry,
            name="boundary",
            style_function=lambda _f, c=color: {"color": c, "weight": 2, "fillColor": c, "fillOpacity": 0.35},
            highlight_function=lambda _f: {"weight": 3, "fillOpacity": 0.5},
            tooltip=zone_name,
            popup=folium.Popup(popup_html, max_width=300),
        ).add_to(fmap)

    if change_polygons_path and Path(change_polygons_path).exists():
        change_gdf = to_wgs84(gpd.read_file(change_polygons_path))
        if not change_gdf.empty:
            folium.GeoJson(
                change_gdf,
                name="forest loss",
                style_function=lambda _f: {"color": "#1f2937", "weight": 0, "fillColor": "#1f2937", "fillOpacity": 0.6},
            ).add_to(fmap)

    legend_rows = "".join(_LEGEND_ROW.format(color=c, label=label) for label, c in _RISK_COLORS.items())
    fmap.get_root().html.add_child(folium.Element(_LEGEND_HTML.format(rows=legend_rows)))

    folium.LayerControl().add_to(fmap)
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    fmap.save(out_path)
    return out_path
