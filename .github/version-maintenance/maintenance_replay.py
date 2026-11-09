"""Use the same recorded NuGet versions for both version update implementations."""
import io
import json
from pathlib import Path
import subprocess
import sys
import urllib.request

from version_maintenance import eligible, run

HERE = Path(__file__).resolve().parent
capture = json.loads((HERE / "feeds.json").read_bytes())
feeds = {row["url"]: row["response"] for row in capture.values()}


def response(url):
    document = feeds[url]
    with open("feed-reads.jsonl", "a", encoding="utf-8") as log:
        log.write(json.dumps(url) + "\n")
    return json.dumps(document, separators=(",", ":")).encode()


def run_original():
    urllib.request.urlopen = lambda url, **_: io.BytesIO(response(url))
    namespace = {}
    source = (HERE / "original_helper.py").read_text(encoding="utf-8")
    exec(compile(source, "original_helper.py", "exec"), namespace)
    for path in sorted(Path("src").rglob("*")):
        if path.is_file() and eligible(path):
            namespace["process"](path, path.parts[1])


def run_script():
    original = subprocess.check_output

    def curl_or_git(command, **kwargs):
        if command[0] == "curl":
            return response(command[-1])
        return original(command, **kwargs)

    subprocess.check_output = curl_or_git
    run(".")


if __name__ == "__main__":
    {"original": run_original, "script": run_script}[sys.argv[1]]()
