from pathlib import Path
from zipfile import ZipFile
from lxml import etree
import shutil

path = Path('output/pdf/Cholesky_Investigacion_Integral.docx')
backup = Path('tmp/revision/Cholesky_Investigacion_Integral_antes.docx')
shutil.copy2(path, backup)
changes = [
(' La reconstrucción histórica se conserva en el anexo A.', ''),
('Datos de summary_all.csv, métrica seconds, cohorte principal local (.).', 'Datos de data/processed/summary_all.csv, métrica seconds, correspondientes a la campaña local.'),
('Las versiones actuales de los fuentes candidatos coinciden byte a byte con las instantáneas incluidas en las campañas del clúster.', 'Los paquetes conservan las instantáneas de los fuentes utilizados en cada campaña. Los archivos actuales incorporan una refactorización didáctica posterior y no coinciden byte a byte con esas versiones. Los resultados corresponden a los fuentes archivados; su conservación permite identificar el código medido. La evolución del código se describe en docs/inventario_tecnico.md.'),
('Parte del contexto de afinidad y cgroup solo aparece en la bitácora; el informe distingue esas transcripciones del contenido original del tar. Las tablas reconstruidas inicialmente tenían valores redondeados; para recalcular se utilizan los CSV originales recibidos después.', 'El paquete preformal conserva los CSV y los fuentes, pero no un registro completo de afinidad y cgroup. Las tablas iniciales tenían valores redondeados; los cálculos actuales utilizan los CSV originales de data/raw/cluster/evidencia_preformal_20260928.tar.gz. docs/recursos_actuales.md identifica los registros disponibles en cada paquete.'),
('La reparación propuesta usa una variable local distinta; los nombres posteriores están normalizados, pero no se presenta como inspeccionado un script corregido que no se archivó.', 'La corrección propuesta consiste en usar una variable local distinta. Los nombres posteriores están normalizados, pero el script corregido no se conservó y esa modificación no puede verificarse directamente.'),
('La evidencia respondió el objetivo universitario de distinguir rendimiento algorítmico y beneficio completo sin necesidad de agotar todos los procesos ofrecidos por el portal. Una asignación mayor permitiría otro experimento, pero no cambia retrospectivamente la cuota de esta campaña.', 'La campaña permitió distinguir la aceleración de la aplicación del beneficio del comando completo con la cuota de seis CPUs equivalentes disponible en esa sesión. Una asignación mayor requiere una campaña independiente, como la extensión del 03/10.'),
('Los CSV principales no exportan valid ni código de salida, por lo que no se inventa un estado del shell aunque las comprobaciones numéricas sean satisfactorias.', 'Los CSV principales no exportan valid ni código de salida. La comprobación numérica se apoya en los residuos y las diferencias del factor; estos datos no permiten verificar por sí solos el estado de salida del comando.'),
('La preparación mediante Conda y la reinstalación tras reiniciar la instancia forman parte del relato operativo recibido. Los archivos finales verifican la presencia y versiones de las dependencias, pero no contienen un historial íntegro de instalación ni una prueba independiente de qué directorios se restablecieron. La guía de reproducibilidad presenta esa distinción y recomienda verificar las dependencias de cada instancia.', 'Los registros de entorno conservados identifican la presencia y las versiones de las dependencias utilizadas. No incluyen el historial completo de instalación mediante Conda ni permiten determinar qué directorios se restablecieron al reiniciar la instancia. docs/recursos_actuales.md enumera los registros disponibles; docs/guia_paso_a_paso_experimentos.md describe la ejecución de los bancos. Antes de repetir una campaña, deben verificarse las dependencias de la nueva sesión.'),
('El diagnóstico preformal de N=4096 también registró incrementos, conservados en la bitácora.', 'El diagnóstico preformal de N=4096 conserva mediciones en evidencia_preformal_20260928.tar.gz, pero el paquete no contiene los contadores necesarios para verificar sus incrementos de throttling.'),
('El alcance experimental queda cerrado con esas respuestas, su validación y sus límites. No es necesario ampliar recursos ni realizar otra campaña para sostener las conclusiones actuales. Una ampliación debería responder una pregunta nueva y conservar la comparación contemporánea, los relojes explícitos y la evidencia original.', 'Las campañas realizadas permiten responder las preguntas planteadas dentro del alcance estudiado. Una ampliación puede evaluar nuevas condiciones o comprobar la estabilidad de los resultados en otras sesiones, manteniendo referencias contemporáneas, relojes explícitos y la evidencia original.'),
]
with ZipFile(path) as source:
    entries = [(info, source.read(info.filename)) for info in source.infolist()]
root = etree.fromstring(dict((i.filename, b) for i, b in entries)['word/document.xml'])
ns = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
for old, new in changes:
    matches = []
    for p in root.xpath('//w:body/w:p', namespaces=ns):
        nodes = p.xpath('.//w:t', namespaces=ns)
        text = ''.join(n.text or '' for n in nodes)
        if old in text:
            matches.append((nodes, text.index(old)))
    assert len(matches) == 1, (old, len(matches))
    nodes, start = matches[0]
    end = start + len(old)
    cursor = 0
    inserted = False
    for node in nodes:
        text = node.text or ''
        stop = cursor + len(text)
        if stop > start and cursor < end:
            a, b = max(0, start-cursor), min(len(text), end-cursor)
            node.text = text[:a] + (new if not inserted else '') + text[b:]
            node.set('{http://www.w3.org/XML/1998/namespace}space', 'preserve')
            inserted = True
        cursor = stop
doc = etree.tostring(root, encoding='UTF-8', xml_declaration=True, standalone=True)
temporary = path.with_suffix('.editing.docx')
with ZipFile(temporary, 'w') as target:
    for info, data in entries:
        target.writestr(info, doc if info.filename == 'word/document.xml' else data)
temporary.replace(path)
with ZipFile(path) as z:
    assert z.testzip() is None
    assert all(z.read(info.filename) == data for info, data in entries if info.filename != 'word/document.xml')
print(f'Updated {len(changes)} passages; all other DOCX members preserved.')
