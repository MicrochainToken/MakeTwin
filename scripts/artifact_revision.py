"""Small, Blender-independent helpers for identifying the model actually checked."""
import hashlib
import json
from pathlib import Path


def revision(file):
    path = Path(file)
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    return {'file': path.name, 'bytes': path.stat().st_size, 'sha256': digest.hexdigest()}


def write_json(file, value):
    path = Path(file)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + '.tmp')
    temporary.write_text(json.dumps(value, indent=2) + '\n', encoding='utf-8')
    temporary.replace(path)


def check_report_issues(report, source):
    issues = []
    recorded = report.get('provenance', {}).get('sourceBlend', {})
    if not recorded.get('sha256') or recorded.get('sha256') != source['sha256']:
        issues.append('Check report does not identify this saved Blender revision; rerun checks.')
    errors = report.get('summary', {}).get('errors')
    if not isinstance(errors, int) or errors < 0:
        issues.append('Check report has no valid error count.')
    elif errors:
        issues.append(f'Check report contains {errors} error(s).')
    return issues
