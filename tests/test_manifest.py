import hashlib
import json

from elective_wait.runtime import MANIFEST, REPO


def test_snapshot_manifest_matches_files():
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert manifest["access_date"] == "2026-11-08"
    assert len(manifest["files"]) == 3
    for item in manifest["files"]:
        path = REPO / item["path"]
        assert path.exists()
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        assert digest == item["sha256"]
        assert item["rows"] > 0
        assert item["licence"] == "CC BY 4.0"
