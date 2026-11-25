#!/usr/bin/env python3
"""Check a clean Skill installation. Optional smoke test uses no AI or provider calls."""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
from delivery_files import REQUIRED_VIEWER_FILES
VIEWER_FILES = REQUIRED_VIEWER_FILES


def find_blender():
    explicit = os.environ.get('BLENDER')
    if explicit:
        return shutil.which(explicit) or (explicit if Path(explicit).is_file() and os.access(explicit, os.X_OK) else None)
    return shutil.which('blender') or next((p for p in (
        '/Applications/Blender.app/Contents/MacOS/Blender',
        str(Path.home() / 'Applications/Blender.app/Contents/MacOS/Blender')) if Path(p).is_file()), None)


def inspect(agent=False):
    checks = []
    def add(name, ok, required, fix):
        checks.append(dict(name=name, available=bool(ok), required=required, fix=None if ok else fix))
    add('Python 3.10+', sys.version_info >= (3, 10), True, 'Use Python 3.10 or newer.')
    blender = find_blender()
    version_ok = False
    if blender:
        try:
            r = subprocess.run([blender, '--version'], capture_output=True, text=True, timeout=20)
            first = r.stdout.splitlines()[0] if r.stdout else ''
            import re
            match = re.search(r'Blender (\d+)\.(\d+)', first)
            version_ok = r.returncode == 0 and match and tuple(map(int, match.groups())) >= (4, 2)
        except (OSError, subprocess.TimeoutExpired):
            pass
    add('Blender 4.2+', version_ok, True, 'Install Blender 4.2+; set BLENDER to its executable if it is not found.')
    add('Pillow', importlib.util.find_spec('PIL') is not None, agent, 'Install with: python3 -m pip install Pillow')
    for name in ('pdftoppm', 'pdftotext', 'pdfinfo'):
        add(name, shutil.which(name), agent, 'Install Poppler for PDF manuals (macOS: brew install poppler).')
    node = shutil.which('node')
    node_ok = False
    if node:
        try:
            r = subprocess.run([node, '--version'], capture_output=True, text=True, timeout=10)
            node_ok = r.returncode == 0 and int(r.stdout.strip().lstrip('v').split('.')[0]) >= 22
        except (OSError, ValueError, subprocess.TimeoutExpired):
            pass
    add('Node.js 22+', node_ok, agent, 'Install Node.js 22+ and put node on PATH.')
    for name in VIEWER_FILES:
        add('viewer/' + name, (ROOT / 'templates/viewer' / name).is_file(), True, 'Use the complete Skill folder, including templates/viewer/.')
    import hashlib
    try:
        record = json.loads((ROOT / 'templates/viewer/vendor-sources.json').read_text())
        hashes = record['rewrittenLocalModuleHashes']
        expected = {name for name in VIEWER_FILES if name.startswith('vendor-') and name.endswith('.js')}
        intact = set(hashes) == expected and all(
            hashlib.sha256((ROOT / 'templates/viewer' / name).read_bytes()).hexdigest() == digest
            for name, digest in hashes.items())
    except (OSError, ValueError, KeyError, TypeError):
        intact = False
    add('Viewer vendor integrity', intact, True, 'Restore vendor files and vendor-sources.json from the same release.')
    return checks, blender


def smoke(out, blender):
    out = out.resolve()
    if out.exists() and any(out.iterdir()):
        raise ValueError('Smoke output directory must be empty; choose a new --out directory.')
    out.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ, BLENDER=blender)
    commands = [
        [blender, '-b', '--python-exit-code', '1', '--python', str(ROOT / 'examples/mini-oven/build.py'), '--', '--out', str(out / 'model.blend')],
        [blender, '-b', str(out / 'model.blend'), '--python-exit-code', '1', '--python', str(ROOT / 'scripts/check_model.py'), '--', '--report', str(out / 'checks.json')],
        [blender, '-b', str(out / 'model.blend'), '--python-exit-code', '1', '--python', str(ROOT / 'scripts/export_glb.py'), '--', '--out', str(out / 'model.glb')],
    ]
    for i, command in enumerate(commands, 1):
        with (out / f'step-{i}.log').open('w') as log:
            r = subprocess.run(command, cwd=out, env=env, stdout=log, stderr=subprocess.STDOUT, timeout=600)
        if r.returncode:
            raise RuntimeError(f'Smoke step {i} failed; inspect {out / ("step-" + str(i) + ".log")}')
    import shutil
    for name in ('parts.json', 'explorer.json', 'PLAN.md', 'build.py'):
        shutil.copy2(ROOT / 'examples/mini-oven' / name, out / name)
    from validate_parts import validate
    from audit_explosion import audit
    manifest = json.loads((out / 'model.manifest.json').read_text())
    for filename, report in (
        ('parts-audit.json', validate(manifest, json.loads((out / 'parts.json').read_text()))),
        ('explosion-audit.json', audit(manifest, json.loads((out / 'explorer.json').read_text()), 1)),
    ):
        (out / filename).write_text(json.dumps(report, indent=2) + '\n')
        if not report['passed']:
            raise RuntimeError(f'Example metadata failed: {filename}')
    missing = [n for n in ('parts.json', 'explorer.json', 'model.blend', 'model.glb', 'model.manifest.json', *VIEWER_FILES) if not (out / n).is_file()]
    if missing:
        raise RuntimeError('Missing smoke outputs: ' + ', '.join(missing))
    return dict(passed=True, output=str(out), model='model.glb', note='Deterministic generic example only; no AI/provider calls, product reconstruction or human acceptance.')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--agent', action='store_true', help='Also require the contact-sheet and PDF-manual dependencies.')
    p.add_argument('--smoke', action='store_true', help='Build/check/export the generic oven without AI calls.')
    p.add_argument('--out', type=Path, help='Empty output directory for --smoke; required to avoid modifying the Skill checkout.')
    p.add_argument('--report', type=Path)
    a = p.parse_args()
    if a.smoke and a.out is None:
        p.error('--smoke requires --out DIR')
    checks, blender = inspect(a.agent)
    result = dict(passed=all(c['available'] or not c['required'] for c in checks), checks=checks, providerCalls=0)
    if a.smoke and result['passed']:
        try:
            result['smoke'] = smoke(a.out, blender)
        except (OSError, ValueError, RuntimeError, subprocess.TimeoutExpired) as e:
            result.update(passed=False, smoke=dict(passed=False, error=str(e)))
    if a.report:
        a.report.parent.mkdir(parents=True, exist_ok=True)
        a.report.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))
    return 0 if result['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
