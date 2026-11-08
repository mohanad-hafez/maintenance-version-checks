"""Apply the four explicit rules from the preserved successful historical workflow."""
import hashlib
import json
import re
import subprocess
from pathlib import Path

PROPERTIES = {'PackageValidationBaselineVersion', 'IsPackable', 'VersionPrefix', 'AssemblyVersion'}
ELEMENT = re.compile(r'^(\s*<(?P<name>PackageValidationBaselineVersion|IsPackable|VersionPrefix|AssemblyVersion)\b[^>]*>)(?P<value>[^<]+)(</(?P=name)>.*)$')

def eligible(path):
    p = Path(path)
    return p.parts[0] == 'src' and 'tests' not in p.parts and p.suffix in {'.csproj', '.ilproj', '.props'}

def patch(value):
    parts = value.split('.')
    if len(parts) < 3 or not all(x.isdigit() for x in parts):
        raise ValueError('Non-numeric version cannot be incremented')
    parts[2] = str(int(parts[2]) + 1)
    return '.'.join(parts)

def transform(raw, latest):
    bom = b'\xef\xbb\xbf' if raw.startswith(b'\xef\xbb\xbf') else b''
    content = raw[len(bom):].decode('utf-8')
    output = []
    changes = []
    for index, line in enumerate(content.splitlines(keepends=True), 1):
        m = ELEMENT.match(line.rstrip('\r\n'))
        updated = line
        if m and 'NO-INCREMENT' not in line:
            name, value = m.group('name'), m.group('value')
            new = value
            if name == 'PackageValidationBaselineVersion':
                if not latest:
                    raise ValueError('Latest stable NuGet version unavailable')
                new = latest
            elif name == 'IsPackable' and value == 'true':
                new = 'false'
            elif name in {'VersionPrefix', 'AssemblyVersion'}:
                # The historical successful version increments every numeric entry.
                # Later workflow versions use a different conditional policy.
                if re.fullmatch(r'\d+\.\d+\.\d+(?:\.\d+)?', value):
                    new = patch(value)
            if new != value:
                start, end = m.span('value')
                updated = line[:start] + new + line[end:]
                changes.append({'line': index, 'property': name, 'before': value, 'after': new})
        output.append(updated)
    return bom + ''.join(output).encode('utf-8'), changes

def run(root):
    root = Path(root)
    files = sorted(p for p in root.joinpath('src').rglob('*') if p.is_file() and eligible(p.relative_to(root)))
    snapshots = {str(p.relative_to(root)): p.read_bytes() for p in files}
    needed = sorted({Path(name).parts[1] for name, raw in snapshots.items() if any('PackageValidationBaselineVersion' in line and 'NO-INCREMENT' not in line for line in raw.decode('utf-8-sig').splitlines())})
    feeds = {}
    for package in needed:
        url = f'https://api.nuget.org/v3-flatcontainer/{package.lower()}/index.json'
        raw = subprocess.check_output(['curl', '--fail', '--silent', '--show-error', '--location', '--max-time', '30', url], timeout=35)
        document = json.loads(raw)
        stable = [v for v in document.get('versions', []) if '-' not in v]
        if not stable:
            raise ValueError('No stable versions for ' + package)
        feeds[package] = {'url': url, 'response': document, 'latest': stable[-1], 'response_sha256': hashlib.sha256(raw).hexdigest()}
    Path('version-input-capture.json').write_text(json.dumps({'feeds': feeds, 'before': {name: {'sha256': hashlib.sha256(raw).hexdigest(), 'text': raw.decode('utf-8-sig')} for name, raw in snapshots.items()}, 'policy': 'Historical successful workflow at e5aa18b; not current conditional-prefix policy'}, indent=2) + '\n')
    changes = []
    for name, raw in snapshots.items():
        latest = feeds.get(Path(name).parts[1], {}).get('latest')
        updated, details = transform(raw, latest)
        if updated != raw:
            changes.append({'path': name, 'details': details, 'content': updated.decode('utf-8'), 'sha256': hashlib.sha256(updated).hexdigest()})
            root.joinpath(name).write_bytes(updated)
    Path('version-update-result.json').write_text(json.dumps({'status': 'changes' if changes else 'noop', 'changes': changes, 'files_scanned': len(files), 'model_calls': 0}, indent=2) + '\n')
    print(json.dumps({'files_scanned': len(files), 'files_changed': len(changes), 'model_calls': 0}))

if __name__ == '__main__':
    run('.')
