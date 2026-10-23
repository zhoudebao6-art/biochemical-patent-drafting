"""Transactional formatting and unchanged validation boundaries; no model calls."""
from pathlib import Path
import hashlib
import tempfile
import unittest
import zipfile
from unittest.mock import patch
from docx import Document
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from lxml import etree as ET
import bio_package
import bio_background
import bio_spacing
import bio_scripts
import json
import stage_bundle


def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()


class PackageTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name)/'sample.docx'

    def fixture(self, ambiguous=False):
        doc = Document(); p = doc.add_paragraph('Na₂CO₃含量为0.5 g；10⁻⁵。')
        props = p.runs[0]._r.get_or_add_rPr()
        shade = OxmlElement('w:shd'); shade.set(qn('w:fill'), 'FFFFFF'); props.append(shade)
        background = OxmlElement('w:background'); background.set(qn('w:color'), 'CCFFCC'); doc.element.insert(0, background)
        doc.sections[0].header.paragraphs[0].text = '说 明 书'
        if ambiguous: doc.add_paragraph('retain separate words')
        doc.save(self.path)
        # Non-XML data must be byte-identical after normalization.
        with zipfile.ZipFile(self.path, 'a') as package: package.writestr('word/media/unchanged.bin', b'original-scientific-object')

    def test_single_commit_and_final_hash_preserve_objects_and_native_scripts(self):
        self.fixture()
        replace = bio_package.os.replace
        with patch.object(bio_package.os, 'replace', wraps=replace) as commit:
            result = bio_package.normalize(self.path)
        self.assertEqual(commit.call_count, 1)
        doc = Document(self.path); self.assertEqual(doc.paragraphs[0].text, 'Na2CO3含量为0.5g；10-5。')
        self.assertEqual([r.text for r in doc.paragraphs[0].runs if r.font.subscript], ['2', '3'])
        self.assertEqual([r.text for r in doc.paragraphs[0].runs if r.font.superscript], ['-5'])
        for mode in ('background', 'native_scripts'):
            self.assertEqual(result[mode]['evidence']['artifact_sha256'], sha(self.path))
            self.assertEqual(result[mode]['evidence']['issues'], [])
        with zipfile.ZipFile(self.path) as package: self.assertEqual(package.read('word/media/unchanged.bin'), b'original-scientific-object')
        stable = sha(self.path); bio_package.normalize(self.path); self.assertEqual(sha(self.path), stable)

    def test_late_ambiguity_leaves_entire_file_untouched(self):
        self.fixture(ambiguous=True); original = self.path.read_bytes()
        with self.assertRaisesRegex(ValueError, 'source-bound rewording'):
            bio_package.normalize(self.path)
        self.assertEqual(self.path.read_bytes(), original)
        self.assertTrue(bio_background.scan_docx(self.path)['issues'])
        self.assertTrue(bio_scripts.scan_docx(self.path)['issues'])

    def test_shared_scan_parses_each_xml_once_and_keeps_all_hits(self):
        self.fixture(); parse = ET.fromstring
        with zipfile.ZipFile(self.path) as package:
            expected = len(bio_spacing.selected_parts(package.namelist()))
            with patch.object(bio_package.ET, 'fromstring', wraps=parse) as reader:
                scans = bio_package.scan_package(package, sha(self.path))
            self.assertEqual(reader.call_count, expected)
        for mode, module, key in [('spacing', bio_spacing, 'hits'), ('background', bio_background, 'issues'), ('native_scripts', bio_scripts, 'issues')]:
            self.assertEqual(scans[mode][key], module.scan_docx(self.path)[key])

    def test_individual_domain_entrypoints_preserve_other_domains(self):
        self.fixture(); bio_background.normalize(self.path)
        self.assertFalse(bio_background.scan_docx(self.path)['issues'])
        self.assertTrue(bio_scripts.scan_docx(self.path)['issues'])
        self.assertTrue(bio_spacing.scan_docx(self.path)['hits'])
        bio_scripts.normalize(self.path); self.assertFalse(bio_scripts.scan_docx(self.path)['issues'])
        self.assertTrue(bio_spacing.scan_docx(self.path)['hits'])
        bio_spacing.normalize(self.path); self.assertFalse(bio_spacing.scan_docx(self.path)['hits'])

    def test_compact_packet_binds_exact_exceptions_without_dropping_rules(self):
        skill = Path(__file__).resolve().parents[1]
        rules = json.loads((skill/'references/rules.json').read_text(encoding='utf-8'))
        for stage in stage_bundle.STAGES:
            packet, coverage = stage_bundle.build_packet(skill, rules, stage)
            shared = {rule_id: row for row in coverage['shared_exceptions'] for rule_id in row['rule_ids']}
            for rule in rules['rules']:
                if rule['status'] != 'active' or rule['id'] not in coverage['included_rule_ids']: continue
                row = shared.get(rule['id'])
                if row:
                    self.assertEqual(row['exceptions'], rule['exceptions'])
                    self.assertIn(stage_bundle.rule_block(rule, row['id']), packet)
                    self.assertEqual(packet.count(stage_bundle.canonical(row['exceptions'])), 1)
                else: self.assertIn(stage_bundle.rule_block(rule), packet)


if __name__ == '__main__': unittest.main()
