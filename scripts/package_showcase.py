#!/usr/bin/env python3
"""Package the reusable skill, optionally with an isolated original-input case."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import tarfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]
INSTALL_ID = 'mechanical-explorer-test'
PUBLIC_DIRS = {'assets', 'docs', 'reference', 'scripts', 'templates', 'examples', 'tests'}
PUBLIC_ROOT = {'SKILL.md', 'README.md', 'requirements.txt', 'VERSION', 'LICENSE',
               'CHANGELOG.md', 'PROVENANCE.md', 'CONTRIBUTING.md'}
EXCLUDED_DIRS = {'__pycache__', 'renders', 'output', 'node_modules', 'inputs', 'ops', 'agent-home'}
SUFFIXES = {'.md', '.py', '.sh', '.js', '.cjs', '.html', '.css', '.json', '.txt',
            '.yaml', '.yml', '.png', '.jpg', '.jpeg', '.gif', '.webp', '.svg', '.woff', '.woff2'}


def skill_files(root=ROOT):
    for path in sorted(root.rglob('*')):
        rel = path.relative_to(root)
        if not path.is_file() or path.is_symlink():
            continue
        if any(part.startswith('.') or part in EXCLUDED_DIRS for part in rel.parts):
            continue
        if len(rel.parts) == 1:
            if path.name in PUBLIC_ROOT:
                yield path
            continue
        if rel.parts[0] not in PUBLIC_DIRS:
            continue
        if rel.parts[0] == 'reference' and (path.name == 'feeder-v4-storyboard.md' or 'draft' in path.stem):
            continue
        # The shipped preview is one coherent asset set. Other generated models stay out.
        if path.suffix in SUFFIXES or rel.as_posix() == 'templates/viewer/model.glb':
            yield path


def package(out, case=None, root=None):
    root = Path(root) if root is not None else ROOT
    out = Path(out).resolve()
    if out.exists():
        raise ValueError('Choose a new output file; packages are immutable')
    if not (root / 'SKILL.md').is_file():
        raise ValueError('SKILL.md is missing')
    if case and not str(out).endswith('.tgz'):
        raise ValueError('Case packages use .tgz')
    if not case and out.suffix != '.zip':
        raise ValueError('Skill-only packages use .zip')
    files = {'Skill/' + p.relative_to(root).as_posix(): p for p in skill_files(root)}
    if case:
        case = Path(case).resolve()
        for path in sorted(case.rglob('*')):
            if not path.is_file() or path.is_symlink() or any(part.startswith('.') for part in path.relative_to(case).parts):
                continue
            rel = path.relative_to(case).as_posix()
            if rel != 'CASE.md' and not rel.startswith('inputs/'):
                raise ValueError('Case contains a non-input artifact: ' + rel)
            files[rel] = path
        if 'inputs/manual.pdf' not in files or 'CASE.md' not in files:
            raise ValueError('Case needs CASE.md and inputs/manual.pdf')
    manifest = {
        'skill': INSTALL_ID,
        'version': (root / 'VERSION').read_text().strip() if (root / 'VERSION').exists() else 'unknown',
        'files': {(name if case else name.removeprefix('Skill/')): hashlib.sha256(path.read_bytes()).hexdigest()
                  for name, path in files.items()},
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    temporary = out.with_name(out.name + '.tmp')
    try:
        if case:
            with tarfile.open(temporary, 'w:gz') as archive:
                for name, path in files.items():
                    archive.add(path, arcname=name, recursive=False)
                data = (json.dumps(manifest, indent=2) + '\n').encode()
                info = tarfile.TarInfo('MANIFEST.json')
                info.size, info.mode = len(data), 0o644
                archive.addfile(info, io.BytesIO(data))
        else:
            with zipfile.ZipFile(temporary, 'w', zipfile.ZIP_DEFLATED) as archive:
                for name, path in files.items():
                    archive.write(path, INSTALL_ID + '/' + name.removeprefix('Skill/'))
                archive.writestr(INSTALL_ID + '/PACKAGE-MANIFEST.json', json.dumps(manifest, indent=2) + '\n')
            with zipfile.ZipFile(temporary) as archive:
                if archive.testzip() is not None:
                    raise ValueError('ZIP validation failed')
        temporary.replace(out)
    finally:
        temporary.unlink(missing_ok=True)
    return {'file': str(out), 'files': len(files), 'sha256': hashlib.sha256(out.read_bytes()).hexdigest(), 'modelCalls': 0}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--case', type=Path)
    args = parser.parse_args()
    print(json.dumps(package(args.out, args.case), indent=2))


if __name__ == '__main__':
    main()
