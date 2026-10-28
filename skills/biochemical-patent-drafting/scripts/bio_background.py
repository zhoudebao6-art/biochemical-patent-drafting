"""No page fill, text highlight or Word shading in biochemical final drafts.

Clear direct properties and style/numbering defaults together to prevent
inherited fills returning. Scientific figure pixels and drawing fills are
source objects, not page formatting; retain them for independent visual review.
"""
from pathlib import Path
import hashlib,zipfile
from lxml import etree as ET

W='http://schemas.openxmlformats.org/wordprocessingml/2006/main'
TAGS={'{'+W+'}'+name for name in ('background','shd','highlight')}

def selected_parts(names):
    return [n for n in names if n.startswith('word/') and n.endswith('.xml') and '/embeddings/' not in n]

def root_hits(root,part):
    return [{'part':part,'element':ET.QName(n).localname,'attributes':dict(n.attrib)} for n in root.iter() if n.tag in TAGS]

def scan_package(z,artifact_sha,root_reader=None):
    root_reader=root_reader or (lambda name: ET.fromstring(z.read(name)))
    parts=selected_parts(z.namelist());hits=[]
    for name in parts:hits.extend(root_hits(root_reader(name),name))
    return {'schema_version':1,'artifact_sha256':artifact_sha,'complete':'word/document.xml' in parts,
            'scanned_parts':parts,'issues':hits,
            'scope':'Word page background, paragraph/run/table/cell shading and highlights, including style and numbering inheritance. Figure pixels, drawing fills and app display mode require visual review; source scientific objects are preserved.'}

def scan_docx(path):
    path=Path(path)
    with zipfile.ZipFile(path) as z:return scan_package(z,hashlib.sha256(path.read_bytes()).hexdigest())

def normalize_root(root,part):
    changes=[]
    for node in list(root.iter()):
        if node.tag in TAGS:
            changes.append({'part':part,'element':ET.QName(node).localname})
            node.getparent().remove(node)
    return changes

def normalize(path):
    from bio_package import normalize as normalize_package
    return normalize_package(path,('background',))['background']
