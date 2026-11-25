#!/usr/bin/env python3
"""Audit dense display metadata against the actual exported part inventory."""
import argparse
import json
import math
from collections import Counter
from pathlib import Path


def audit(manifest, explorer, minimum):
    ids = [p['id'] for p in manifest['parts']]
    groups = explorer.get('groups', [])
    errors = []
    if explorer.get('schemaVersion') != 1:
        errors.append('Unsupported explorer schema')
    if len(set(ids)) != len(ids):
        errors.append('Duplicate exported part IDs')
    assigned = []
    moving = set()
    group_ids = []
    for g in groups:
        label = g.get('id', '<missing>')
        group_ids.append(label)
        parts = g.get('parts', [])
        assigned.extend(parts)
        if len(parts) != 1:
            errors.append(f'{label}: expected one part per display group')
        offset = g.get('offset', [])
        valid = (len(offset) == 3 and all(type(v) in (float, int) and math.isfinite(v) for v in offset))
        if not valid or sum(v*v for v in offset) < 1e-6:
            errors.append(f'{label}: missing or negligible separation (<1 mm)')
        else:
            moving.update(parts)
        start, end = g.get('start'), g.get('end')
        if not (type(start) in (float, int) and type(end) in (float, int) and 0 <= start < end <= 1):
            errors.append(f'{label}: invalid stage interval')
        if g.get('evidence') not in ('observed', 'inferred', 'illustrative') or not g.get('note') or not g.get('label'):
            errors.append(f'{label}: missing evidence, note or label')
    if len(set(group_ids)) != len(group_ids):
        errors.append('Duplicate display group IDs')
    missing, unknown = sorted(set(ids)-set(assigned)), sorted(set(assigned)-set(ids))
    repeated = sorted(k for k, n in Counter(assigned).items() if n > 1)
    if missing: errors.append(f'{len(missing)} exported parts have no display group')
    if unknown: errors.append(f'{len(unknown)} unknown part IDs')
    if repeated: errors.append(f'{len(repeated)} parts have repeated membership')
    if len(set(ids)) < minimum: errors.append(f'Part count {len(set(ids))} below target {minimum}')
    return dict(passed=not errors, modeledParts=len(set(ids)), displayGroups=len(groups),
                separatedParts=len(set(ids) & moving), minimum=minimum, missing=missing,
                unknown=unknown, repeated=repeated, errors=errors,
                limitations='Inventory and metadata only; not visual, collision, geometry or engineering validation.')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--manifest', type=Path, required=True)
    p.add_argument('--explorer', type=Path, required=True)
    p.add_argument('--minimum', type=int, default=300)
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args()
    if a.minimum < 1: p.error('minimum must be positive')
    report = audit(json.loads(a.manifest.read_text()), json.loads(a.explorer.read_text()), a.minimum)
    a.out.write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps({k: report[k] for k in ('passed', 'modeledParts', 'displayGroups', 'separatedParts', 'errors')}))
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
