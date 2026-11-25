"""Set C3D_EXPORT_FIXTURE to the directory produced by tests/run_tests.sh."""
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path


@unittest.skipUnless(os.environ.get('C3D_EXPORT_FIXTURE'), 'Run example tests and set C3D_EXPORT_FIXTURE first')
class ExportGuardTests(unittest.TestCase):
    def setUp(self):
        self.skill = Path(__file__).resolve().parents[1]
        self.fixture = Path(os.environ['C3D_EXPORT_FIXTURE']).resolve()
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.out = Path(self.tmp.name)
        self.report = json.loads((self.fixture / 'checks.json').read_text())

    def run_export(self, partial=False):
        checks = self.out / 'checks.json'
        checks.write_text(json.dumps(self.report))
        cmd = [str(self.skill / 'scripts/blender.sh'), '-b', str(self.fixture / 'mini-oven.blend'),
               '--python', str(self.skill / 'scripts/export_glb.py'), '--',
               '--checks', str(checks), '--out', str(self.out / 'draft.glb')]
        if partial:
            cmd.append('--partial')
        return subprocess.run(cmd, capture_output=True, text=True, timeout=45)

    def test_stale_report_fails_without_overwriting_existing_export(self):
        self.report['provenance']['sourceBlend']['sha256'] = '0' * 64
        old = b'previous artifact must survive'
        (self.out / 'draft.glb').write_bytes(old)
        run = self.run_export()
        self.assertNotEqual(run.returncode, 0, run.stdout + run.stderr)
        self.assertEqual((self.out / 'draft.glb').read_bytes(), old)

    def test_failed_checks_block_normal_export(self):
        self.report['summary']['errors'] = 2
        run = self.run_export()
        self.assertNotEqual(run.returncode, 0, run.stdout + run.stderr)
        self.assertFalse((self.out / 'draft.glb').exists())

    def test_partial_export_preserves_failure_label(self):
        self.report['summary']['errors'] = 2
        run = self.run_export(partial=True)
        self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
        manifest = json.loads((self.out / 'draft.manifest.json').read_text())
        self.assertEqual(manifest['validation']['status'], 'partial')
        self.assertTrue(manifest['validation']['issues'])


if __name__ == '__main__':
    unittest.main()
