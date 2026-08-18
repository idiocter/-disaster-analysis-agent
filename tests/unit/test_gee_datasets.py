import pytest

from src.data.gee_datasets import DYNAMIC_WORLD, HANSEN_GFC, select_dataset_for_analysis


def test_forest_loss_always_uses_hansen():
    assert select_dataset_for_analysis("forest_loss", "2005-01-01") is HANSEN_GFC
    assert select_dataset_for_analysis("forest_loss", "2020-01-01") is HANSEN_GFC


def test_land_cover_change_after_2015_uses_dynamic_world():
    assert select_dataset_for_analysis("land_cover_change", "2018-01-01") is DYNAMIC_WORLD


def test_land_cover_change_before_2015_raises_with_explanation():
    with pytest.raises(ValueError, match="Dynamic World only"):
        select_dataset_for_analysis("land_cover_change", "2005-01-01")


def test_unknown_analysis_type_raises():
    with pytest.raises(ValueError, match="unknown analysis_type"):
        select_dataset_for_analysis("something_else", "2020-01-01")
