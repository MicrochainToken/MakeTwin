"""Clean-install checks are deterministic and must never require provider access."""
import json
import os
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import doctor
import package_skill


class CleanInstallTests(unittest.TestCase):
    def test_missing_blender_has_actionable_failure(self):
        with patch.object(doctor, 'find_blender', return_value=None), patch.object(doctor.shutil, 'which', return_value=None):
            checks, binary = doctor.inspect()
        check = next(c for c in checks if c['name'] == 'Blender 4.2+')
        self.assertFalse(check['available'])
        self.assertTrue(check['required'])
        self.assertIn('BLENDER', check['fix'])
        self.assertIsNone(binary)

    def test_smoke_refuses_existing_outputs(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            (folder / 'valuable.txt').write_text('keep')
            with self.assertRaises(ValueError), patch.object(doctor.subprocess, 'run') as launch:
                doctor.smoke(folder, '/not/a/blender')
            launch.assert_not_called()
            self.assertEqual((folder / 'valuable.txt').read_text(), 'keep')

    def test_runtime_zip_excludes_product_history_and_generated_assets(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'skill'
            for rel in ['SKILL.md', 'README.md', 'requirements.txt', 'scripts/helper.py', 'templates/viewer/index.html',
                        'reference/api.md', 'examples/generic/build.py', 'reference/feeder-v4-storyboard.md',
                        'reference/v5-draft.md', 'evaluations/product/build.py', '.git/config',
                        'examples/generic/model.glb', 'scripts/__pycache__/helper.pyc']:
                p = root / rel
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text(rel)
            out = Path(tmp) / 'skill.zip'
            report = package_skill.package(out, root)
            with zipfile.ZipFile(out) as z:
                files = z.namelist()
                self.assertIn('mechanical-explorer-test/scripts/helper.py', files)
                self.assertIn('mechanical-explorer-test/examples/generic/build.py', files)
                self.assertFalse(any('/evaluations/' in f or '/.git/' in f or 'storyboard' in f or 'draft' in f or f.endswith(('.glb', '.pyc')) for f in files))
                manifest = json.loads(z.read('mechanical-explorer-test/PACKAGE-MANIFEST.json'))
                self.assertIn('SKILL.md', manifest['files'])
            self.assertEqual(len(report['sha256']), 64)
            with self.assertRaises(ValueError):
                package_skill.package(out, root)

class ViewerInstallTests(unittest.TestCase):
    def test_missing_runtime_dependency_is_required(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(doctor, 'ROOT', Path(tmp)), patch.object(doctor, 'find_blender', return_value=None):
            checks, _ = doctor.inspect()
        for name in ('vendor-build-three.module.js', 'explorer-controller.js', 'EARCUT-LICENSE.txt'):
            check = next(c for c in checks if c['name'] == 'viewer/' + name)
            self.assertTrue(check['required'])
            self.assertFalse(check['available'])
        self.assertFalse(next(c for c in checks if c['name'] == 'Viewer vendor integrity')['available'])
