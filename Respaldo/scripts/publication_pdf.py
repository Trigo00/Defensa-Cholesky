"""Publicación A4 con portada, índice navegable y jerarquía editorial."""
from pathlib import Path
import re
from io import BytesIO
from xml.sax.saxutils import escape
import matplotlib
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import (BaseDocTemplate,PageTemplate,Frame,Paragraph,Spacer,
    Image,Table,TableStyle,PageBreak,KeepTogether,CondPageBreak)
from reportlab.platypus.tableofcontents import TableOfContents

INK='#163b50';TEAL='#188579';WIDTH=A4[0]-104

class Report(BaseDocTemplate):
    def afterFlowable(self,f):
        if isinstance(f,Paragraph) and hasattr(f,'toc_title'):
            self.canv.bookmarkPage(f.key)
            self.canv.addOutlineEntry(f.toc_title,f.key,level=0,closed=False)
            self.notify('TOCEntry',(0,f.toc_title,self.page,f.key))

def publish(root,text):
    fonts=Path(matplotlib.get_data_path())/'fonts/ttf'
    for name,file in [('DV','DejaVuSans.ttf'),('DVB','DejaVuSans-Bold.ttf'),('DVI','DejaVuSans-Oblique.ttf')]:
        pdfmetrics.registerFont(TTFont(name,str(fonts/file)))
    pdfmetrics.registerFontFamily('DV',normal='DV',bold='DVB',italic='DVI',boldItalic='DVB')
    styles={
        'body':ParagraphStyle('body',fontName='DV',fontSize=9.4,leading=14.1,spaceAfter=8,allowWidows=0,allowOrphans=0,textColor=colors.HexColor('#253c48')),
        'h1':ParagraphStyle('h1',fontName='DVB',fontSize=17,leading=22,spaceBefore=17,spaceAfter=12,keepWithNext=True,textColor=colors.HexColor(INK)),
        'h2':ParagraphStyle('h2',fontName='DVB',fontSize=11.5,leading=16,spaceBefore=12,spaceAfter=8,keepWithNext=True,textColor=colors.HexColor(INK)),
        'caption':ParagraphStyle('caption',fontName='DV',fontSize=8.3,leading=11.8,spaceAfter=13,textColor=colors.HexColor('#526675')),
        'cell':ParagraphStyle('cell',fontName='DV',fontSize=7.6,leading=10.5),
        'title':ParagraphStyle('title',fontName='DVB',fontSize=34,leading=40,textColor=colors.HexColor(INK),spaceAfter=20),
        'deck':ParagraphStyle('deck',fontName='DV',fontSize=16,leading=24,textColor=colors.HexColor(INK),spaceAfter=22),
        'formula':ParagraphStyle('formula',fontName='DV',fontSize=13,leading=23,alignment=1,spaceBefore=10,spaceAfter=14,textColor=colors.HexColor(INK))}
    def markup(t):
        t=escape(t).replace('ᵀ','<super>T</super>').replace('²','<super>2</super>').replace('³','<super>3</super>')
        t=t.replace('&lt;br/&gt;','<br/>').replace('&lt;br&gt;','<br/>').replace('\n','<br/>')
        t=re.sub(r'`([^`]+)`',r'<font color="#36596c">\1</font>',t)
        t=re.sub(r'\*\*(.+?)\*\*',r'<b>\1</b>',t)
        t=re.sub(r'\*([^*]+)\*',r'<i>\1</i>',t)
        return re.sub(r'\[([^\]]+)\]\(([^)]+)\)',lambda m:f'<link href="{m[2]}" color="{TEAL}">{m[1]}</link>' if m[2].startswith('http') else m[1],t)
    def p(t,style='body'):return Paragraph(markup(t),styles[style])
    story=[Spacer(1,48),p('INVESTIGACIÓN EXPERIMENTAL · HPC','h2'),Spacer(1,14),p('Cholesky','title'),
        p('De la organización de memoria<br/>a la evaluación de MPI frente a LAPACK','deck'),
        Spacer(1,16),p('Implementación en C · distribución MPI · referencia optimizada','body'),
        Spacer(1,24),
        p('**Facultad de Ciencias Exactas y Tecnología · Universidad Nacional de Tucumán**<br/>Cátedra de Computación de Alto Rendimiento','caption'),
        Spacer(1,32),p('21 de septiembre al 3 de octubre de 2026','h2'),
        p('Informe integral | Código, evidencia y resultados reproducibles'),Spacer(1,36),
        p('Pregunta central','h2'),p('Cuándo distribuir el trabajo reduce el tiempo y cuánto depende esa ventaja del kernel local y de la frontera de medición.','deck'),PageBreak()]
    story.append(p('Índice de lectura','h1'))
    toc=TableOfContents();toc.levelStyles=[ParagraphStyle('toc',fontName='DV',fontSize=9.1,leading=14,spaceBefore=6,textColor=colors.HexColor(INK))]
    story.append(toc)
    lines=text.splitlines();i=0;section=0;sub=0
    while i<len(lines):
        line=lines[i].strip()
        if not line or line.startswith('# ') or line.startswith('Informe de investigación experimental'):
            i+=1;continue
        if line.startswith('## '):
            section+=1;sub=0;title=line[3:]
            if title in ('Resultados principales','Resumen','Anexo A. Reconstrucción histórica y procedencia'):story.append(PageBreak())
            else:story.append(CondPageBreak(150))
            title=title if title.startswith('Anexo ') else f'{section}. {title}'
            h=p(title,'h1');h.toc_title=title;h.key=f'section-{section}';story.append(h);i+=1;continue
        if line.startswith('### '):
            sub+=1;story.append(p(f'{section}.{sub}. '+line[4:],'h2'));i+=1;continue
        if line.startswith('$$ '):
            from matplotlib.mathtext import math_to_image
            from matplotlib.font_manager import FontProperties
            stream=BytesIO()
            math_to_image('$'+line[3:].removesuffix(' $$')+'$',stream,
                          prop=FontProperties(size=13),dpi=220,format='png',color=INK)
            stream.seek(0);img=Image(stream)
            img.drawWidth*=72/220;img.drawHeight*=72/220
            if img.drawWidth>WIDTH:
                img.drawHeight*=WIDTH/img.drawWidth;img.drawWidth=WIDTH
            story.extend([Spacer(1,8),img,Spacer(1,14)]);i+=1;continue
        if line.startswith('|'):
            rr=[]
            while i<len(lines) and lines[i].startswith('|'):
                cells=[x.strip() for x in lines[i].strip().strip('|').split('|')]
                if not all(re.fullmatch(r':?-+:?',x) for x in cells):rr.append(cells)
                i+=1
            n=len(rr[0]);widths=[WIDTH/n]*n
            if rr[0][0]=='Campaña' and n==5:widths=[140,64,96,96,WIDTH-396]
            if n==2:widths=[WIDTH*.3,WIDTH*.7]
            table=Table([[p(c,'cell') for c in row] for row in rr],colWidths=widths,repeatRows=1,hAlign='LEFT')
            table.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#dbe9ef')),('VALIGN',(0,0),(-1,-1),'TOP'),('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,colors.HexColor('#f2f6f8')]),('TOPPADDING',(0,0),(-1,-1),7),('BOTTOMPADDING',(0,0),(-1,-1),7),('LINEBELOW',(0,0),(-1,0),.7,colors.HexColor(TEAL))]))
            story.extend([KeepTogether([table]) if len(rr)<=10 else table,Spacer(1,12)]);continue
        if line.startswith('!['):
            path=(root/'docs'/re.search(r'\]\(([^)]+)\)',line)[1]).resolve()
            img=Image(str(path));img.drawHeight*=WIDTH/img.drawWidth;img.drawWidth=WIDTH
            i+=1
            while i<len(lines) and not lines[i].strip():i+=1
            group=[img,Spacer(1,5)]
            if i<len(lines) and lines[i].startswith('Figura '):group.append(p(lines[i],'caption'));i+=1
            story.append(KeepTogether(group));continue
        parts=[line];i+=1
        while i<len(lines) and lines[i].strip() and not lines[i].startswith(('#','|','![','$$ ')):
            parts.append(lines[i].strip());i+=1
        story.append(p(' '.join(parts)))
    output=root/'output/pdf/Cholesky_Investigacion_Integral.pdf'
    def page(c,doc):
        if doc.page>1:
            c.setStrokeColor(colors.HexColor(TEAL));c.setLineWidth(1)
            c.line(52,A4[1]-33,A4[0]-52,A4[1]-33)
            c.setFont('DV',7);c.setFillColor(colors.HexColor('#526675'))
            c.drawString(52,A4[1]-25,'CHOLESKY  /  MEMORIA · MPI · LAPACK')
            c.drawString(52,25,'Investigación experimental · HPC Cholesky · Septiembre-octubre 2026')
            c.drawRightString(A4[0]-52,25,f'Página {doc.page}')
    doc=Report(str(output),pagesize=A4,title='Cholesky: investigación experimental integral',author='Agustín Trigo · Proyecto Cholesky HPC')
    doc.addPageTemplates(PageTemplate(id='report',frames=[Frame(52,46,WIDTH,A4[1]-98,leftPadding=0,rightPadding=0,topPadding=0,bottomPadding=0)],onPage=page))
    doc.multiBuild(story)
    return output

