import datetime

import pytest

from modules import versioning


def test_resolve_build_meta_uses_runtime_time_when_git_is_unavailable(monkeypatch):
    fixed_now = datetime.datetime(2026, 8, 13, 12, 34, 56)

    class FakeDateTime(datetime.datetime):
        @classmethod
        def now(cls, tz=None):
            if tz is None:
                return fixed_now
            return fixed_now.replace(tzinfo=tz)

    monkeypatch.setattr(versioning, "_git_revision", lambda: None)
    monkeypatch.setattr(versioning, "_git_commit_timestamp", lambda: None)
    monkeypatch.setattr(versioning, "_read_build_meta", lambda: (fixed_now.timestamp() - 86400.0, 17))
    monkeypatch.setattr(versioning.datetime, "datetime", FakeDateTime)

    timestamp, revision = versioning._resolve_build_meta()

    assert timestamp == pytest.approx(fixed_now.timestamp())
    assert revision == 17
