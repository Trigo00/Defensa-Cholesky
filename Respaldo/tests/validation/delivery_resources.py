"""Inventario comprobable del Word, las imágenes y los paquetes conservados."""
from pathlib import Path, PurePosixPath
from urllib.parse import quote
from collections import defaultdict
import hashlib, zipfile, tarfile, xml.etree.ElementTree as ET, posixpath, json, csv

def digest(data):
    return hashlib.sha256(data).hexdigest()

def inspect_resources(root):
    docx=root/'output/Documentacion/Documentacion-Cholesky-HPC.docx'
    ns={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main',
        'r':'http://schemas.openxmlformats.org/officeDocument/2006/relationships'}
    contexts={}
    with zipfile.ZipFile(docx) as z:
        assert z.testzip() is None
        members=set(z.namelist())
        embedded=defaultdict(list)
        for name in members:
            if name.startswith('word/media/'):
                embedded[digest(z.read(name))].append(name)
        rels={}
        checked=0
        for name in members:
            if not name.endswith('.rels'):continue
            base=posixpath.dirname(posixpath.dirname(name))
            for rel in ET.fromstring(z.read(name)):
                if rel.attrib.get('TargetMode')=='External':continue
                target=rel.attrib['Target']
                resolved=posixpath.normpath(posixpath.join(base,target)).lstrip('/')
                assert resolved in members,(name,resolved)
                checked+=1
                if name=='word/_rels/document.xml.rels':rels[rel.attrib['Id']]=resolved
        doc=ET.fromstring(z.read('word/document.xml'))
        recent=[]
        for p in doc.findall('.//w:p',ns):
            text=''.join(t.text or '' for t in p.findall('.//w:t',ns)).strip()
            for node in p.iter():
                rid=node.attrib.get('{'+ns['r']+'}embed') or node.attrib.get('{'+ns['r']+'}id')
                if rid in rels and rels[rid].startswith('word/media/'):
                    contexts.setdefault(rels[rid],(text or ' / '.join(recent[-2:]))[:180])
            if text:recent.append(text)
    lines=['# Recursos actuales de presentación y evidencia','',
        'El [Word principal](../output/Documentacion/Documentacion-Cholesky-HPC.docx) es la referencia de presentación y se edita manualmente. Este índice se actualiza con el verificador de entrega. No modifica el Word ni sus imágenes.','',
        '## Imágenes conservadas','',
        'La correspondencia se verifica por SHA-256 del contenido, no por el nombre. El contexto se extrae del texto próximo en el XML del Word; sirve como pista de búsqueda y no certifica una ubicación visual ni una página.','',
        '| Imagen | Imagen idéntica incorporada al Word | Contexto textual próximo |','|---|---|---|']
    media=[]
    for p in sorted((root/'docs/media').iterdir()):
        if not p.is_file():continue
        h=digest(p.read_bytes());matches=sorted(embedded.get(h,[]))
        assert matches,('Imagen sin correspondencia exacta en Word',p)
        ctx=next((contexts[m] for m in matches if contexts.get(m)),'Sin contexto textual próximo')
        ctx=ctx.replace('|','/').replace('\n',' ')
        lines.append(f'| [{p.name}](media/{quote(p.name)}) | '+', '.join(matches)+f' | {ctx} |')
        media.append({'file':p.relative_to(root).as_posix(),'sha256':h,'embedded_matches':matches})
    unique=len({m['sha256'] for m in media})
    lines+=['',f'Se conservan {len(media)} archivos externos con {unique} contenidos distintos. El Word también contiene recursos embebidos que no tienen copia externa.','',
        '## Evidencia del clúster','',
        'Los siguientes nombres son miembros internos de paquetes tar.gz, no rutas extraídas. Pueden consultarse con `tar -tf paquete.tar.gz` y leerse con `tar -xOf paquete.tar.gz miembro`. Los registros de entorno, compilación y afinidad no equivalen a una transcripción completa de los comandos.','']
    archives=[]
    audits={a['archive']:a for a in json.loads((root/'data/processed/audit.json').read_text())}
    with (root/'data/processed/verified_hashes.csv').open(encoding='utf-8') as f:
        manifests=list(csv.DictReader(f))
    for p in sorted((root/'data/raw/cluster').glob('*.tar.gz')):
        with tarfile.open(p) as t:
            assert digest(p.read_bytes())==audits[p.name]['sha256'],('Paquete distinto del analizado',p.name)
            for h in manifests:
                if h['archive']==p.name:
                    assert digest(t.extractfile(h['member']).read())==h['sha256'],h
            files=[m for m in t.getmembers() if m.isfile()]
            # Read every member to check archive readability, without extraction.
            for m in files:
                with t.extractfile(m) as f:
                    while f.read(1024*1024):pass
            selected=[m.name for m in files if m.name.endswith('.sh') or any(k in m.name.lower() for k in ('entorno','binding','build','protocolo','host'))]
            scripts=[m.name for m in files if m.name.endswith('.sh')]
        lines += [f'### {p.name}','',f'[Paquete original](../data/raw/cluster/{p.name}) · {len(files)} archivos internos.','']
        lines += [f'- `{m}`' for m in selected] or ['- No hay registros de entorno/compilación/afinidad identificados por nombre en este paquete; consultar sus CSV y demás miembros.']
        lines += ['', 'Lanzadores .sh conservados: '+(', '.join(scripts) if scripts else 'ninguno en este paquete.') ,'']
        archives.append({'file':p.name,'sha256':digest(p.read_bytes()),'members_read':len(files),'shell_scripts':scripts})
    (root/'docs/recursos_actuales.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    return {'docx_sha256':digest(docx.read_bytes()),'docx_internal_relationships_checked':checked,'external_images':len(media),'unique_external_images':unique,'image_correspondence':media,'archives':archives}
