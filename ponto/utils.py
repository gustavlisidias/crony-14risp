import time

from django.utils import timezone

from collections import defaultdict
from datetime import date, datetime, timedelta, time as create_time

from funcionarios.models import Score, JornadaFuncionario
from ponto.models import SolicitacaoAbono, SolicitacaoPonto, Ponto, Saldos, Feriados
from web.utils import parse_date, parse_employee


def filtrar_abonos(inicio, final, funcionario):
	data_inico = timezone.localtime(inicio)
	data_final = timezone.localtime(final)

	montar_pontos = {}
	jornadas_filtradas = {}
	nro_dias = (data_final.date() - data_inico.date()).days

	if data_inico.date() == data_final.date():
		wd_incio = 1 if data_inico.date().weekday() + 2 == 8 else data_inico.date().weekday() + 2
		jornadas = JornadaFuncionario.objects.filter(funcionario=funcionario, final_vigencia=None, dia=wd_incio).order_by('funcionario__id', 'agrupador', 'dia', 'ordem')
	else:
		jornadas = JornadaFuncionario.objects.filter(funcionario=funcionario, final_vigencia=None).order_by('funcionario__id', 'agrupador', 'dia', 'ordem')

	for i in range(nro_dias + 1):
		dia_atual = data_inico.date() + timedelta(days=i)
		wd_atual = 1 if dia_atual.weekday() + 2 == 8 else dia_atual.weekday() + 2

		if dia_atual not in montar_pontos:
			montar_pontos[dia_atual] = []

		for jornada in jornadas.filter(dia=wd_atual):
			montar_pontos[dia_atual].append(jornada.hora)

	for dia, horas in montar_pontos.items():
		if dia < data_inico.date() or dia > data_final.date():
			continue

		horas_filtradas = []
		
		for hora in horas:
			if dia == data_inico.date() and hora < data_inico.time():
				continue
			if dia == data_final.date() and hora > data_final.time():
				continue
			horas_filtradas.append(hora)
		
		if dia == data_inico.date() and data_inico.time() not in horas_filtradas:
			horas_filtradas.insert(0, data_inico.time())
		if dia == data_final.date() and data_final.time() not in horas_filtradas:
			horas_filtradas.append(data_final.time())

		jornadas_filtradas[dia] = horas_filtradas

	return jornadas_filtradas
	

def pontos_por_dia(data_inicial=None, data_final=None, funcionarios=None, fechamento=False):
	data_inicial = parse_date(data_inicial)
	data_final = parse_date(data_final)
	funcionarios = parse_employee(funcionarios)

	if not (data_inicial and data_final and funcionarios):
		return None, None

	############################################INICIO BLOCO 00###########################################
	INICIO_FUNCAO_0 = time.time()

	pontos = Ponto.objects.filter(data__range=[data_inicial, data_final], funcionario__in=funcionarios).values(
		'funcionario__id', 'data', 'encerrado', 'motivo', 'hora'
	).order_by('funcionario', 'data', 'hora')

	jornadas = JornadaFuncionario.objects.filter(funcionario__in=funcionarios).values(
		'funcionario__id', 'agrupador', 'inicio_vigencia', 'final_vigencia', 'dia', 'hora'
	).order_by('funcionario', 'agrupador', 'dia', 'ordem')

	if not (pontos and jornadas):
		return None, None

	# Criado dicionário de pontos por data por funcionário
	# Exemplo: funcionário: data: motivo, encerrado, pontos: []
	# {306: {01/10/2024: {'motivo': 'teste', 'ecerrado': True, 'pontos': [8:01, 12:05, 13:20, 18:02]}}}
	pontos_dict = defaultdict(lambda: defaultdict(lambda: {'pontos': [], 'encerrado': '', 'motivo': ''}))
	for i in pontos:
		pontos_dict[i['funcionario__id']][i['data']]['pontos'].append(i['hora'])
		pontos_dict[i['funcionario__id']][i['data']]['encerrado'] = i['encerrado']
		pontos_dict[i['funcionario__id']][i['data']]['motivo'] = i['motivo']

	# Criando dicionário de jornadas por weekday por agrupador por funcionário
	# Exemplo: funcionário: agrupador: inicio, vencimento + dia: lista de horas
	# {306: {1: {'inicio': 01/10/2024, 'vencimento': 25/10/2024, 1: [8:00, 12:00, 13:12, 18:00]}}}
	jornadas_dict = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
	for i in jornadas:
		vencimento = i['final_vigencia'] or date.today() + timedelta(days=30)

		if i['agrupador'] not in jornadas_dict[i['funcionario__id']]:
			jornadas_dict[i['funcionario__id']][i['agrupador']] = {'inicio': i['inicio_vigencia'], 'vencimento': vencimento, 'dias': defaultdict(list)}

		jornadas_dict[i['funcionario__id']][i['agrupador']]['dias'][i['dia']].append(i['hora'])
	
	# Gerando dicionário de pontução por funcionário nos Scores em aberto
	scores = {score.funcionario.id: score.pontuacao for score in Score.objects.filter(fechado=False)}

	# Gerando dicionário de feriados cadastrados por data
	feriados = {i.data: i.funcionarios.all() for i in Feriados.objects.all()}

	# Gerando dicionário de saldo por funcionário
	saldos = defaultdict(lambda: defaultdict(lambda: timedelta(seconds=0)))
	for i in Saldos.objects.all().order_by('funcionario__id', 'data'):
		saldos[i.funcionario.id][i.data] += i.saldo

	# Gerando dicionário de solicitações de Ajuste de ponto e de Abono de ponto
	solicitacoes_ajuste = SolicitacaoPonto.objects.filter(funcionario__in=funcionarios).values('funcionario__id', 'data', 'status', 'motivo', 'data_cadastro__month').distinct()
	solicitacoes_abono = SolicitacaoAbono.objects.filter(funcionario__in=funcionarios).values('funcionario__id', 'inicio__date', 'status', 'motivo', 'data_cadastro__month', 'tipo').distinct()
	solicitacoes = [{'categoria': 'ajuste', 'data': i['data'], 'funcionario': i['funcionario__id'], 'motivo': i['motivo'], 'status': i['status'], 'mes': i['data_cadastro__month'], 'tipo': 'SA'} for i in solicitacoes_ajuste]
	solicitacoes.extend([{'categoria': 'abono', 'data': i['inicio__date'], 'funcionario': i['funcionario__id'], 'motivo': i['motivo'], 'status': i['status'], 'mes': i['data_cadastro__month'], 'tipo': i['tipo']} for i in solicitacoes_abono])
	
	FIM_FUNCAO_0 = time.time()
	############################################FINAL BLOCO 00############################################

	print(f'\nObjeto terá o registro de pontos de {len(funcionarios)} funcinário(s) dentro do período de {data_inicial.strftime("%d/%m/%Y")} até {data_final.strftime("%d/%m/%Y")} ({(data_final-data_inicial).days} dias)')
	print(f'Preparação dos dados: {FIM_FUNCAO_0 - INICIO_FUNCAO_0}')
	
	############################################INICIO BLOCO 01###########################################
	INICIO_FUNCAO_1 = time.time()

	dias_por_funcionario = {data_atual: [] for data_atual in (data_inicial + timedelta(days=n) for n in range((data_final - data_inicial).days + 1))}
	for data in dias_por_funcionario:
		for funcionario in funcionarios:

			motivos = {data: None}
			pendencias = {data: False}

			for i in solicitacoes:
				if i['funcionario'] == funcionario.id and i['data'] == data.date():
					if i['status'] is True:
						motivos[data] = i['motivo'].strip()
					else:
						pendencias[data] = True

			pontos_funcionario = []
			encerrado = False
			motivo = motivos.get(data)
			pendente = pendencias.get(data)

			dados_ponto = pontos_dict.get(funcionario.id, {}).get(data.date(), None)
			if dados_ponto:
				pontos_funcionario = dados_ponto['pontos']
				encerrado = dados_ponto['encerrado']
				
				if motivo is None:
					motivo = dados_ponto['motivo'] if dados_ponto['motivo'] else ''

					# Verifica se o motivo está vazio e o dia é sábado ou domingo
					if not motivo and data.date().weekday() in [5, 6]:
						motivo = ''
			
			dias_por_funcionario[data].append({
				'funcionario': funcionario,
				'pontos': pontos_funcionario,
				'encerrado': encerrado,
				'pendente': pendente,
				'motivo': motivo,
				'total': timedelta(seconds=0),
				'saldo': saldos.get(funcionario.id, {}).get(data.date(), timedelta(seconds=0)),
				'score': scores.get(funcionario.id, 0),
				'he50': timedelta(0),
				'he100': timedelta(0),
				'noturno': timedelta(0)
			})
	
	FIM_FUNCAO_1 = time.time()
	############################################FINAL BLOCO 01############################################

	print(f'Inicialização do objeto principal: {FIM_FUNCAO_1 - INICIO_FUNCAO_1}')

	############################################INICIO BLOCO 02###########################################
	INICIO_FUNCAO_2 = time.time()
	
	score_por_funcionario = {}
	for dia, dados in dias_por_funcionario.items():
		for dado in dados:
			
			if dado['funcionario'] not in score_por_funcionario:
				score_por_funcionario[dado['funcionario']] = [0, 0, []]
			
			pontos = dado['pontos']
			qtd_pontos = len(pontos)

			weekday = 1 if dia.weekday() + 2 == 8 else dia.weekday() + 2
			tolerancia = timedelta(minutes=5) if dado['funcionario'].get_contrato.tipo == 'est' else timedelta(minutes=10)

			jornada = []
			for _, info in jornadas_dict.get(dado['funcionario'].id, {}).items():
				if dia.date() >= info['inicio'] and dia.date() <= info['vencimento']:
					jornada = info['dias'].get(weekday, [])
					break

			total_esperado = total_saldo(jornada)
			qtd_jornada = len(jornada)
			
			# Se é ponto antes da data de contratação, é ignorado
			# Se não possui pontos naquele dia, e não é final de semana, é considerado falta
			# Caso contrário é calculado o total diário
			if dia.date() < dado['funcionario'].data_contratacao:
				dado['saldo'] = timedelta(0)
				dado['score'] = 5

			elif not dado['pontos'] and weekday in [1, 7]:
				dado['saldo'] = timedelta(0)
				dado['score'] = 5

				if not dado['motivo']:
					dado['motivo'] = 'Descanso remunerado'

			elif qtd_pontos <= 1:
				dado['saldo'] -= total_esperado
				dado['score'] -= 1

				if not dado['motivo']:
					dado['motivo'] = 'Falta não compensada'
			
			else:
				dado['total'] += total_saldo(pontos)
				dado['saldo'] += dado['total'] - total_esperado

				# Se trabalhei menos que o esperado, mesmo com a tolerancia, o score é penalizado
				if (dado['total'] + tolerancia) < total_esperado:
					dado['score'] -= 0.25
				
				# Saldo deve respeitar tolerancia
				if dado['saldo'] < timedelta(0) and dado['saldo'] >= tolerancia *-1:
					dado['saldo'] = timedelta(0)

				# Calculo dos Adicionais
				feriado = feriados.get(dia.date())
				dado['he50'], dado['he100'], dado['noturno'] = calculo_adicionais(dado['saldo'], feriado, dado['pontos'], dado['funcionario'], weekday)

				# Calculo do score diário
				# Regra: se meu ponto está entre a (jornada - tolerancia) e (jornada + tolerancia)
				# Exemplo: ponto deve ser marcado as 08:00
				# Se meu registro estiver fora de 07:50 e 08:00, meu score leva penalidade 
				if qtd_jornada == qtd_pontos:
					for j, p in zip(jornada, pontos):
						periodo = [datetime.combine(datetime.today(), j) - tolerancia, datetime.combine(datetime.today(), j) + tolerancia]
						registro = datetime.combine(datetime.today(), p)
						if not (registro >= periodo[0] and registro <= periodo [1]):
							dado['score'] -= 0.25
				else:
					dado['score'] -= 0.25
			
			# Normalizando o score diário final
			dado['score'] = 5 if dado['score'] > 5 else dado['score']
			score_por_funcionario[dado['funcionario']][2].append(dado['score'])
			###########################################################
	
	FIM_FUNCAO_2 = time.time()
	############################################FINAL BLOCO 02############################################

	print(f'Cálculo dos totais, saldos e banco de horas: {FIM_FUNCAO_2 - INICIO_FUNCAO_2}\n')

	##################################################################################################

	# Ajustando médias e cálculos utilizados nos gráficos
	# Notas calculadas no período, média e média percentual considerando a base como 5
	for funcionario, notas in score_por_funcionario.items():
		if notas[2]:
			media = sum(notas[2]) / len(notas[2])
			notas[0] = media
			notas[1] = media * 100 / 5

	##################################################################################################
	
	# Condição para quando fechamento		
	if fechamento:
		mes = datetime.today().month - 1

		for funcionario in funcionarios:
			ajustes = [i for i in solicitacoes if i['categoria'] == 'ajuste' and i['funcionario'] == funcionario.id and i['mes'] == mes and i['status'] is True]
			abonos = [i for i in solicitacoes if i['categoria'] == 'abono' and i['funcionario'] == funcionario.id and i['mes'] == mes and i['status'] is True]

			total_ajustes = len(ajustes) * 0.01
			total_declaracoes = len([i for i in abonos if i['tipo'] == 'DC']) * 0.04
			total_faltas = len([i for i in abonos if i['tipo'] == 'FT']) * 1.25
			total_atestados = len([i for i in abonos if i['tipo'] not in ['DC', 'FT']]) * 0.08
			total_desconto = total_ajustes + total_atestados + total_declaracoes + total_faltas

			cargo = funcionario.cargo.slug

			if cargo == 'analista':
				total_desconto * 2.5
			elif cargo == 'estagiario':
				total_desconto * 2
			else:
				total_desconto * 2.25
			
			nota = score_por_funcionario.get(funcionario, [5, 100, []])
			nota_final = nota[0] - total_desconto
			nota_percentual = (nota_final * 100) / 5

			if nota_final > 5:
				nota_final = 5
				nota_percentual = 100

			if nota_final < 0:
				nota_final = 0
				nota_percentual = 0
			
			score_por_funcionario[funcionario] = [nota_final, nota_percentual, nota[2]]
	
	return dias_por_funcionario, score_por_funcionario


def total_saldo(queryset):
	try:
		if isinstance(queryset, list):
			horarios = queryset
		else:
			horarios = queryset.values_list('hora', flat=True)

	except Exception:
		return None
	
	total = timedelta(0)

	for i in range(0, len(horarios), 2):
		try:
			total += timedelta(
				hours=(horarios[i+1].hour - horarios[i].hour),
				minutes=(horarios[i+1].minute - horarios[i].minute),
				seconds=(horarios[i+1].second - horarios[i].second)
			)
		except IndexError:
			continue

	return total


def total_saldo_noturno(queryset):
	try:
		if isinstance(queryset, list):
			horarios = queryset
		else:
			horarios = queryset.values_list('hora', flat=True)

	except Exception:
		return None
	
	inicio_noturno = create_time(22, 0)
	fim_noturno = create_time(5, 0)
	total_noturno = timedelta()

	for i in range(0, len(horarios) - 1, 2):
		entrada = horarios[i]
		saida = horarios[i + 1]
		
		entrada_dt = datetime.combine(datetime.today(), entrada)
		saida_dt = datetime.combine(datetime.today(), saida)
		
		if saida < entrada:
			saida_dt += timedelta(days=1)
		
		if entrada < inicio_noturno and saida > inicio_noturno:
			noturno_inicio = datetime.combine(datetime.today(), inicio_noturno)
			total_noturno += min(saida_dt, noturno_inicio + timedelta(hours=7)) - noturno_inicio
		
		elif entrada >= inicio_noturno or saida <= fim_noturno:
			total_noturno += saida_dt - entrada_dt

	return total_noturno


def calculo_adicionais(saldo, feriado, pontos, funcionario, weekday):
	'''
	Adicional de 100%: feriados, sábado, domingo, após 2h de saldo
	Adicional de 50%: até 2h de saldo
	Adicional de 20%: nortuno (22h até as 5h)
	'''
	ultimo_ponto = pontos[-1]

	saldo_100 = timedelta(0)
	saldo_50 = timedelta(0)
	saldo_20 = timedelta(0)

	if ultimo_ponto >= create_time(22, 0):
		saldo_20 += total_saldo_noturno(pontos)

	if saldo > timedelta(0):
		if (feriado and funcionario in feriado) or (weekday in [1, 7]):
			saldo_100 += saldo

		elif saldo > timedelta(minutes=120):
			saldo_100 += saldo - timedelta(minutes=120)
			saldo_50 += timedelta(minutes=120)

		else:
			saldo_50 += saldo

	return saldo_50, saldo_100, saldo_20
