import json

import _harness


def _write(path, value):
    path.write_text(json.dumps(value), encoding="utf-8")


def test_known_failure_overlays_compose_in_filename_order(tmp_path, monkeypatch):
    baseline = tmp_path / "known_failures.json"
    overlays = tmp_path / "known_failure_overlays"
    overlays.mkdir()
    _write(baseline, {"base reason": ["kept", "removed", "reclassified"]})
    _write(overlays / "02-first.json", {
        "remove": ["removed", "reclassified"],
        "add": {"first reason": ["added", "reclassified"]},
    })
    _write(overlays / "05-last.json", {
        "remove": ["reclassified"],
        "add": {"last reason": ["reclassified"]},
    })
    monkeypatch.setattr(_harness, "KNOWN_FAILURES", baseline)
    monkeypatch.setattr(_harness, "KNOWN_FAILURE_OVERLAYS", overlays)

    assert _harness.load_known_failures() == {
        "kept": "base reason",
        "added": "first reason",
        "reclassified": "last reason",
    }
    assert _harness.load_known_failures(exclude_overlays=("02-first",)) == {
        "kept": "base reason",
        "removed": "base reason",
        "reclassified": "last reason",
    }


def test_duplicate_name_in_one_layer_is_rejected(tmp_path, monkeypatch):
    baseline = tmp_path / "known_failures.json"
    _write(baseline, {"one": ["duplicate"], "two": ["duplicate"]})
    monkeypatch.setattr(_harness, "KNOWN_FAILURES", baseline)
    monkeypatch.setattr(_harness, "KNOWN_FAILURE_OVERLAYS", tmp_path / "missing")

    try:
        _harness.load_known_failures()
    except ValueError as exc:
        assert "duplicate" in str(exc)
    else:
        raise AssertionError("duplicate fixture was accepted")
