# ruff: noqa: F401
from avaliacoes.models import Nivel
from funcionarios.models import Perfil
from ponto.models import Ponto
from ponto.utils import pontos_por_dia

from datetime import datetime, time
from collections import defaultdict


def dados_avaliacao(avaliacao, perguntas, respostas):
	if not respostas:
		return None, None
	
	total_respostas = len(respostas)
	total_participantes = len(avaliacao.avaliadores.all())
	total_participantes_ativos = len(set([i.funcionario for i in respostas]))
	total_perguntas = len(perguntas)

	participantes_sem_resposta = avaliacao.avaliadores.exclude(id__in=[i.funcionario.id for i in respostas])

	# Determinação da data de início para cálculo de score
	primeiro_ponto = Ponto.objects.filter(funcionario=avaliacao.avaliado).values('data').order_by('data').first()
	inicio_score = datetime.combine(max(avaliacao.inicio, avaliacao.avaliado.data_contratacao, primeiro_ponto['data']), time())
	_, score_periodo = pontos_por_dia(inicio_score, datetime.combine(avaliacao.final, time()), avaliacao.avaliado)
	
	# Estruturas para armazenar notas e estatísticas
	tabela = defaultdict(lambda: {'par': 0, 'auto': 0, 'gestor': 0})
	notas_por_nivel = defaultdict(lambda: {'par': 0, 'auto': 0, 'gestor': 0})
	qtd_por_nivel = {'par': set(), 'auto': set(), 'gestor': set()}
	comentarios = defaultdict(list)
	pesos = {i.get_tipo_display().lower(): i.peso for i in Nivel.objects.filter(avaliacao=avaliacao)}

	for resposta in respostas:
		funcionario = resposta.funcionario
		titulo_pergunta = resposta.referencia.pergunta.titulo
		nota, peso = resposta.nota, resposta.referencia.pergunta.peso

		# Coleta de observações por funcionário
		if resposta.observacao:
			comentarios[funcionario].append({
				'observacao': resposta.observacao,
				'pergunta': titulo_pergunta
			})

		# Determinar o nível do avaliador
		if funcionario == avaliacao.avaliado:
			nivel = 'auto'
		elif funcionario == avaliacao.avaliado.gerente or funcionario.usuario.get_access != 'common':
			nivel = 'gestor'
		else:
			nivel = 'par'

		# Atualizar contadores e somar notas
		tabela[titulo_pergunta][nivel] += nota
		notas_por_nivel[titulo_pergunta][nivel] += nota * peso
		qtd_por_nivel[nivel].add(funcionario.id)
	
	# Cálculo da média das notas por critério e nível
	for criterio in tabela:
		for nivel in pesos.keys():
			qtd = len(qtd_por_nivel[nivel])
			tabela[criterio][nivel] /= qtd if qtd else 1
			notas_por_nivel[criterio][nivel] /= qtd if qtd else 1

	# Média por critério
	media_por_criterio = {criterio: sum(niveis.values()) / len(niveis) for criterio, niveis in tabela.items()}

	# Média por nível
	niveis_tabela = {'par': 0, 'auto': 0, 'gestor': 0}
	for criterio in tabela.values():
		for nivel, valor in criterio.items():
			niveis_tabela[nivel] += valor

	media_por_nivel = {nivel: total / len(tabela) for nivel, total in niveis_tabela.items()}
	
	# Aplicação dos pesos às notas finais
	nota_final = sum(notas_por_nivel[criterio][nivel] * pesos[nivel] for criterio in notas_por_nivel for nivel in pesos)

	# Definindo se usuário está dentro da nota de corte (aprovado)
	cortes = {'ouro': 4.5, 'prata': 4, 'bronze': 3.5}
	corte = cortes.get(avaliacao.avaliado.get_perfil.time.titulo.lower(), 2.5)
	aprovado = nota_final >= corte
	
	dados = {
		'total_respostas': total_respostas,
		'total_participantes': total_participantes,
		'total_participantes_ativos': total_participantes_ativos,
		'total_perguntas': total_perguntas,
		'score': score_periodo.get(avaliacao.avaliado.id, {}).get('media', 0),
		'notas': dict(notas_por_nivel),
		'comentarios': dict(comentarios),
		'nota_final': nota_final,
		'aprovado': aprovado,
		'corte': corte,
		'grafico': {tipo: sum(valor[tipo] for valor in dict(tabela).values()) / len(dict(tabela)) for tipo in pesos.keys()},
		'media_por_criterio': media_por_criterio,
		'media_por_nivel': media_por_nivel,
		'participantes_sem_resposta': participantes_sem_resposta
	}

	return dados, dict(tabela)
