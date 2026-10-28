"""Frozen routing for finals saved beside each case's original primary source.

Only the final filename is writable here. Existing source directories are never
claimed as controller-owned; the existing publisher keeps intents in batch work.
"""
from pathlib import Path
import re
import unicodedata
import batch_tool as b

MODE = 'source_case_files_v1'
SNAPSHOT = 'delivery-targets.snapshot.json'


def enabled(m):
    return m.get('policy', {}).get('delivery', {}).get('layout') == 'source_case_files'


def filename(folder):
    from output_contract import filename as exact_filename
    name = Path(folder).name
    if re.fullmatch(r'(?i)(CON|PRN|AUX|NUL|CONIN\$|CONOUT\$|COM[1-9¹²³]|LPT[1-9¹²³])', name.split('.')[0].rstrip(' ')):
        raise b.BatchError('Case folder name cannot be used unchanged as a Windows filename')
    return exact_filename(name)


def directory_identity(folder):
    folder = b.root_path(folder, required=True)
    value = folder.stat()
    if not value.st_ino: raise b.BatchError('Filesystem must provide stable directory identity')
    return {'device': value.st_dev, 'inode': value.st_ino}


def mapping(m):
    result = {}; occupied = set()
    for c in m['projects']:
        target = c.get('delivery_target')
        primary = b.clean_path(c['primary_source'], m['input'])
        directory = primary.parent
        if (not isinstance(target, dict) or set(target) != {'directory', 'filename', 'directory_identity'}
                or target['directory'] != str(directory) or target['filename'] != filename(directory)):
            raise b.BatchError('Frozen case delivery target changed')
        identity = target['directory_identity']
        if (not isinstance(identity, dict) or set(identity) != {'device', 'inode'}
                or any(type(v) is not int for v in identity.values()) or not identity['inode']):
            raise b.BatchError('Invalid frozen directory identity')
        key = unicodedata.normalize('NFC', str(directory / target['filename'])).casefold()
        if key in occupied or c['id'] in result:
            raise b.BatchError('Multiple cases resolve to the same delivery target; separate case folders before drafting')
        occupied.add(key); result[c['id']] = target
    return result


def freeze(root, cases):
    from flat_delivery import target_path
    for c in cases:
        folder = b.clean_path(c['primary_source'], root).parent
        c['delivery_target'] = {'directory': str(folder), 'filename': filename(folder),
                                'directory_identity': directory_identity(folder)}
    m = {'input': str(root), 'projects': cases}
    result = mapping(m)
    for target in result.values():
        path = target_path(Path(target['directory']), target['filename'])
        if path.exists():
            raise b.BatchError('Case final already exists; preserve it and resolve the conflict before drafting: ' + str(path))
    return result


def verify(m):
    expected = mapping(m)
    path = b.clean_path(Path(m['batch_dir']) / SNAPSHOT, m['batch_dir'])
    if not path.is_file() or b.read(path) != expected:
        raise b.BatchError('Frozen delivery targets do not match the batch snapshot')
    return expected


def destination(m, c):
    target = verify(m)[c['id']]
    # A missing, renamed, substituted or redirected original folder must never
    # be silently recreated or replaced by a different directory at this path.
    folder = b.clean_path(target['directory'], m['input'])
    if not folder.is_dir() or directory_identity(folder) != target['directory_identity']:
        raise b.BatchError('Case directory identity changed; preserve files and resolve the original folder: ' + str(folder))
    return folder
