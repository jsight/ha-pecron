"""Tests for const module."""

from custom_components.pecron.const import (
    CONF_EMAIL,
    CONF_PASSWORD,
    CONF_REFRESH_INTERVAL,
    CONF_REGION,
    DEFAULT_REFRESH_INTERVAL,
    DEFAULT_REGION,
    DOMAIN,
    REGIONS,
)


def test_domain() -> None:
    """Test domain constant."""
    assert DOMAIN == "pecron"


def test_config_keys() -> None:
    """Test config key constants."""
    assert CONF_EMAIL == "email"
    assert CONF_PASSWORD == "password"
    assert CONF_REGION == "region"
    assert CONF_REFRESH_INTERVAL == "refresh_interval"


def test_defaults() -> None:
    """Test default values."""
    assert DEFAULT_REGION == "US"
    assert DEFAULT_REFRESH_INTERVAL == 600
    assert isinstance(DEFAULT_REFRESH_INTERVAL, int)


def test_regions() -> None:
    """Test region list."""
    assert isinstance(REGIONS, (list, tuple))
    assert len(REGIONS) > 0
