#!/usr/bin/env python3
"""Audit local deliverables without Blender, model calls or network access."""
import argparse
import json
import struct
from pathlib import Path

from delivery_files import viewer_assets
from guide_schema import validate_guides, validate_clip_cameras
from artifact_revision import revision, check_report_issues, write_json


def glb_document(file):
    raw = Path(file).read_bytes()
    if len(raw) < 20:
        raise ValueError('GLB is truncated.')
    magic, version, total = struct.unpack_from('<4sII', raw)
    size, kind = struct.unpack_from('<II', raw, 12)
    if magic != b'glTF' or version != 2 or total != len(raw) or kind != 0x4e4f534a or size > len(raw) - 20:
        raise ValueError('Invalid GLB header or JSON chunk.')
    doc = json.loads(raw[20:20 + size])
    if any(buffer.get('uri') for buffer in doc.get('buffers', [])):
        raise ValueError('GLB depends on an external buffer.')
    return doc


def audit(project):
    project = Path(project)
    issues = []
    result = {'technicalPassed': False, 'humanAcceptance': 'not_assessed', 'issues': issues}
    try:
        source = revision(project / 'model.blend')
        model = revision(project / 'model.glb')
        manifest = json.loads((project / 'model.manifest.json').read_text())
        checks = json.loads((project / 'checks.json').read_text())
        renders = json.loads((project / 'renders/render-manifest.json').read_text())
        for label, record in [('Export', manifest), ('Renders', renders)]:
            if record.get('provenance', {}).get('sourceBlend', {}).get('sha256') != source['sha256']:
                issues.append(label + ' do not identify the current Blender revision.')
        issues.extend(check_report_issues(checks, source))
        if manifest.get('artifact', {}).get('sha256') != model['sha256']:
            issues.append('Export manifest does not identify the current GLB bytes.')
        if manifest.get('validation', {}).get('status') != 'checks_passed':
            issues.append('Export is partial or has no validated export status.')
        if not renders.get('complete') or not renders.get('files'):
            issues.append('Review renders are incomplete.')
        for record in renders.get('files', []):
            name = record.get('file', '')
            if not name or Path(name).name != name:
                issues.append('Invalid render filename in manifest.')
                continue
            if revision(project / 'renders' / name)['sha256'] != record.get('sha256'):
                issues.append('Render bytes changed: ' + name)
        doc = glb_document(project / 'model.glb')
        clips = {a.get('name') for a in doc.get('animations', [])}
        expected = {a['name'] for a in manifest.get('clips', [])}
        issues.extend(validate_guides(manifest.get('guides', []), {a['name']: a.get('seconds', 0) for a in manifest.get('clips', [])}, {p['id'] for p in manifest.get('parts', [])}))
        issues.extend(validate_clip_cameras(manifest.get('clipCameras', {}), {a['name']: a.get('seconds', 0) for a in manifest.get('clips', [])}, {p['id'] for p in manifest.get('parts', [])}))
        if manifest.get('schemaVersion', 4) >= 5:
            embedded = doc.get('scenes', [{}])[doc.get('scene', 0)].get('extras', {}).get('c3d_camera_metadata')
            if not embedded or json.loads(embedded) != {k:manifest[k] for k in ('schemaVersion','cameraViews','guides','clipCameras')}:
                issues.append('GLB camera metadata differs from its manifest.')
            for asset in viewer_assets():
                if not (project / asset.name).is_file():
                    issues.append('Missing portable viewer file: ' + asset.name)
        if clips != expected:
            issues.append('Animation names in GLB and export manifest differ.')
        if not expected.issubset(set(renders.get('clips', []))):
            issues.append('Not all exported animations have review render sheets.')
        rendered_files = {r.get('file') for r in renders.get('files', [])}
        required_sheets = {'views.png'} | {'clip-' + name + '.png' for name in expected}
        if not required_sheets.issubset(rendered_files):
            issues.append('Render manifest is missing required overview or animation sheet files.')
        names = {n.get('name') for n in doc.get('nodes', [])}
        missing = {p['id'] for p in manifest.get('parts', [])} - names
        if missing:
            issues.append('Registered parts missing from GLB nodes: ' + ', '.join(sorted(missing)))
        unregistered = {n.get('name', '<unnamed>') for n in doc.get('nodes', []) if 'mesh' in n} - {
            p['id'] for p in manifest.get('parts', [])}
        if unregistered:
            issues.append('Unregistered mesh nodes in GLB: ' + ', '.join(sorted(unregistered)))
        result.update(sourceBlend=source, artifact=model, meshCount=len(doc.get('meshes', [])),
                      clipCount=len(clips), warningCount=checks['summary'].get('warnings', 0))
    except (OSError, ValueError, KeyError, TypeError) as error:
        issues.append(str(error))
    result['technicalPassed'] = not issues
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('project', type=Path)
    parser.add_argument('--report', type=Path)
    args = parser.parse_args()
    report = audit(args.project)
    if args.report:
        write_json(args.report, report)
    print(json.dumps(report, indent=2))
    return 0 if report['technicalPassed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
