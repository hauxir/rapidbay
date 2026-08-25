"""Regression tests for the static-file containment check.

uvicorn percent-decodes the request path before routing, so `/%2Fetc%2Fpasswd`
reaches the catch-all frontend route as the absolute path `/etc/passwd`, and
`os.path.join` silently drops the FRONTEND_DIR prefix.
"""

import os

from app.app import _resolve_within


def test_relative_paths_resolve(tmp_path):
    (tmp_path / "lib").mkdir()
    (tmp_path / "app.js").write_text("x")
    (tmp_path / "lib" / "a.js").write_text("y")

    assert _resolve_within(str(tmp_path), "app.js") == str(tmp_path / "app.js")
    assert _resolve_within(str(tmp_path), "lib/a.js") == str(tmp_path / "lib" / "a.js")
    assert _resolve_within(str(tmp_path), "lib/../app.js") == str(tmp_path / "app.js")


def test_absolute_and_traversing_paths_are_rejected(tmp_path):
    for path in ["/etc/passwd", "../../etc/passwd", "..", "lib/../../etc/passwd"]:
        assert _resolve_within(str(tmp_path), path) is None, path


def test_symlink_escape_is_rejected(tmp_path):
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "secret").write_text("s")
    root = tmp_path / "root"
    root.mkdir()
    os.symlink(str(outside), str(root / "link"))

    assert _resolve_within(str(root), "link/secret") is None
