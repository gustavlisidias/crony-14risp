from avaliacoes.models import Nivel
from funcionarios.models import Perfil
from ponto.utils import pontos_por_dia


def dados_avaliacao(avaliacao, perguntas, respostas):
	total_respostas = len(respostas)
	total_participantes = len(avaliacao.avaliadores.all())
	total_participantes_ativos = len(set([i.funcionario for i in respostas]))
	total_perguntas = len(perguntas)
	
	_, score_periodo = pontos_por_dia(avaliacao.inicio, avaliacao.final, avaliacao.avaliado)
	time = Perfil.objects.get(funcionario=avaliacao.avaliado).time.titulo.lower()

	cortes = {'diamante': 4.5, 'ouro': 4.0, 'prata': 3.5, 'bronze': 2.5}
	notas_por_nivel = {0: {}, 1: {}, 2: {}}
	comentarios = {}

	# Criando objeto de nota por funcionario por nivel de avaliador
	for i in respostas:
		observacoes = [{'observacao': j.observacao, 'pergunta': j.referencia.pergunta.titulo} for j in respostas if i.funcionario == j.funcionario and j.observacao]
		if observacoes:
			comentarios[i.funcionario] = observacoes
		
		if i.funcionario == avaliacao.avaliado:
			nivel = 0
		elif i.funcionario.usuario.get_access != 'common':
			nivel = 2
		else:
			nivel = 1
		
		if i.funcionario not in notas_por_nivel[nivel]:
			notas_por_nivel[nivel][i.funcionario] = {}
		
		if i.referencia.pergunta not in notas_por_nivel[nivel][i.funcionario]:
			notas_por_nivel[nivel][i.funcionario][i.referencia.pergunta] = i.nota * i.referencia.pergunta.peso
	
	# Calculo da média de notas por nível
	for nivel, funcionarios in notas_por_nivel.items():
		media = 0
		qtd_func = len(notas_por_nivel[nivel]) if notas_por_nivel[nivel] else 1
		for _, perguntas in funcionarios.items():
			for _, nota in perguntas.items():
				media += nota
		
		notas_por_nivel[nivel]['media'] = media / qtd_func

	# Cálculo da nota final
	nota_final = sum([notas_por_nivel[i]['media'] * Nivel.objects.get(avaliacao=avaliacao, tipo=i).peso for i in notas_por_nivel])
	if score_periodo:
		nota_final = (nota_final + score_periodo[avaliacao.avaliado][0]) / 2
	
	# Definindo se usuário está dentro da nota de corte (aprovado)
	corte = cortes.get(time, 0)
	aprovado = nota_final >= corte

	tabela = {}
	tabela_footer = {0: 0, 1: 0, 2: 0}
	for nivel, funcionarios in notas_por_nivel.items():
		for funcionario, perguntas in funcionarios.items():
			if funcionario != 'media':

				for pergunta, nota in perguntas.items():
					if pergunta.titulo not in tabela:
						tabela[pergunta.titulo] = {0: 0, 1: 0, 2: 0}

					qtd_respostas = (len(notas_por_nivel[nivel]) - 1)
					tabela[pergunta.titulo][nivel] += nota / qtd_respostas
					tabela_footer[nivel] += nota / qtd_respostas

	return {
		'total_respostas': total_respostas,
		'total_participantes': total_participantes,
		'total_participantes_ativos': total_participantes_ativos,
		'total_perguntas': total_perguntas,
		'score': score_periodo[avaliacao.avaliado][0] if score_periodo else 0,
		'notas': notas_por_nivel,
		'comentarios': comentarios,
		'nota_final': nota_final,
		'aprovado': aprovado,
		'tabela': tabela,
		'tabela_footer': tabela_footer
	}
	