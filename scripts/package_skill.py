#!/usr/bin/env python3
"""Create a portable runtime ZIP, excluding private experiments, models and Git history."""
import argparse
import hashlib
import json
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]
EXCLUDED_REFERENCES = {'engineering.md', 'feeder-v4-storyboard.md', 'v4-draft.md', 'v5-draft.md'}


def runtime_files(root=ROOT):
    files = [root / n for n in ('SKILL.md', 'README.md', 'requirements.txt', 'VERSION', 'LICENSE', 'CHANGELOG.md', 'PROVENANCE.md')]
    for folder in ('reference', 'scripts', 'templates', 'examples'):
        for p in sorted((root / folder).rglob('*')):
            rel = p.relative_to(root)
            if not p.is_file() or p.is_symlink() or any(x.startswith('.') or x in ('__pycache__', 'renders') for x in rel.parts):
                continue
            if folder == 'reference' and (p.name in EXCLUDED_REFERENCES or 'draft' in p.stem):
                continue
            if p.suffix.lower() not in ('.md', '.py', '.sh', '.js', '.html', '.css', '.json', '.txt'):
                continue
            if p.name in ('checks.json', 'build_results_page.py') or p.name.endswith('.manifest.json'):
                continue
            files.append(p)
    return sorted(set(p for p in files if p.is_file()))


def package(out, root=ROOT):
    out = out.resolve()
    if out.suffix.lower() != '.zip':
        raise ValueError('--out must end in .zip')
    if out.exists():
        raise ValueError('Refusing to overwrite an existing package; choose a new --out file.')
    files = runtime_files(root)
    if not files or root / 'SKILL.md' not in files:
        raise ValueError('SKILL.md is missing')
    manifest = {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    out.parent.mkdir(parents=True, exist_ok=True)
    temporary = out.with_suffix('.zip.tmp')
    try:
        with zipfile.ZipFile(temporary, 'w', zipfile.ZIP_DEFLATED) as z:
            for p in files:
                z.write(p, 'mechanical-explorer-test/' + str(p.relative_to(root)))
            z.writestr('mechanical-explorer-test/PACKAGE-MANIFEST.json', json.dumps(manifest, indent=2) + '\n')
        with zipfile.ZipFile(temporary) as z:
            if z.testzip() is not None:
                raise ValueError('ZIP validation failed')
        temporary.replace(out)
    finally:
        temporary.unlink(missing_ok=True)
    return dict(file=str(out), files=len(files), sha256=hashlib.sha256(out.read_bytes()).hexdigest())


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args()
    try:
        print(json.dumps(package(a.out), indent=2))
    except (ValueError, OSError) as e:
        p.error(str(e))


if __name__ == '__main__':
    main()
