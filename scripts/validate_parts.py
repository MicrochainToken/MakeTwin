"""Validate exported IDs and the semantic/movement contract; not engineering truth."""
import argparse
import json
import math
from pathlib import Path


def validate(manifest, data):
    errors = []
    expected = {p['id'] for p in manifest.get('parts', [])}
    parts = data.get('parts', [])
    if data.get('schemaVersion') != 1 or data.get('units') != 'metres' or data.get('coordinateSystem') != 'glTF-Y-up':
        errors.append('Expected schemaVersion 1, metres and glTF-Y-up')
    if not isinstance(parts, list):
        return {'passed': False, 'errors': errors + ['parts must be a list']}
    ids = [p.get('id') for p in parts]
    if len(set(ids)) != len(ids): errors.append('Duplicate part IDs')
    if set(ids) != expected: errors.append('Metadata IDs do not exactly cover exported parts')
    assemblies = data.get('assemblies', [])
    assembly_ids = {a.get('id') for a in assemblies}
    if len(assembly_ids) != len(assemblies): errors.append('Duplicate assembly IDs')
    for a in assemblies:
        if not all(isinstance(a.get(k), str) and a[k].strip() for k in ('id', 'label', 'purpose')):
            errors.append('Assembly requires id, label and purpose')
    parents = {}
    def vector(v):
        return isinstance(v, list) and len(v) == 3 and all(type(x) in (int, float) and math.isfinite(x) for x in v)
    for p in parts:
        pid = p.get('id')
        for key in ('id', 'label', 'function', 'evidenceNote'):
            if not isinstance(p.get(key), str) or not p[key].strip(): errors.append(f'{pid}: missing {key}')
        if p.get('evidence') not in ('observed', 'inferred', 'illustrative'): errors.append(f'{pid}: invalid evidence')
        if p.get('assembly') not in assembly_ids: errors.append(f'{pid}: unknown assembly')
        parent = p.get('parent')
        if 'parent' not in p or (parent is not None and (parent not in expected or parent == pid)):
            errors.append(f'{pid}: invalid parent')
        parents[pid] = parent
        interfaces = p.get('interfaces')
        if not isinstance(interfaces, list): errors.append(f'{pid}: interfaces must be a list')
        else:
            for rel in interfaces:
                if rel.get('target') not in expected or rel.get('target') == pid or not rel.get('type') or rel.get('evidence') not in ('observed', 'inferred', 'illustrative'):
                    errors.append(f'{pid}: invalid interface')
        motion = p.get('motion', {})
        kind = motion.get('kind')
        if kind not in ('fixed', 'unknown', 'rotation', 'translation'): errors.append(f'{pid}: invalid motion kind')
        if kind in ('rotation', 'translation'):
            axis, pivot, limits = motion.get('axis'), motion.get('pivot'), motion.get('range')
            if not vector(axis) or abs(sum(x*x for x in axis)-1) > 1e-3: errors.append(f'{pid}: axis must be normalized')
            if not vector(pivot): errors.append(f'{pid}: invalid pivot')
            if not (isinstance(limits, list) and len(limits) == 2 and all(type(x) in (int, float) and math.isfinite(x) for x in limits) and limits[0] <= limits[1]): errors.append(f'{pid}: invalid movement range')
            if motion.get('space') not in ('model', 'parent') or motion.get('unit') != ('radians' if kind == 'rotation' else 'metres') or not motion.get('note'):
                errors.append(f'{pid}: missing movement basis, space or unit')
    for pid in ids:
        visited, node = set(), pid
        while node is not None and node in parents:
            if node in visited:
                errors.append(f'{pid}: parent cycle')
                break
            visited.add(node)
            node = parents[node]
    return dict(passed=not errors, exportedParts=len(expected), metadataParts=len(parts), errors=errors,
                limitations='Schema, coverage and references only; function accuracy and physical movement require review.')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--manifest', type=Path, required=True)
    p.add_argument('--parts', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args()
    report = validate(json.loads(a.manifest.read_text()), json.loads(a.parts.read_text()))
    a.out.write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report))
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
