"""One package transaction for biochemical display normalization and scans.

Domain modules retain their rules. This module only shares XML reads and an
atomic commit; no file is replaced until every selected transform succeeds.
"""
from pathlib import Path
import hashlib
import os
import tempfile
import zipfile
from lxml import etree as ET
import bio_background
import bio_scripts
import bio_spacing

MODES = ('native_scripts', 'background', 'spacing')


def scan_package(package, artifact_sha, roots=None):
    roots = {} if roots is None else roots
    def root(name):
        if name not in roots:
            roots[name] = ET.fromstring(package.read(name))
        return roots[name]
    parts = bio_spacing.selected_parts(package.namelist())
    return {
        'native_scripts': bio_scripts.scan_package(package, artifact_sha, root),
        'background': bio_background.scan_package(package, artifact_sha, root),
        'spacing': {'schema_version': 1, 'artifact_sha256': artifact_sha,
                    'complete': 'word/document.xml' in parts,
                    'hits': [hit for name in parts for hit in bio_spacing.root_hits(root(name), name)],
                    'scope': 'Visible OOXML text, headers/footers, tables, equations, drawings/charts and numbering; images/OLE require visual review'},
    }


def scan_docx(path):
    path = Path(path)
    before = hashlib.sha256(path.read_bytes()).hexdigest()
    with zipfile.ZipFile(path) as package:
        result = scan_package(package, before)
    if hashlib.sha256(path.read_bytes()).hexdigest() != before:
        raise ValueError('Document changed during biochemical scan')
    return result


def normalize(path, modes=MODES):
    """Only use on a caller-owned generated copy. Preserve other ZIP entries."""
    modes = tuple(modes)
    if not modes or len(set(modes)) != len(modes) or set(modes) - set(MODES):
        raise ValueError('Unknown or duplicate normalization mode')
    path = Path(path)
    before = hashlib.sha256(path.read_bytes()).hexdigest()
    roots = {}; replacements = {}; converted = []; removed = []; spaced = []; count = 0
    with zipfile.ZipFile(path) as package:
        names = package.namelist()
        if 'word/document.xml' not in names:
            raise ValueError('Missing word/document.xml')
        for name in bio_spacing.selected_parts(names):
            root = ET.fromstring(package.read(name)); roots[name] = root; changed = False
            if 'native_scripts' in modes and bio_scripts.root_hits(root, name):
                converted.extend(bio_scripts.normalize_root(root, name)); changed = True
            if 'background' in modes and name in bio_background.selected_parts([name]):
                edits = bio_background.normalize_root(root, name)
                removed.extend(edits); changed = changed or bool(edits)
            if 'spacing' in modes:
                hits = bio_spacing.normalize_root(root, name)
                if hits: spaced.append(name); count += hits; changed = True
            if changed:
                replacements[name] = ET.tostring(root, xml_declaration=True, encoding='UTF-8', standalone=True)
        # Validate all enabled domains against the final in-memory document.
        evidence = scan_package(package, before, roots)
        for mode in modes:
            ev = evidence[mode]
            if not ev['complete'] or ev.get('issues', ev.get('hits')):
                raise ValueError('Biochemical normalization incomplete: ' + mode)
        if replacements:
            with tempfile.TemporaryDirectory(prefix='bio-format-', dir=path.parent) as tmp:
                pending = Path(tmp) / path.name
                with zipfile.ZipFile(pending, 'w') as output:
                    for item in package.infolist():
                        data = replacements[item.filename] if item.filename in replacements else package.read(item.filename)
                        output.writestr(item, data)
                package.close()
                if hashlib.sha256(path.read_bytes()).hexdigest() != before:
                    raise ValueError('Document changed before biochemical commit')
                os.replace(pending, path)
        elif hashlib.sha256(path.read_bytes()).hexdigest() != before:
            raise ValueError('Document changed during biochemical normalization')
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    for ev in evidence.values(): ev['artifact_sha256'] = digest
    return {
        'native_scripts': {'converted_runs': converted, 'raw_source_modified': False, 'evidence': evidence['native_scripts']},
        'background': {'removed': removed, 'evidence': evidence['background']},
        'spacing': {'mode': 'no_visible_spaces_v2', 'removed_characters': count, 'changed_parts': spaced,
                    'raw_source_modified': False, 'status': 'mechanical_normalization_not_semantic_acceptance'},
    }
