from io import BytesIO
from pathlib import Path
import json
import base64
from html import escape
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import streamlit as st
from exportar import gerar_pdf, gerar_story
from datetime import datetime
from zoneinfo import ZoneInfo
from calculo import calcular, participacao, ELEITORADO, FONTE_ELEITORADO

st.set_page_config(page_title='Simulador Presidencial — Segundo Turno', page_icon='📊', layout='wide')
st.markdown("""<style>
.block-container{padding-top:2.5rem;max-width:1200px}h1{color:#153e60;font-size:clamp(1.75rem,3.2vw,2.65rem)!important;line-height:1.18!important}
div[data-testid="stMetric"]{background:#eef5fb;border-radius:12px;padding:12px}
.author-banner{background:linear-gradient(110deg,#102f49,#1c5470);border-left:5px solid #6bd0bd;border-radius:14px;padding:14px 20px;margin:0 0 20px;color:white;box-shadow:0 5px 20px #102f4910}
.author-eyebrow{font-family:Arial,sans-serif;font-size:11px;letter-spacing:2.2px;font-weight:700;color:#a9ded9;margin-bottom:5px}
.author-name{font-family:Georgia,'Times New Roman',serif;font-size:clamp(1rem,1.6vw,1.2rem);font-weight:700;line-height:1.3}
.author-detail{font-family:Arial,sans-serif;font-size:12px;color:#c7dbe5;margin-top:7px}
.candidate-card{display:flex;gap:14px;align-items:center;margin:14px 0 4px;padding:12px;border:1px solid #e0e9ef;border-radius:12px;background:#f4f8fb;color:#18354b}
.candidate-photo{width:66px;height:88px;object-fit:contain;border-radius:6px;background:white;flex-shrink:0}
.candidate-placeholder{width:66px;height:88px;display:flex;align-items:center;justify-content:center;border-radius:6px;background:#e0e9ef;font-size:28px}
.candidate-name{font-weight:700;font-size:16px}.candidate-detail{font-size:12px;color:#52697a;margin-top:4px}
.winner-card{display:flex;align-items:center;gap:24px;padding:24px;margin:18px 0;background:#e7f4f0;border:1px solid #b5dcd0;border-radius:16px;color:#18354b}
.winner-card img{width:100px;height:132px;object-fit:contain;background:white;border-radius:10px;flex-shrink:0}
.winner-label{font-size:12px;font-weight:700;letter-spacing:1px;color:#246958;margin-bottom:8px}
.winner-message{font-size:clamp(1.1rem,2vw,1.4rem);line-height:1.5}
.results-scroll{overflow-x:auto;margin:18px 0 24px}.results-table{width:100%;border-collapse:collapse;color:#18354b;background:white}
.results-table th{background:#eef5fb;text-align:left;font-size:13px;padding:14px;white-space:nowrap}
.results-table td{padding:12px 14px;border-bottom:1px solid #e0e9ef;white-space:nowrap}
.results-table .result-person{display:flex;align-items:center;gap:12px;font-weight:600}
.results-table img{width:48px;height:64px;object-fit:contain;border-radius:6px;background:#f4f8fb}
@media(max-width:640px){.winner-card{padding:16px;gap:14px}.winner-card img{width:75px;height:100px}}
@media(max-width:640px){.author-banner{padding:14px}.candidate-card{gap:10px}.candidate-name{font-size:14px}}
</style>""", unsafe_allow_html=True)
st.markdown('<div class="author-banner"><div class="author-eyebrow">DESENVOLVIDO POR</div><div class="author-name">Eng. Victor Faccirolli</div><div class="author-detail">Eleições 2026 • Segundo turno • Versão 2.0</div></div>', unsafe_allow_html=True)
st.title('Simulador Presidencial — Segundo Turno')
st.write('Monte seu cenário com abstenção, votação dos candidatos, brancos e nulos. Veja as quantidades estimadas, os votos válidos e o resultado do seu cenário de segundo turno. Salve e compare com amigos e familiares.')
st.caption('Simulação baseada nos valores informados pelo usuário. Não é pesquisa eleitoral nem previsão estatística.')
st.metric('Eleitorado de referência do projeto anterior', f'{ELEITORADO:,}'.replace(',', '.'))
st.caption('Base mantida do simulador anterior. Conferência do eleitorado oficial pendente antes da publicação.')
base = Path(__file__).parent
fotos = json.loads((base / 'fotos.json').read_text(encoding='utf-8'))
nomes = ['Lula (PT)', 'Flávio Bolsonaro (PL)']
def foto_resultado(nome):
    cadastro = fotos.get(nome)
    if not cadastro or not (base / cadastro['foto']).is_file():
        return ''
    dados = base64.b64encode((base / cadastro['foto']).read_bytes()).decode('ascii')
    return f'<img src="data:image/jpeg;base64,{dados}" alt="Foto de {escape(nome)}">'

def numero_br(valor, casas=0):
    return f'{valor:,.{casas}f}'.replace(',', '_').replace('.', ',').replace('_', '.')

modo = st.radio('Como deseja preencher?', ['Percentuais', 'Votos'], horizontal=True)
st.caption('Percentuais: candidatos + brancos + nulos devem somar 100% de quem comparece. A abstenção é informada separadamente, como percentual do eleitorado apto. Votos: a soma deve corresponder ao comparecimento estimado.')
abstencao = st.number_input('Abstenção estimada (% do eleitorado apto)', min_value=0.0, max_value=100.0, value=21.0, step=0.1, format='%.2f', help='Percentual de pessoas aptas que não irão votar. Ex.: 20% reduz o comparecimento para 80% do eleitorado. Não some este percentual aos candidatos, brancos e nulos.')
ausentes, presentes = participacao(abstencao)
c1, c2 = st.columns(2)
c1.metric('Ausentes estimados', f'{ausentes:,}'.replace(',', '.'))
c2.metric('Comparecimento estimado', f'{presentes:,}'.replace(',', '.'))
with st.form('cenario'):
    participante = st.text_input('Seu nome (obrigatório)', max_chars=60, placeholder='Ex.: Victor')
    titulo = st.text_input('Nome do cenário (opcional)', max_chars=80, placeholder='Ex.: Meu palpite para o segundo turno')
    cols = st.columns(2)
    entradas = {}
    for i, nome in enumerate(nomes):
        with cols[i % 2]:
            cadastro = fotos.get(nome)
            if cadastro and (base / cadastro['foto']).is_file():
                b64 = base64.b64encode((base / cadastro['foto']).read_bytes()).decode('ascii')
                retrato = f'<img class="candidate-photo" src="data:image/jpeg;base64,{b64}" alt="Foto de {escape(nome)}">'
                detalhe = f"Número {cadastro['numero']} • Foto do projeto original"
            else:
                retrato = '<div class="candidate-placeholder">👤</div>'
                detalhe = 'Foto não cadastrada'
            st.markdown(f'<div class="candidate-card">{retrato}<div><div class="candidate-name">{escape(nome)}</div><div class="candidate-detail">{escape(detalhe)}</div></div></div>', unsafe_allow_html=True)
            entradas[nome] = st.number_input(nome, min_value=0.0 if modo == 'Percentuais' else 0, max_value=100.0 if modo == 'Percentuais' else 1000000000, value=0.0 if modo == 'Percentuais' else 0, step=0.1 if modo == 'Percentuais' else 1000, format='%.2f' if modo == 'Percentuais' else '%d', key=f'{modo}_{nome}', help='Informe o percentual entre quem comparece, ou a quantidade de votos deste candidato. Zero significa nenhum voto neste cenário.')
    cols = st.columns(2)
    extras = []
    for col, label in zip(cols, ['Brancos', 'Nulos']):
        with col:
            extras.append(st.number_input(label, min_value=0.0 if modo == 'Percentuais' else 0, max_value=100.0 if modo == 'Percentuais' else 1000000000, value=0.0 if modo == 'Percentuais' else 0, step=0.1 if modo == 'Percentuais' else 1000, format='%.2f' if modo == 'Percentuais' else '%d', key=f'{modo}_{label}', help='Informe o percentual entre quem comparece, ou a quantidade de votos. Brancos e nulos não são votos válidos.'))
    enviar = st.form_submit_button('Calcular resultado e gerar gráficos', type='primary', width='stretch')
if enviar:
    try:
        if not participante.strip():
            raise ValueError('Preencha seu nome para identificar o resultado.')
        r = calcular(entradas, *extras, modo=modo, abstencao_pct=abstencao)
        st.session_state['resultado'] = r
        st.session_state['titulo_resultado'] = titulo.strip() or 'Meu cenário'
        st.session_state['participante_resultado'] = participante.strip()
        st.session_state['data_resultado'] = datetime.now(ZoneInfo('America/Sao_Paulo')).strftime('%d/%m/%Y %H:%M')
    except ValueError as e:
        st.session_state.pop('resultado', None)
        st.error(str(e))
r = st.session_state.get('resultado')
if r:
    st.divider()
    st.subheader(st.session_state['titulo_resultado'])
    st.write('Participante: ' + st.session_state['participante_resultado'])
    st.caption('Calculado em ' + st.session_state['data_resultado'] + ' (horário de Brasília)')
    st.caption('Resultado do último cálculo. Após alterar os campos, clique em Calcular novamente.')
    participacao_cols = st.columns(3)
    participacao_cols[0].metric('Abstenção do cenário', f"{r['abstencao_pct']:.2f}%", f"{r['ausentes']:,} ausentes".replace(',', '.'), delta_color='off')
    participacao_cols[1].metric('Comparecimento do cenário', f"{r['comparecimento']:,}".replace(',', '.'))
    participacao_cols[2].metric('Votos válidos estimados', f"{r['validos_qtd']:,}".replace(',', '.'))
    cols = st.columns(3)
    cols[0].metric('Válidos (% de quem comparece)', f"{r['validos']/r['total']*100:.2f}%")
    cols[1].metric('Brancos e nulos (% de quem comparece)', f"{(r['brancos']+r['nulos'])/r['total']*100:.2f}%")
    cols[2].metric('Líder (% dos válidos)', f"{r['linhas'][0]['% dos válidos']:.2f}%")
    qtd_chave = 'Votos estimados' if r['modo'] == 'Percentuais' else 'Votos'
    if r['vencedor']:
        lider = next(linha for linha in r['linhas'] if linha['Candidato'] == r['vencedor'])
        percentual_lider = numero_br(lider['% dos válidos'], 2)
        votos_lider = numero_br(lider[qtd_chave])
        mensagem = f"Neste cenário, {r['vencedor']} venceria as eleições com {percentual_lider}% dos votos válidos, totalizando {votos_lider} votos."
        st.markdown(f'<div class="winner-card">{foto_resultado(r["vencedor"])}<div><div class="winner-label">VENCEDOR NESTE CENÁRIO</div><div class="winner-message">Neste cenário, <strong>{escape(r["vencedor"])}</strong> venceria as eleições com <strong>{percentual_lider}% dos votos válidos</strong>, totalizando <strong>{votos_lider} votos</strong>.</div></div></div>', unsafe_allow_html=True)
    else:
        mensagem = 'Empate no cenário: 50% dos votos válidos para cada candidato.'
        st.warning(mensagem)
    diferenca = abs(r['linhas'][0][qtd_chave] - r['linhas'][1][qtd_chave])
    st.metric('Diferença entre os candidatos', f'{diferenca:,} votos'.replace(',', '.'), f"{abs(r['linhas'][0]['% dos válidos'] - r['linhas'][1]['% dos válidos']):.2f} pontos percentuais", delta_color='off')
    if r['modo'] == 'Percentuais':
        st.caption('Quantidades estimadas arredondadas por maiores restos para preservar a soma. Os percentuais e a decisão usam os percentuais originais, sem arredondamento.')
    st.caption('Empates são exibidos sem declarar vencedor. Percentuais exibidos com duas casas decimais.')
    df = pd.DataFrame(r['linhas'])
    cabecalhos = ['Candidato', 'Valor informado', '% do total', '% dos válidos', qtd_chave]
    linhas_html = []
    for linha in r['linhas']:
        pessoa = f'<div class="result-person">{foto_resultado(linha["Candidato"])}<span>{escape(linha["Candidato"])}</span></div>'
        valores = [pessoa, numero_br(linha['Valor informado'], 2 if r['modo'] == 'Percentuais' else 0), numero_br(linha['% do total'], 2) + '%', numero_br(linha['% dos válidos'], 2) + '%', numero_br(linha[qtd_chave])]
        linhas_html.append('<tr>' + ''.join(f'<td>{valor}</td>' for valor in valores) + '</tr>')
    st.markdown('<div class="results-scroll"><table class="results-table"><thead><tr>' + ''.join(f'<th>{escape(titulo)}</th>' for titulo in cabecalhos) + '</tr></thead><tbody>' + ''.join(linhas_html) + '</tbody></table></div>', unsafe_allow_html=True)
    plt.rcParams.update({'font.family': 'DejaVu Sans', 'axes.spines.top': False, 'axes.spines.right': False})
    fig, ax = plt.subplots(figsize=(11, max(5, len(df)*.42)))
    ax.barh(df['Candidato'][::-1], df['% dos válidos'][::-1], color=['#168b86' if 'Flávio' in n else '#486ab4' for n in df['Candidato'][::-1]])
    ax.axvline(50, color='#c27718', linestyle='--', label='50%: é necessário superar esta marca')
    for i, v in enumerate(df['% dos válidos'][::-1]):
        ax.text(v + .7, i, f'{v:.2f}%', va='center', fontsize=9)
    ax.set_xlim(0, 110); ax.set_xlabel('% dos votos válidos'); ax.set_title('Votação por candidato — votos válidos', loc='left', pad=18)
    ax.legend(loc='lower right', fontsize=8)
    fig.text(.99, .01, 'Simulação do usuário • Desenvolvido por Victor Faccirolli', ha='right', fontsize=8, color='#666666')
    fig.tight_layout(rect=(0,.04,1,1))
    st.pyplot(fig)
    fig2, ax2 = plt.subplots(figsize=(8,4.5))
    ax2.bar(['Válidos','Brancos','Nulos'], [r['validos']/r['total']*100,r['brancos']/r['total']*100,r['nulos']/r['total']*100], color=['#247a99','#9aabb5','#56616b'])
    for p in ax2.patches:
        ax2.annotate(f'{p.get_height():.2f}%', (p.get_x()+p.get_width()/2,p.get_height()), ha='center', va='bottom')
    ax2.set_ylim(0,110); ax2.set_ylabel('% de quem comparece'); ax2.set_title('Composição da votação', loc='left', pad=14)
    fig2.tight_layout(); st.pyplot(fig2)
    fig3, ax3 = plt.subplots(figsize=(9,5))
    valores = [r['validos_qtd'], r['brancos_qtd'], r['nulos_qtd'], r['ausentes']]
    ax3.bar(['Válidos', 'Brancos', 'Nulos', 'Abstenção'], [v/r['eleitorado']*100 for v in valores], color=['#247a99','#9aabb5','#56616b','#c27718'])
    for p, v in zip(ax3.patches, valores):
        ax3.annotate(f"{v/r['eleitorado']*100:.2f}%\n{v:,}".replace(',', '.'), (p.get_x()+p.get_width()/2, p.get_height()), ha='center', va='bottom', fontsize=9)
    ax3.set_ylim(0,115); ax3.set_ylabel('% do eleitorado apto'); ax3.set_title('Eleitorado: participação e abstenção', loc='left', pad=14)
    fig3.text(.99,.01,'Simulação do usuário • Eng. Victor Faccirolli',ha='right',fontsize=8,color='#666666')
    fig3.tight_layout(rect=(0,.04,1,1)); st.pyplot(fig3)
    st.subheader('Salve seu resultado e compare')
    st.caption('Os arquivos identificam o participante e os valores do último cálculo. Não há ranking público nem armazenamento permanente dos palpites.')
    meta = dict(participante=st.session_state['participante_resultado'], cenario=st.session_state['titulo_resultado'], data=st.session_state['data_resultado'])
    pdf = gerar_pdf(r, meta, [fig, fig2, fig3])
    story = gerar_story(r, meta)
    dc1, dc2 = st.columns(2)
    dc1.download_button('Baixar resultado em PDF', pdf, 'meu_cenario_segundo_turno.pdf', 'application/pdf', type='primary')
    dc2.download_button('Baixar imagem para Stories / WhatsApp', story, 'meu_cenario_story.png', 'image/png')
    for i, figura in enumerate([fig, fig2, fig3], 1):
        buffer = BytesIO(); figura.savefig(buffer, format='png', dpi=200, bbox_inches='tight')
        st.download_button(f'Baixar gráfico {i} (PNG)', buffer.getvalue(), f'grafico_{i}.png', 'image/png', key=f'png{i}')
        plt.close(figura)
    st.download_button('Baixar tabela (CSV)', df.to_csv(index=False,sep=';',decimal=',').encode('utf-8-sig'), 'resultado.csv', 'text/csv')
    resumo = dict(**meta, resultado=mensagem, **r)
    st.download_button('Baixar cenário e resultado (JSON)', json.dumps(resumo, ensure_ascii=False, indent=2), 'cenario.json', 'application/json')
with st.expander('Como o cálculo funciona'):
    st.write('Votos válidos = soma dos votos dos candidatos. Percentual válido = votos do candidato ÷ votos válidos × 100. Neste cenário de dois candidatos, a vitória exige mais de 50% dos votos válidos. Brancos e nulos não entram no denominador. Abstenção é o não comparecimento e também não entra. Com a distribuição percentual mantida, mudar apenas a abstenção altera as quantidades estimadas, mas não altera os percentuais válidos dos candidatos.')
    st.markdown('[Regras e informações do TSE](https://www.tse.jus.br/comunicacao/noticias/2022/Outubro/votos-em-branco-ou-nulos-nao-sao-transferidos-para-o-vencedor-nem-cancelam-uma-eleicao) · [DivulgaCandContas](https://divulgacandcontas.tse.jus.br/)')
