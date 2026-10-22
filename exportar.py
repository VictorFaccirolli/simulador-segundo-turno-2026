"""Exportações independentes da interface: PDF e cartão vertical 1080 x 1920."""
from io import BytesIO
from html import escape
from pathlib import Path
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, PageBreak
from PIL import Image as PILImage, ImageDraw, ImageFont
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from matplotlib import font_manager

pdfmetrics.registerFont(TTFont('DejaVu', font_manager.findfont(font_manager.FontProperties(family='DejaVu Sans'))))
pdfmetrics.registerFont(TTFont('DejaVu-Bold', font_manager.findfont(font_manager.FontProperties(family='DejaVu Sans', weight='bold'))))

def numero(v):
    return f'{v:,}'.replace(',', '.')

def percentual(v):
    return f'{v:.2f}%'.replace('.', ',')

def gerar_pdf(r, meta, figuras=()):
    out = BytesIO()
    doc = SimpleDocTemplate(out, pagesize=A4, rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40)
    styles = getSampleStyleSheet()
    for style in styles.byName.values():
        style.fontName = 'DejaVu-Bold' if 'Heading' in style.name or style.name == 'Title' else 'DejaVu'
    styles.add(ParagraphStyle(name='Azul', fontName='DejaVu-Bold', fontSize=22, leading=27, textColor=colors.HexColor('#153e60'), spaceAfter=14))
    story = []
    def texto(t, estilo='BodyText'):
        story.append(Paragraph(escape(str(t)), styles[estilo]))
        story.append(Spacer(1, 9))
    texto('SIMULADOR PRESIDENCIAL', 'Azul')
    texto('Segundo turno | Eleições 2026', 'Heading2')
    texto('Desenvolvido pelo Engenheiro Victor Faccirolli')
    texto('Participante: ' + meta['participante'], 'Heading2')
    texto('Cenário: ' + meta['cenario'])
    texto('Calculado em ' + meta['data'] + ' (Brasília)')
    texto((r['vencedor'] + ' venceria neste cenário.') if r['vencedor'] else 'Empate no cenário: 50% para cada candidato.', 'Heading2')
    key = 'Votos estimados' if r['modo']=='Percentuais' else 'Votos'
    rows = [['Candidato', 'Votos', '% dos válidos']]
    rows += [[l['Candidato'],numero(l[key]),percentual(l['% dos válidos'])] for l in r['linhas']]
    tabela = Table(rows, colWidths=[220,140,115])
    tabela.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#153e60')),('TEXTCOLOR',(0,0),(-1,0),colors.white),('FONTNAME',(0,0),(-1,0),'Helvetica-Bold'),('BACKGROUND',(0,1),(-1,-1),colors.HexColor('#eef5fb')),('BOTTOMPADDING',(0,0),(-1,-1),12),('TOPPADDING',(0,0),(-1,-1),12)]))
    story += [tabela,Spacer(1,18)]
    tabela.setStyle(TableStyle([('FONTNAME',(0,0),(-1,0),'DejaVu-Bold'),('FONTNAME',(0,1),(-1,-1),'DejaVu')]))
    texto('Diferença: ' + numero(abs(r['linhas'][0][key]-r['linhas'][1][key])) + ' votos | ' + percentual(abs(r['linhas'][0]['% dos válidos']-r['linhas'][1]['% dos válidos'])).replace('%',' pontos percentuais'))
    texto('Parâmetros e participação', 'Heading2')
    for label, value in [('Eleitorado de referência',numero(r['eleitorado'])),('Abstenção',percentual(r['abstencao_pct'])+' | '+numero(r['ausentes'])+' ausentes'),('Comparecimento',numero(r['comparecimento'])),('Votos válidos',numero(r['validos_qtd'])),('Brancos',numero(r['brancos_qtd'])),('Nulos',numero(r['nulos_qtd']))]:
        texto(label+': '+value)
    texto('Entradas ('+r['modo']+'): '+ '; '.join(l['Candidato']+' = '+str(l['Valor informado']) for l in r['linhas'])+'; Brancos = '+str(r['brancos'])+'; Nulos = '+str(r['nulos']))
    texto('Simulação pessoal, não é pesquisa eleitoral nem previsão. Base de eleitores mantida do projeto anterior, pendente de conferência antes da publicação. Votos inteiros estimados por maiores restos; decisão e percentuais usam as entradas não arredondadas para exibição.')
    for i,fig in enumerate(figuras):
        if i==0 or i==1:
            story.append(PageBreak())
        buf=BytesIO(); fig.savefig(buf,format='png',dpi=130,bbox_inches='tight'); buf.seek(0)
        w,h=PILImage.open(buf).size; buf.seek(0)
        story.append(Image(buf,width=495,height=495*h/w))
        story.append(Spacer(1,14))
    def rodape(canvas, doc):
        canvas.setFont('Helvetica',8); canvas.setFillColor(colors.HexColor('#52697a'))
        canvas.drawString(40,24,'Simulação pessoal | Eng. Victor Faccirolli')
        canvas.drawRightString(A4[0]-40,24,str(doc.page))
    doc.build(story,onFirstPage=rodape,onLaterPages=rodape)
    return out.getvalue()

def gerar_story(r, meta):
    img=PILImage.new('RGB',(1080,1920),'#f1f6fa'); d=ImageDraw.Draw(img)
    # Matplotlib distribui DejaVu Sans também em Windows e no Streamlit Cloud.
    from matplotlib import font_manager
    def font(size,bold=False):
        return ImageFont.truetype(font_manager.findfont(font_manager.FontProperties(family='DejaVu Sans',weight='bold' if bold else 'normal')),size)
    def write(text,y,size=30,fill='#18354b',bold=False):
        f=font(size,bold)
        while d.textbbox((0,0),text,font=f)[2]>920 and size>12:
            size-=1; f=font(size,bold)
        d.text((80,y),text,font=f,fill=fill)
    d.rectangle((0,0,1080,440),fill='#123b56')
    write('ELEIÇÕES 2026',82,28,'#94d9d0',True)
    write('Meu cenário',145,66,'white',True)
    write('Segundo turno',235,46,'white',True)
    write('SIMULAÇÃO PESSOAL',335,25,'#94d9d0')
    write(meta['participante'],495,46,bold=True)
    write(meta['cenario'],565,28)
    write(meta['data']+' • Brasília',620,24)
    key='Votos estimados' if r['modo']=='Percentuais' else 'Votos'
    for i,l in enumerate(r['linhas']):
        y=715+i*290
        d.rounded_rectangle((60,y,1020,y+250),radius=25,fill='white')
        write(l['Candidato'],y+25,36,bold=True)
        write(percentual(l['% dos válidos']),y+83,66, '#168b86' if 'Flávio' in l['Candidato'] else '#486ab4',True)
        write(numero(l[key])+' votos • % dos válidos',y+180,26)
    write('Venceria: '+r['vencedor'] if r['vencedor'] else 'Empate no cenário',1340,34,bold=True)
    write('Abstenção: '+percentual(r['abstencao_pct']),1420,29)
    write('Brancos e nulos: '+percentual((r['brancos']+r['nulos'])/r['total']*100)+' de quem comparece',1475,27)
    write('Eleitorado de referência: '+numero(r['eleitorado']),1530,27)
    write('Compare seu cenário com amigos e familiares.',1615,28,bold=True)
    write('Não é pesquisa eleitoral nem previsão.',1680,25)
    write('Base do projeto anterior; conferência pendente.',1720,22)
    d.rectangle((0,1795,1080,1920),fill='#123b56')
    write('Desenvolvido pelo Engenheiro',1820,24,'#c7dbe5')
    write('Victor Faccirolli',1860,30,'white',True)
    out=BytesIO(); img.save(out,format='PNG'); return out.getvalue()
