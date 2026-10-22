"""Cálculo exato: a decisão nunca usa percentuais arredondados."""
from decimal import Decimal, ROUND_HALF_UP

ELEITORADO = 158745463
FONTE_ELEITORADO = "https://www.tse.jus.br/comunicacao/noticias/2026/Julho/mais-de-158-milhoes-de-eleitores-estao-aptos-votar-nas-eleicoes-2026"

def participacao(abstencao_pct):
    a = Decimal(str(abstencao_pct))
    if not a.is_finite() or not 0 <= a <= 100:
        raise ValueError("A abstenção deve estar entre 0% e 100%.")
    ausentes = int((Decimal(ELEITORADO)*a/100).quantize(Decimal(1), rounding=ROUND_HALF_UP))
    return ausentes, ELEITORADO-ausentes

def distribuir(total, pesos):
    """Maiores restos: quantidades inteiras cuja soma preserva o comparecimento."""
    exatos = [Decimal(total)*v/100 for v in pesos]
    inteiros = [int(v) for v in exatos]
    faltam = total-sum(inteiros)
    ordem = sorted(range(len(pesos)),key=lambda i: (-(exatos[i]-inteiros[i]),i))
    for i in ordem[:faltam]:
        inteiros[i] += 1
    return inteiros

def calcular(votos, brancos=0, nulos=0, modo='Votos', abstencao_pct=0):
    dados = {str(k): Decimal(str(v)) for k, v in votos.items()}
    branco, nulo = Decimal(str(brancos)), Decimal(str(nulos))
    valores = [*dados.values(), branco, nulo]
    if not dados or any(not v.is_finite() or v < 0 for v in valores):
        raise ValueError('Informe valores finitos e não negativos.')
    if modo not in ('Votos', 'Percentuais'):
        raise ValueError('Modo inválido.')
    if modo == 'Votos' and any(v != v.to_integral_value() for v in valores):
        raise ValueError('Quantidades de votos devem ser inteiras.')
    if modo == 'Percentuais':
        dados = {k: v.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP) for k, v in dados.items()}
        branco = branco.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        nulo = nulo.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    ausentes, comparecimento = participacao(abstencao_pct)
    if comparecimento == 0:
        raise ValueError('Com 100% de abstenção não há comparecimento nem votos válidos para definir resultado.')
    validos = sum(dados.values(), Decimal(0))
    total = validos + branco + nulo
    if modo == 'Percentuais' and total != Decimal(100):
        raise ValueError(f'A soma deve ser 100%. Soma atual: {total}%.')
    if modo == 'Votos' and total != comparecimento:
        diferenca = Decimal(comparecimento)-total
        raise ValueError(f'Os votos de candidatos + brancos + nulos devem somar o comparecimento estimado ({comparecimento:,}). Diferença: {diferenca:+}. Ajuste os votos ou use Percentuais.')
    if validos == 0:
        raise ValueError('Informe votos para pelo menos um candidato. Não há votos válidos para calcular.')
    ranking = sorted(dados.items(), key=lambda item: (-item[1], item[0]))
    vencedor = ranking[0][0] if ranking[0][1] * 2 > validos else None
    linhas = [{'Candidato': nome, 'Valor informado': float(v), '% do total': float(v / total * 100), '% dos válidos': float(v / validos * 100)} for nome, v in ranking]
    if modo == 'Percentuais':
        quantidades = distribuir(comparecimento, [*dados.values(), branco, nulo])
    else:
        quantidades = [int(v) for v in [*dados.values(), branco, nulo]]
    mapa_qtd = dict(zip(dados, quantidades[:-2]))
    for linha in linhas:
        linha['Votos estimados' if modo == 'Percentuais' else 'Votos'] = mapa_qtd[linha['Candidato']]
    # Empates que afetam as duas vagas exigem desempate; não escolher por ordem alfabética.
    corte = ranking[1][1] if len(ranking) > 1 else ranking[0][1]
    empatados = [nome for nome, v in ranking if v == corte]
    empate = not vencedor and len(empatados) > (2 - sum(v > corte for _, v in ranking))
    return dict(linhas=linhas, validos=float(validos), total=float(total), brancos=float(branco), nulos=float(nulo), vencedor=vencedor, empate=empate, empatados=empatados, segundo_turno=[nome for nome, _ in ranking[:2]], modo=modo, eleitorado=ELEITORADO, abstencao_pct=float(abstencao_pct), ausentes=ausentes, comparecimento=comparecimento, validos_qtd=sum(quantidades[:-2]), brancos_qtd=quantidades[-2], nulos_qtd=quantidades[-1])
