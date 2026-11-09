"""Check exact inputs and version edits in the working tree."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys

here = Path(__file__).resolve().parent
evidence = Path("../evidence")
before = json.loads((here / "before.json").read_bytes())
expected = json.loads((here / "expected.json").read_bytes())


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


if sys.argv[1] == "before":
    assert subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip() == "e5aa18b677b7553d8972b71afdff9665f745746e"
    assert all(digest(path) == value for path, value in before.items())
elif sys.argv[1] == "after":
    paths = subprocess.check_output(["git", "diff", "--name-only"], text=True).splitlines()
    assert {path:digest(path) for path in paths} == expected
    files = [{"path":path,"content":Path(path).read_bytes().decode("utf-8")} for path in paths]
    (evidence / "changes.json").write_text(json.dumps({"status":"changes","changes":files}),encoding="utf-8")
    reads = [json.loads(line) for line in Path("feed-reads.jsonl").read_text().splitlines()]
    feeds = json.loads((here / "feeds.json").read_bytes())
    assert set(reads) == {row["url"] for row in feeds.values()}
    (evidence / "feed-reads.json").write_text(json.dumps(reads),encoding="utf-8")
elif sys.argv[1] == "build":
    packages = sorted(path.name for path in Path("artifacts").rglob("*.nupkg"))
    binaries = sorted(path.name for path in Path("artifacts/bin").rglob("*.dll"))
    assert binaries, "No build binaries were produced"
    resolved = {}
    for path in Path(".").rglob("project.assets.json"):
        data = json.loads(path.read_bytes())
        resolved[str(path)] = sorted(data.get("libraries",{}))
    assert resolved, "No build dependency resolution evidence"
    (evidence / "build.json").write_text(json.dumps({"packages":packages,"binaries":binaries,"resolved":resolved}),encoding="utf-8")
