#!/usr/bin/env python3
"""Test to validate DEFAULT_SESSION_SETTINGS contains only valid libtorrent settings."""

import libtorrent

from app.torrent import DEFAULT_SESSION_SETTINGS


def test_default_session_settings_valid():
    """Smoke test to ensure all keys in DEFAULT_SESSION_SETTINGS are valid libtorrent settings."""
    settings = libtorrent.session_params()
    try:
        settings.settings = DEFAULT_SESSION_SETTINGS
    except Exception as e:
        raise AssertionError(f"Invalid setting in DEFAULT_SESSION_SETTINGS: {e}") from e


if __name__ == '__main__':
    test_default_session_settings_valid()
    print("✓ All settings in DEFAULT_SESSION_SETTINGS are valid")
