import json
import struct
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from artifact_revision import revision, write_json
from verify_delivery import audit


class DeliveryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.p = Path(self.tmp.name)
        (self.p / 'renders').mkdir()
        (self.p / 'model.blend').write_bytes(b'saved revision one')
        doc = json.dumps({'asset': {'version': '2.0'}, 'nodes': [{'name': 'body', 'mesh': 0}],
                          'meshes': [{}], 'animations': [{'name': 'open_lid'}]}).encode()
        doc += b' ' * (-len(doc) % 4)
        (self.p / 'model.glb').write_bytes(struct.pack('<4sIIII', b'glTF', 2, 20 + len(doc),
                                                     len(doc), 0x4e4f534a) + doc)
        source = {'sourceBlend': revision(self.p / 'model.blend')}
        self.manifest = {'provenance': source, 'artifact': revision(self.p / 'model.glb'),
                         'validation': {'status': 'checks_passed'}, 'parts': [{'id': 'body'}],
                         'clips': [{'name': 'open_lid'}]}
        write_json(self.p / 'model.manifest.json', self.manifest)
        write_json(self.p / 'checks.json', {'provenance': source, 'summary': {'errors': 0, 'warnings': 0}})
        (self.p / 'renders/views.png').write_bytes(b'fixture image bytes')
        (self.p / 'renders/clip-open_lid.png').write_bytes(b'fixture clip sheet bytes')
        self.renders = {'provenance': source, 'complete': True, 'clips': ['open_lid'],
                        'files': [revision(self.p / 'renders/views.png'),
                                  revision(self.p / 'renders/clip-open_lid.png')]}
        write_json(self.p / 'renders/render-manifest.json', self.renders)

    def test_matching_artifacts_are_technically_consistent_not_human_accepted(self):
        result = audit(self.p)
        self.assertTrue(result['technicalPassed'], result['issues'])
        self.assertEqual(result['humanAcceptance'], 'not_assessed')

    def test_new_blend_invalidates_old_checks_renders_and_export(self):
        (self.p / 'model.blend').write_bytes(b'new unexported revision')
        self.assertFalse(audit(self.p)['technicalPassed'])
        self.assertGreaterEqual(len(audit(self.p)['issues']), 3)

    def test_changed_glb_is_detected(self):
        with (self.p / 'model.glb').open('ab') as stream:
            stream.write(b'changed')
        self.assertFalse(audit(self.p)['technicalPassed'])

    def test_interrupted_render_is_not_accepted(self):
        self.renders['complete'] = False
        write_json(self.p / 'renders/render-manifest.json', self.renders)
        self.assertFalse(audit(self.p)['technicalPassed'])

    def test_changed_render_is_detected(self):
        (self.p / 'renders/views.png').write_bytes(b'older unrelated render')
        self.assertFalse(audit(self.p)['technicalPassed'])

    def test_partial_export_is_preserved_but_not_passed(self):
        self.manifest['validation']['status'] = 'partial'
        write_json(self.p / 'model.manifest.json', self.manifest)
        self.assertFalse(audit(self.p)['technicalPassed'])

    def test_missing_animation_review_is_not_passed(self):
        self.renders['clips'] = []
        write_json(self.p / 'renders/render-manifest.json', self.renders)
        self.assertFalse(audit(self.p)['technicalPassed'])

    def test_clip_name_without_actual_sheet_is_not_passed(self):
        self.renders['files'] = [revision(self.p / 'renders/views.png')]
        write_json(self.p / 'renders/render-manifest.json', self.renders)
        self.assertFalse(audit(self.p)['technicalPassed'])

    def test_mesh_missing_from_part_manifest_is_not_passed(self):
        self.manifest['parts'] = []
        write_json(self.p / 'model.manifest.json', self.manifest)
        self.assertFalse(audit(self.p)['technicalPassed'])


if __name__ == '__main__':
    unittest.main()
