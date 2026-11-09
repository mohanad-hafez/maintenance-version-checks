#!/usr/bin/env python3
import json, os, re, urllib.request

NO_INCREMENT = "NO-INCREMENT"

def latest_nuget(pkg):
    url = f"https://api.nuget.org/v3-flatcontainer/{pkg.lower()}/index.json"
    try:
        with urllib.request.urlopen(url, timeout=30) as r:
            vers = json.loads(r.read()).get("versions", [])
        stable = [v for v in vers if "-" not in v]
        return stable[-1] if stable else None
    except Exception:
        return None

def bump_patch(v):
    p = v.split(".")
    if len(p) >= 3:
        p[2] = str(int(p[2]) + 1)
    return ".".join(p)

RE_BASELINE = re.compile(
    r"^(?P<pre>\s*<PackageValidationBaselineVersion>)"
    r"(?P<ver>[^<]+)"
    r"(?P<post></PackageValidationBaselineVersion>.*)$")
RE_PACKABLE = re.compile(
    r"^(?P<pre>\s*<IsPackable>)true(?P<post></IsPackable>.*)$")
RE_VERPREFIX = re.compile(
    r"^(?P<pre>\s*<VersionPrefix[^>]*>)"
    r"(?P<ver>\d+\.\d+\.\d+)"
    r"(?P<post></VersionPrefix>.*)$")
RE_ASMVER = re.compile(
    r"^(?P<pre>\s*<AssemblyVersion[^>]*>)"
    r"(?P<ver>\d+\.\d+\.\d+\.\d+)"
    r"(?P<post></AssemblyVersion>.*)$")

def process(path, pkg):
    with open(path, "rb") as f:
        raw = f.read()
    bom = b""
    if raw.startswith(b"\xef\xbb\xbf"):
        bom, raw = raw[:3], raw[3:]
    le = "\r\n" if b"\r\n" in raw else "\n"
    text = raw.decode("utf-8")
    lines, out, changed = text.split(le), [], False
    nuget_ver = None
    for line in lines:
        nl = line
        skip = NO_INCREMENT in line
        m = RE_BASELINE.match(line)
        if m and not skip:
            if nuget_ver is None:
                nuget_ver = latest_nuget(pkg)
            if nuget_ver and nuget_ver != m.group("ver"):
                nl = m.group("pre") + nuget_ver + m.group("post")
        m = RE_PACKABLE.match(line)
        if m:
            nl = m.group("pre") + "false" + m.group("post")
        m = RE_VERPREFIX.match(line)
        if m and not skip:
            nl = m.group("pre") + bump_patch(m.group("ver")) + m.group("post")
        m = RE_ASMVER.match(line)
        if m and not skip:
            nl = m.group("pre") + bump_patch(m.group("ver")) + m.group("post")
        if nl != line:
            changed = True
        out.append(nl)
    if changed:
        with open(path, "wb") as f:
            f.write(bom + le.join(out).encode("utf-8"))
    return changed