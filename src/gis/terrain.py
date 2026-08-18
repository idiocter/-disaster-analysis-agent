"""Slope derivation from a DEM via the `gdaldem` CLI (part of the
conda-forge `gdal` package already in this project's environment), rather
than a separate richdem dependency -- simpler, one less package, and
gdaldem is already available wherever GDAL is.
"""

import subprocess
from pathlib import Path


def compute_slope_raster(dem_path: str, out_path: str) -> str:
    """Writes a slope-in-degrees raster derived from dem_path to out_path
    and returns out_path. Raises CalledProcessError if gdaldem fails (e.g.
    malformed input) -- callers should let that propagate to their own
    fallible-node error handling rather than silently produce a wrong slope.
    """
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        ["gdaldem", "slope", dem_path, out_path, "-of", "GTiff", "-compute_edges"],
        check=True,
        capture_output=True,
        text=True,
    )
    return out_path
