from src.data.cache import aoi_hash, cache_file_path


def test_aoi_hash_is_deterministic():
    bounds = (87.20, 26.60, 87.30, 26.68)
    assert aoi_hash(bounds) == aoi_hash(bounds)


def test_aoi_hash_differs_for_different_bounds():
    a = aoi_hash((87.20, 26.60, 87.30, 26.68))
    b = aoi_hash((81.30, 28.20, 81.40, 28.28))
    assert a != b


def test_cache_file_path_is_stable_and_sanitizes_dataset_id():
    path = cache_file_path(
        "UMD/hansen/global_forest_change_2023_v1_11", (87.20, 26.60, 87.30, 26.68), "2005-01-01", "2020-12-31"
    )
    assert "/" not in path.split("/")[-1]  # dataset id's slashes replaced, no accidental subpaths
    assert path.endswith(".tif")
    assert "2005-01-01" in path and "2020-12-31" in path
