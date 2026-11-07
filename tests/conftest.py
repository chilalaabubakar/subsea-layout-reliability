import pytest

from layout_rel.config import field_path, load_config, param
from layout_rel.layout import load_field


@pytest.fixture
def cfg():
    return load_config()


@pytest.fixture
def field(cfg):
    return load_field(field_path(cfg), param(cfg, "routing.length_factor"))
