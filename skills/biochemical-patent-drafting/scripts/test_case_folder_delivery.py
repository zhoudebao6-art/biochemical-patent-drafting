"""Real filesystem publication with simulated acceptance, never model review."""
import copy
import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import batch_tool as b
import flat_delivery as flat
import parallel_batch as p
from test_parallel_batch import POLICY
import test_parallel_batch as parallel
from test_batch_tool import docx

DELIVERY = {'name_source': 'case_folder', 'layout': 'source_case_files', 'timing': 'after_each_acceptance'}


class CaseFolderTests(unittest.TestCase):
    reserve = parallel.ParallelTests.reserve
    record = parallel.ParallelTests.record

    def receipt(self, reserved, verdict='complete'):
        result=parallel.ParallelTests.receipt(self,reserved,verdict)
        result.update({key:reserved['spawn_arguments'][key] for key in ('model','reasoning_effort')})
        return result

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.src = self.root / '输入批次'; self.src.mkdir()
        self.folders = [self.src / '第一案完整名称', self.src / '第二案完整名称']
        for folder in self.folders:
            folder.mkdir(); docx(folder / '技术项目优化说明书.docx', 'source')
            (folder / '样品数据.xlsx').write_bytes(b'untouched attachment')
        self.originals = {str(f): b.sha(f) for f in self.src.rglob('*') if f.is_file()}
        self.policy = copy.deepcopy(POLICY); self.policy['delivery'] = DELIVERY
        self.policy_path = self.root / 'policy.json'; b.atomic(self.policy_path, self.policy)
        self.rules_path = self.root / 'rules.json'; b.atomic(self.rules_path, {'version': 17, 'rules': []})
        for key, value in (('POLICY', self.policy_path), ('RULES', self.rules_path)):
            patcher = patch.object(p, key, value); patcher.start(); self.addCleanup(patcher.stop)
        self.selection = {'projects': [{'title': '正式技术标题',
            'primary_source': str((folder / '技术项目优化说明书.docx').relative_to(self.src)),
            'source_files': [str(f.relative_to(self.src)) for f in folder.iterdir()]}
            for folder in self.folders]}

    def init(self):
        self.manifest = p.init(self.src, self.root / 'work', self.selection, self.root / 'unused-desktop')
        self.batch = self.manifest.parent

    def complete_one(self):
        draft = self.reserve(1); self.record(draft)
        review = self.reserve(1); self.record(review)
        return draft['case_id']

    def target(self, index=0):
        folder = self.folders[index]
        return folder / (folder.name + '.docx')

    def assert_originals(self):
        self.assertEqual({f: b.sha(Path(f)) for f in self.originals}, self.originals)

    def test_policy_accepts_new_and_rejects_extra_settings(self):
        p.validate_policy(self.policy)
        bad = copy.deepcopy(self.policy); bad['delivery'] = dict(DELIVERY, folder_suffix='终稿')
        with self.assertRaises(b.BatchError): p.validate_policy(bad)

    def test_immediate_delivery_exact_folder_filename_and_resume(self):
        self.init(); self.complete_one()
        self.assertEqual(Path(p.deliver(self.manifest)), self.src)
        self.assertTrue(self.target().is_file()); self.assertFalse(self.target(1).exists())
        before = (b.sha(self.target()), self.target().stat().st_mtime_ns)
        self.assertFalse(b.read(self.manifest)['delivery_closed'])
        self.complete_one(); p.deliver(self.manifest); p.deliver(self.manifest)
        self.assertEqual((b.sha(self.target()), self.target().stat().st_mtime_ns), before)
        self.assertTrue(b.read(self.manifest)['delivery_closed'])
        for folder in self.folders:
            self.assertEqual({f.name for f in folder.iterdir()},
                {'技术项目优化说明书.docx', '样品数据.xlsx', folder.name + '.docx'})
        self.assertFalse((self.root / 'unused-desktop').exists())
        self.assert_originals()

    def test_same_leaf_names_in_different_directories_do_not_conflict(self):
        self.folders = []
        for group in ('组甲', '组乙'):
            folder = self.src / group / '相同名称'; folder.mkdir(parents=True)
            docx(folder / '项目书.docx', 'source'); self.folders.append(folder)
        self.selection = {'projects': [{'title': '同名', 'primary_source': str((f/'项目书.docx').relative_to(self.src)),
             'source_files': [str((f/'项目书.docx').relative_to(self.src))]} for f in self.folders]}
        self.init(); self.complete_one(); p.deliver(self.manifest); self.complete_one(); p.deliver(self.manifest)
        self.assertTrue(all(self.target(i).exists() for i in range(2)))

    def test_multiple_proposals_in_one_folder_block_before_batch_creation(self):
        folder = self.folders[0]; docx(folder / '另一本项目书.docx', 'other')
        self.selection['projects'][1] = {'title': '另一案',
            'primary_source': str((folder/'另一本项目书.docx').relative_to(self.src)),
            'source_files': [str((folder/'另一本项目书.docx').relative_to(self.src))]}
        with self.assertRaisesRegex(b.BatchError, 'same delivery target'): self.init()
        self.assertFalse((self.root/'work').exists())

    def test_existing_final_and_source_name_conflicts_are_not_overwritten(self):
        self.target().write_bytes(b'user document')
        with self.assertRaisesRegex(b.BatchError, 'already exists'): self.init()
        self.assertEqual(self.target().read_bytes(), b'user document'); self.assert_originals()

    def test_conflict_created_after_init_preserved_even_identical_bytes(self):
        self.init(); self.complete_one()
        c=b.read(self.manifest)['projects'][0]; self.target().write_bytes(Path(c['artifact']).read_bytes())
        identity=flat.file_identity(self.target())
        with self.assertRaisesRegex(b.BatchError, 'receipt|Unowned'): p.deliver(self.manifest)
        self.assertEqual(flat.file_identity(self.target()),identity); self.assert_originals()

    def test_delivery_map_tamper_is_rejected(self):
        self.init(); m=b.read(self.manifest); m['projects'][0]['delivery_target']['filename']='wrong.docx'
        b.atomic(self.manifest,m)
        with self.assertRaisesRegex(b.BatchError, 'target'): p.load_manifest(self.manifest)

    def test_replaced_directory_is_not_used(self):
        self.init(); self.complete_one()
        folder=self.folders[0]; folder.rename(self.src/'original-preserved'); folder.mkdir()
        for source in (self.src/'original-preserved').iterdir(): shutil.copyfile(source,folder/source.name)
        with self.assertRaisesRegex(b.BatchError, 'directory identity'): p.deliver(self.manifest)
        self.assertFalse(self.target().exists())

    def test_junction_target_is_rejected(self):
        if os.name != 'nt': self.skipTest('Windows junction regression')
        import subprocess
        self.init(); self.complete_one(); folder=self.folders[0]
        preserved=self.src/'original-preserved'; folder.rename(preserved)
        run=subprocess.run(['cmd','/c','mklink','/J',str(folder),str(preserved)],capture_output=True)
        self.assertEqual(run.returncode,0)
        try:
            with self.assertRaisesRegex(b.BatchError,'reparse|Links'): p.deliver(self.manifest)
            self.assertFalse((preserved/(folder.name+'.docx')).exists())
        finally:
            os.rmdir(folder)  # remove only the junction itself, never its contents

    def test_unaccepted_case_is_not_published(self):
        self.init(); self.record(self.reserve(1))
        with self.assertRaises(b.BatchError): p.deliver(self.manifest)
        self.assertFalse(self.target().exists())

    def test_changed_source_prevents_publication(self):
        self.init(); self.complete_one()
        (self.folders[0]/'样品数据.xlsx').write_bytes(b'changed')
        with self.assertRaises(b.BatchError): p.deliver(self.manifest)
        self.assertFalse(self.target().exists())

    def test_changed_accepted_artifact_prevents_publication(self):
        self.init(); self.complete_one(); c=b.read(self.manifest)['projects'][0]
        Path(c['artifact']).write_bytes(b'changed')
        with self.assertRaises(b.BatchError): p.deliver(self.manifest)
        self.assertFalse(self.target().exists())

    def test_interrupted_staged_publish_recovers_identity(self):
        self.init(); self.complete_one()
        with patch.object(flat,'publish_file',side_effect=OSError('interrupted')):
            with self.assertRaises(OSError): p.deliver(self.manifest)
        m=b.read(self.manifest); record=b.read(flat.receipt_path(m,m['projects'][0]))
        p.deliver(self.manifest)
        self.assertEqual(flat.file_identity(self.target()),record['file_identity']); self.assert_originals()

    def test_published_then_manifest_crash_recovers_without_overwrite(self):
        self.init(); self.complete_one(); original=b.atomic
        def interrupt(path,value):
            if Path(path)==self.manifest and value.get('delivery_path'): raise OSError('commit interrupted')
            return original(path,value)
        with patch.object(b,'atomic',side_effect=interrupt):
            with self.assertRaises(OSError): p.deliver(self.manifest)
        before=(b.sha(self.target()),self.target().stat().st_mtime_ns)
        p.deliver(self.manifest)
        self.assertEqual((b.sha(self.target()),self.target().stat().st_mtime_ns),before)
        self.assertEqual(b.read(self.manifest)['projects'][0]['status'],'delivered')

    def test_direct_single_case_folder_is_supported(self):
        self.src=self.folders[0]; self.folders=[self.src]
        self.selection={'projects':[{'title':'正式名称','primary_source':'技术项目优化说明书.docx',
                                     'source_files':['技术项目优化说明书.docx','样品数据.xlsx']}]}
        self.init(); self.complete_one(); p.deliver(self.manifest)
        self.assertTrue(self.target().exists())

    def test_generated_final_cannot_be_selected_as_primary_or_attachment(self):
        self.init(); self.complete_one(); p.deliver(self.manifest)
        self.selection['projects'][0]['source_files'].append(str(self.target().relative_to(self.src)))
        with self.assertRaisesRegex(b.BatchError,'already exists|Source cannot'): self.init()

    def test_source_itself_named_as_target_is_protected(self):
        docx(self.target(), 'original proposal')
        rel=str(self.target().relative_to(self.src))
        self.selection['projects'][0].update(primary_source=rel,source_files=[rel])
        digest=b.sha(self.target())
        with self.assertRaisesRegex(b.BatchError,'already exists'): self.init()
        self.assertEqual(b.sha(self.target()),digest)

    def test_full_folder_name_preserved_without_title_or_suffix(self):
        import case_folder_delivery as folders
        folder=self.src/('完整名称-'+'化学材料'*24+'(1)')
        self.assertEqual(folders.filename(folder),folder.name+'.docx')
        for name in ('NUL','CONIN$','COM¹','结尾.','中'*251):
            with self.subTest(name=name), self.assertRaises(b.BatchError): folders.filename(self.src/name)

    def test_nonblocking_publication_merges_other_case_progress(self):
        import test_nonblocking_pools as nonblocking
        policy=nonblocking.policy(); policy['delivery']=DELIVERY
        b.atomic(self.policy_path,policy)
        self.init(); self.complete_one()
        original=flat.publish_file
        def interleave(stage,target):
            # Queue activity happens outside the publication lock; it must survive
            # the independently committed final's manifest merge.
            self.record(self.reserve(1))
            original(stage,target)
        with patch.object(flat,'publish_file',side_effect=interleave):
            p.deliver(self.manifest)
        m=b.read(self.manifest)
        self.assertEqual(m['delivery_mode'],'source_case_files_v1')
        self.assertEqual([c['status'] for c in m['projects']],['delivered','drafted'])
        self.assertTrue(self.target().exists()); self.assertFalse(self.target(1).exists())

    def test_real_current_policy_freezes_routing_and_all_tools(self):
        skill=Path(__file__).resolve().parents[1]
        with patch.object(p,'POLICY',skill/'references/batch-policy.json'), patch.object(p,'RULES',skill/'references/rules.json'):
            self.init()
        m=p.load_manifest(self.manifest)
        self.assertEqual(m['policy']['delivery'],DELIVERY)
        self.assertEqual(m['policy']['stage_pools'],{'draft':16,'review':8,'revise':8})
        import stage_bundle
        stage_bundle.verify(m,full=True)

    def test_title_contract_keeps_official_title_and_case_folder_filename_separate(self):
        self.init(); m=b.read(self.manifest); c=m['projects'][0]
        m['policy'].update(output_contract='wording_title_v18',biochemical_contract='biochemical_v1')
        report={'sha256':'current'}
        verified={'handoff':{'input_inspection':'bound'},'input_report':report,'source_reports':[]}
        technical={'document_title':c['title'],'artifact_sha256':'current','delivery_filename':c['title']+'.docx'}
        import prepare_handoff, bio_contract, output_contract
        with patch.object(prepare_handoff,'verify_prepared',return_value=verified), patch.object(bio_contract,'check',return_value=technical):
            result=output_contract.verify(m,c,{'input_artifact_sha256':'current'},{})
        self.assertEqual(result['document_title'],'正式技术标题')
        self.assertEqual(result['delivery_filename'],self.target().name)


if __name__ == '__main__': unittest.main()
