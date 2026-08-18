import geopandas as gpd
from shapely.geometry import box

from src.viz.map_builder import _risk_color, build_interactive_map


def test_risk_color_maps_known_classes():
    assert _risk_color("Low") == "#16a34a"
    assert _risk_color("Very High") == "#dc2626"


def test_risk_color_defaults_for_unknown_or_missing():
    assert _risk_color(None) == "#6b7280"
    assert _risk_color("Nonsense") == "#6b7280"


def test_build_interactive_map_includes_legend_and_risk_popup(tmp_path):
    boundary = gpd.GeoDataFrame(
        [{"name": "TestZone", "geometry": box(87.2, 26.6, 87.3, 26.68)}], crs="EPSG:4326"
    )
    risk_by_zone = {
        "TestZone": {
            "zone_name": "TestZone",
            "risk_score": 62.0,
            "risk_class": "High",
            "contributions": {"forest_loss_pct": 20.0, "mean_slope_deg": 15.0, "rainfall_intensity_norm": 12.0},
        }
    }
    out_path = str(tmp_path / "map.html")

    result = build_interactive_map(boundary, None, risk_by_zone, out_path)

    html = open(result).read()
    assert "Disaster risk" in html  # legend present
    assert "High" in html
    assert "#ea580c" in html  # High's fill color, used for both the zone and the legend swatch
