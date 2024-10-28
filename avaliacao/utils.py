from avaliacao.models import PesoAvaliador
from funcionarios.models import Perfil
from ponto.utils import pontos_por_dia


def dados_avaliacao(avaliacao, respostas):
	total_respostas = len(respostas)
	total_participantes = len(avaliacao.avaliadores.all())
	total_participantes_ativos = len(set([i.funcionario for i in respostas]))
	total_perguntas = len(set([i.pergunta.pergunta for i in respostas]))
	
	_, score_periodo = pontos_por_dia(avaliacao.inicio, avaliacao.final, avaliacao.avaliado)

	notas = {}
	comentarios = {}
	for i in respostas:
		observacoes = {j.observacao for j in respostas if i.funcionario == j.funcionario and j.observacao}
		if observacoes:
			comentarios[i.funcionario] = observacoes
		
		if i.funcionario == avaliacao.avaliado:
			nivel = 0
		elif i.funcionario.usuario.get_access != 'common':
			nivel = 2
		else:
			nivel = 1
		
		if nivel not in notas:
			notas[nivel] = {}
		
		if i.funcionario not in notas[nivel]:
			notas[nivel][i.funcionario] = {}
		
		if i.pergunta.criterio not in notas[nivel][i.funcionario]:
			notas[nivel][i.funcionario][i.pergunta.criterio] = i.nota * i.pergunta.peso

	for nivel, funcionarios in notas.items():
		x = 0
		for _, criterios in funcionarios.items():
			for _, nota in criterios.items():
				x += nota / len(notas[nivel])

		notas[nivel]['media'] = x

	score = score_periodo[avaliacao.avaliado][0] if score_periodo else 0
	nota_final = (sum([notas[i]['media'] * PesoAvaliador.objects.get(avaliacao=avaliacao, nivel=i).peso for i in notas]) + score) / 2

	time = Perfil.objects.get(funcionario=avaliacao.avaliado).time.titulo.lower()

	if time == 'diamante':
		corte = 4.5
	elif time == 'ouro':
		corte = 4
	elif time == 'prata':
		corte = 3.5
	elif time == 'bronze':
		corte = 2.5
	else:
		corte = 0
	
	aprovado = nota_final >= corte

	tabela = {}
	tabela_footer = {}
	for nivel, funcionarios in notas.items():
		for funcionario, criterios in funcionarios.items():
			if funcionario != 'media':
				for criterio, nota in criterios.items():
					if criterio.nome not in tabela:
						tabela[criterio.nome] = {0: 0, 1: 0, 2: 0}

					tabela[criterio.nome][nivel] += nota / (len(notas[nivel]) - 1)

					if nivel not in tabela_footer:
						tabela_footer[nivel] = 0
					tabela_footer[nivel] += nota / (len(notas[nivel]) - 1)

	return {
		'total_respostas': total_respostas,
		'total_participantes': total_participantes,
		'total_participantes_ativos': total_participantes_ativos,
		'total_perguntas': total_perguntas,
		'score': score_periodo[avaliacao.avaliado][0] if score_periodo else 0,
		'notas': notas,
		'comentarios': comentarios,
		'nota_final': nota_final,
		'aprovado': aprovado,
		'tabela': tabela,
		'tabela_footer': tabela_footer
	}
	