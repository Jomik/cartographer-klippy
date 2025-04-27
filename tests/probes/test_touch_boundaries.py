from __future__ import annotations

from dataclasses import dataclass

from cartographer.probe.touch_mode import TouchBoundaries


@dataclass
class Configuration:
    mesh_min: tuple[float, float]
    mesh_max: tuple[float, float]
    x_offset: float
    y_offset: float

    move_speed: float = 10
    touch_samples: int = 3
    touch_max_samples: int = 10


def test_is_within_bounds():
    bounds = TouchBoundaries(min_x=10.0, max_x=20.0, min_y=5.0, max_y=15.0)

    # Test points clearly within bounds
    assert bounds.is_within(x=15.0, y=10.0) is True
    assert bounds.is_within(x=10.0, y=5.0) is True  # On lower bounds
    assert bounds.is_within(x=20.0, y=15.0) is True  # On upper bounds

    # Test points clearly outside bounds (beyond 0.01 tolerance)
    assert bounds.is_within(x=9.98, y=10.0) is False  # Left of min_x (outside epsilon)
    assert bounds.is_within(x=20.02, y=10.0) is False  # Right of max_x (outside epsilon)
    assert bounds.is_within(x=15.0, y=4.98) is False  # Below min_y (outside epsilon)
    assert bounds.is_within(x=15.0, y=15.02) is False  # Above max_y (outside epsilon)

    # Test points near boundary (within 0.01 tolerance)
    assert bounds.is_within(x=9.99, y=10.0) is True  # Just left of min_x (within epsilon)
    assert bounds.is_within(x=20.01, y=10.0) is True  # Just right of max_x (within epsilon)
    assert bounds.is_within(x=15.0, y=4.99) is True  # Just below min_y (within epsilon)
    assert bounds.is_within(x=15.0, y=15.01) is True  # Just above max_y (within epsilon)


def test_from_config():
    # Test with zero offsets
    config = Configuration(mesh_min=(0.0, 0.0), mesh_max=(100.0, 100.0), x_offset=0.0, y_offset=0.0)
    bounds = TouchBoundaries.from_config(config)
    assert bounds == TouchBoundaries(min_x=0.0, max_x=100.0, min_y=0.0, max_y=100.0)

    # Test with positive offsets
    config = Configuration(mesh_min=(0.0, 0.0), mesh_max=(100.0, 100.0), x_offset=10.0, y_offset=5.0)
    bounds = TouchBoundaries.from_config(config)
    assert bounds == TouchBoundaries(min_x=0.0, max_x=90.0, min_y=0.0, max_y=95.0)

    # Test with negative offsets
    config = Configuration(mesh_min=(0.0, 0.0), mesh_max=(100.0, 100.0), x_offset=-10.0, y_offset=-5.0)
    bounds = TouchBoundaries.from_config(config)
    assert bounds == TouchBoundaries(min_x=10.0, max_x=100.0, min_y=5.0, max_y=100.0)

    # Test with non-zero mesh_min
    config = Configuration(mesh_min=(10.0, 20.0), mesh_max=(100.0, 100.0), x_offset=5.0, y_offset=10.0)
    bounds = TouchBoundaries.from_config(config)
    assert bounds == TouchBoundaries(min_x=10.0, max_x=95.0, min_y=20.0, max_y=90.0)

    config = Configuration(mesh_min=(10.0, 10.0), mesh_max=(30.0, 30.0), x_offset=20, y_offset=20)
    bounds = TouchBoundaries.from_config(config)

    assert bounds.is_within(x=20.0, y=20.0) is False
