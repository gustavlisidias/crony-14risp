from datetime import timedelta, datetime, date
from collections import defaultdict

from django.db.models import Sum
from django.db.models.query import QuerySet
from django.utils import timezone

from funcionarios.models import Funcionario, JornadaFuncionario
from ponto.models import Ponto, Saldos, Feriados, SolicitacaoPonto, SolicitacaoAbono, Fechamento


def calcular_banco(dados, data_inicial, funcionarios):
	def banco_anterior(pontos, jornadas_queryset, dados_anteriores, primeira_data, tolerancia):
		pontos_queryset = pontos.filter(data__lt=primeira_data).order_by('data', 'hora').values('funcionario__id', 'data', 'hora')
		
		for ponto in pontos_queryset:
			data = ponto['data']
			funcionario_id = ponto['funcionario__id']
			dados_anteriores[data][funcionario_id]['pontos'].append(ponto['hora'])

		jornadas_dict = jornadas_queryset.values('funcionario__id', 'agrupador', 'inicio_vigencia', 'final_vigencia', 'dia', 'hora').order_by('funcionario', 'agrupador', 'dia', 'ordem')

		jornadas = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))

		for i in jornadas_dict:
			index = i['funcionario__id']
			agrupador = i['agrupador']
			inicio = i['inicio_vigencia']
			vencimento = i['final_vigencia'] or date.today() + timedelta(days=30)
			wday = i['dia']
			whour = i['hora']

			if agrupador not in jornadas[index]:
				jornadas[index][agrupador] = {'inicio': inicio, 'vencimento': vencimento, 'dias': defaultdict(list)}

			jornadas[index][agrupador]['dias'][wday].append(whour)

		banco = timedelta()

		for data, funcionarios_ids in dados_anteriores.items():
			weekday = 1 if data.weekday() + 2 == 8 else data.weekday() + 2

			for funcionario_id, dado in funcionarios_ids.items():
				jornada = next((info['dias'].get(weekday, []) for _, info in jornadas.get(funcionario_id).items() if info['inicio'] <= data <= info['vencimento']), [])
				
				total_jornada = timedelta()
				total_trabalhado = timedelta()
				saldo = Saldos.objects.filter(funcionario__id=funcionario_id, data=data).aggregate(total=Sum('saldo'))['total'] or timedelta()

				hora_extra_50 = timedelta()
				hora_extra_100 = timedelta()
				hora_extra_desconto = timedelta()
				
				if jornada and len(pontos) >= 2:
					for i in range(0, len(jornada) - 1, 2):
						entrada = datetime.combine(datetime.today(), jornada[i])
						saida = datetime.combine(datetime.today(), jornada[i + 1])
						duracao = saida - entrada
						total_jornada += duracao

					for i in range(0, len(dado['pontos']) - 1, 2):
						entrada = datetime.combine(datetime.today(), dado['pontos'][i])
						saida = datetime.combine(datetime.today(), dado['pontos'][i + 1])
						duracao = saida - entrada
						total_trabalhado += duracao
					
					saldo += total_trabalhado - total_jornada
					
					if (saldo < timedelta() and saldo >= tolerancia * -1):
						saldo = timedelta()

					if saldo > timedelta():
						feriados = Feriados.objects.filter(data=data)
						is_feriado = feriados.first().get_feriado_funcionario(funcionario) if feriados.exists() else False

						if weekday in [1, 7] or is_feriado:
							hora_extra_100 += saldo
						else:
							hora_extra_50 += saldo

					elif saldo < timedelta():
						hora_extra_desconto -= saldo

					banco += (hora_extra_50 * 1.5) + (hora_extra_100 * 2) - hora_extra_desconto
		
		return banco
	
	banco = timedelta()
	
	if len(funcionarios) == 1:
		funcionario = funcionarios.first()
		pontos = Ponto.objects.filter(funcionario=funcionario).order_by('data', 'hora')
		jornadas = JornadaFuncionario.objects.filter(funcionario=funcionario)

		if pontos:
			primeiro_registro = pontos.first().data
			tolerancia = timedelta(minutes=5) if funcionario.get_contrato.tipo == 'est' else timedelta(minutes=10)
			datas = [primeiro_registro + timedelta(days=i) for i in range((data_inicial - primeiro_registro).days)]
			dados_anteriores = {d: {funcionario.id: {'pontos': list()}} for d in datas}
			
			banco = banco_anterior(pontos, jornadas, dados_anteriores, data_inicial, tolerancia)
	
	for data, funcionarios in dados.items():
		for funcionario, dado in funcionarios.items():
			banco += dado['hora_extra'] # Validar se será o campo saldo ou hora_extra
			dados[data][funcionario].update({'banco': banco})

	return dados


def calcular_totais_e_saldos(funcionario, data, pontos, jornada, weekday, motivo, score):
	def calcular_horas_extras(he_funcionario, he_data, he_weekday, he_saldo):
		"""
		Existem diferentes tipos de horas extras, de acordo com a Consolidação das Leis do Trabalho (CLT)
		Hora extra diurna: É a mais comum e simples, e corresponde a um acréscimo de 50% sobre o valor da hora normal. É aplicada a horas trabalhadas de segunda a sábado, entre as 5h e as 22h.
		Hora extra noturna: Corresponde a um acréscimo de 80% sobre o valor da hora normal. É aplicada a horas trabalhadas entre as 22h de um dia e as 5h do dia seguinte.
		Hora extra em domingos e feriados: Corresponde a um acréscimo de 100% sobre o valor da hora normal. É aplicada a horas trabalhadas em domingos, feriados e pontos facultativos.

		Seguindo regras enviadas por Anderson (Chat Crony)

		HORAS EXTRAS
		1 - 50% (cinquanta por cento) saldos positivos, incluindo noturno;
		2 - 100% (cem por cento) as prestadas aos sábados, domingos e feriados.
		"""

		hora_extra_50 = timedelta()
		hora_extra_100 = timedelta()
		hora_extra_desconto = timedelta()

		if he_funcionario.get_contrato.tipo == 'est':
			return he_saldo

		elif he_saldo > timedelta():
			feriados = Feriados.objects.filter(data=he_data)
			is_feriado = feriados.first().get_feriado_funcionario(he_funcionario) if feriados.exists() else False

			if he_weekday in [1, 7] or is_feriado:
				hora_extra_100 += he_saldo
			else:
				hora_extra_50 += he_saldo

		elif he_saldo < timedelta():
			hora_extra_desconto -= he_saldo

		hora_extra_total = (hora_extra_50 * 1.5) + (hora_extra_100 * 2) - hora_extra_desconto
		
		return hora_extra_total
	
	total_jornada = timedelta()
	total_trabalhado = timedelta()

	score_calculado = True if score != 0 else False

	funcionario = Funcionario.objects.get(pk=funcionario)
	tolerancia = timedelta(minutes=5) if funcionario.get_contrato.tipo == 'est' else timedelta(minutes=10)
	saldo = Saldos.objects.filter(funcionario=funcionario, data=data).aggregate(total=Sum('saldo'))['total'] or timedelta()
	
	feriados = Feriados.objects.filter(data=data)
	is_feriado = feriados.first().get_feriado_funcionario(funcionario) if feriados.exists() else False
	
	qtd_pontos = len(pontos)
	qtd_jornada = len(jornada)

	for i in range(0, qtd_jornada - 1, 2):
		entrada = datetime.combine(datetime.today(), jornada[i])
		saida = datetime.combine(datetime.today(), jornada[i + 1])
		duracao = saida - entrada
		total_jornada += duracao

	if qtd_pontos == 0 and weekday in [1, 7]: # Sábado e Domingo
		motivo = 'Descanso remunerado'

	elif qtd_pontos == 1 and motivo: # Feriado e/ou Ferias -> Saldo Calculado
		saldo -= total_jornada

	elif qtd_pontos <= 1 and not motivo:
		motivo = 'Falta não compensada'
		saldo -= total_jornada

		if not score_calculado:
			score = 1

	else:
		for i in range(0, qtd_pontos - 1, 2):
			entrada = datetime.combine(datetime.today(), pontos[i])
			saida = datetime.combine(datetime.today(), pontos[i + 1])
			duracao = saida - entrada
			total_trabalhado += duracao

		saldo += total_trabalhado - total_jornada

		if not score_calculado:
			score = 5

		if (total_trabalhado + tolerancia) < total_jornada and not score_calculado:
			score = 2.5

		if saldo < timedelta() and saldo >= tolerancia * -1:
			saldo = timedelta()

			if not score_calculado:
				score = 4.5
	
	hora_extra = calcular_horas_extras(funcionario, data, weekday, saldo)

	faltando_registro = False
	if qtd_pontos < qtd_jornada and weekday not in [1, 7] and not is_feriado:
		faltando_registro = True

	return {
		'total': total_trabalhado,
		'jornada': total_jornada,
		'saldo': saldo,
		'score': score,
		'motivo': motivo.strip(),
		'hora_extra': hora_extra,
		'faltando_registro': faltando_registro
	}


def pontos_por_dia(data_inicio, data_fim, funcionarios, fechamento=False):
	if not isinstance(funcionarios, QuerySet):
		funcionarios = Funcionario.objects.filter(pk=funcionarios.pk)

	def inicializar_dados(datas, funcionarios):
		"""
		Garante que todos os dias no intervalo e todos os funcionários tenham dados inicializados.
		"""
		dados = dict()

		for data in datas:
			if data not in dados:
				dados[data] = dict()

			for funcionario in funcionarios:
				if funcionario['id'] not in dados[data]:
					dados[data][funcionario['id']] = {'nome': funcionario['nome'], 'pontos': list(), 'motivo': '', 'encerrado': False, 'estagiario': funcionario['estagio']}
		
		return dados

	def carregar_pontos(datas, funcionarios):
		"""
		Adiciona pontos registrados para cada funcionário no intervalo.
		"""
		# Consultas iniciais
		funcionarios_ids = [f['id'] for f in funcionarios]

		pontos_queryset = Ponto.objects.filter(funcionario__id__in=funcionarios_ids, data__range=(data_inicio, data_fim)).order_by('data', 'hora').values(
			'funcionario__id', 'data', 'hora', 'encerrado', 'alterado', 'motivo'
		)

		ajustes_queryet = SolicitacaoPonto.objects.filter(funcionario__id__in=funcionarios_ids).values('funcionario__id', 'data', 'status', 'motivo', 'data_cadastro__month', 'data_cadastro__year').distinct()
		abonos_queryset = SolicitacaoAbono.objects.filter(funcionario__id__in=funcionarios_ids).values('funcionario__id', 'inicio__date', 'status', 'motivo', 'data_cadastro__month', 'data_cadastro__year', 'tipo').distinct()

		# Pré-processar solicitações
		solicitacoes = defaultdict(list)
		for ajuste in ajustes_queryet:
			solicitacoes[(ajuste['funcionario__id'], ajuste['data'])].append({
				'categoria': 'ajuste',
				'motivo': ajuste['motivo'],
				'status': ajuste['status'],
				'mes': ajuste['data_cadastro__month'],
				'ano': ajuste['data_cadastro__year'],
				'tipo': 'SA'
			})

		for abono in abonos_queryset:
			solicitacoes[(abono['funcionario__id'], abono['inicio__date'])].append({
				'categoria': 'abono',
				'motivo': abono['motivo'],
				'status': abono['status'],
				'mes': abono['data_cadastro__month'],
				'ano': abono['data_cadastro__year'],
				'tipo': abono['tipo']
			})

		# Inicializar dados
		dados = inicializar_dados(datas, funcionarios)

		# Processar pontos e atualizar dados
		for ponto in pontos_queryset:
			data = ponto['data']
			funcionario_id = ponto['funcionario__id']

			# Atualizar pontos
			dados[data][funcionario_id]['pontos'].append(ponto['hora'])

			# Determinar pendências e motivo
			pendente = any(not s['status'] for s in solicitacoes.get((funcionario_id, data), []))
			motivo = ponto['motivo'] if ponto['motivo'] else ''
			dados[data][funcionario_id].update({
				'encerrado': ponto['encerrado'],
				'pendente': pendente,
				'motivo': motivo
			})

		return dados, solicitacoes

	def calcular_scores_e_dados(funcionarios, dados):
		"""
		Processa os dados calculando totais, saldos e scores para cada funcionário.
		"""
		funcionarios_ids = [f['id'] for f in funcionarios]

		# Levantar jornadas dos funcionários
		jornadas_dict = JornadaFuncionario.objects.filter(funcionario__id__in=funcionarios_ids).values(
			'funcionario__id', 'agrupador', 'inicio_vigencia', 'final_vigencia', 'dia', 'hora'
		).order_by('funcionario', 'agrupador', 'dia', 'ordem')

		jornadas = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))

		for i in jornadas_dict:
			index = i['funcionario__id']
			agrupador = i['agrupador']
			inicio = i['inicio_vigencia']
			vencimento = i['final_vigencia'] or date.today() + timedelta(days=30)
			wday = i['dia']
			whora = i['hora']

			if agrupador not in jornadas[index]:
				jornadas[index][agrupador] = {'inicio': inicio, 'vencimento': vencimento, 'dias': defaultdict(list)}

			jornadas[index][agrupador]['dias'][wday].append(whora)

		# Calcular os scores e atualizar os dados
		score_por_funcionario = defaultdict(lambda: {'media': 0, 'perc': 0, 'notas': list()})

		for data, funcionarios_ids in dados.items():
			weekday = 1 if data.weekday() + 2 == 8 else data.weekday() + 2

			for funcionario_id, dado in funcionarios_ids.items():
				anomes = int(data.strftime('%Y%m'))
				fechamento = Fechamento.objects.filter(funcionario__id=funcionario_id, referencia=anomes).values_list('pontuacao', flat=True)
				score = fechamento[0] if fechamento else 0

				jornada = next((info['dias'].get(weekday, []) for _, info in jornadas.get(funcionario_id).items() if info['inicio'] <= data <= info['vencimento']), [])
				totais_saldos = calcular_totais_e_saldos(funcionario_id, data, dado['pontos'], jornada, weekday, dado['motivo'], score)

				dado.update(totais_saldos)
				score_por_funcionario[funcionario_id]['notas'].append(totais_saldos['score'])

		return score_por_funcionario

	def calcular_scores_fechamento(solicitacoes, score_por_funcionario):
		"""
		Calcula o score final utilizado para o fechamento mensal
		"""
		hoje = date.today()
		mes = hoje.month - 1 if hoje.month > 1 else 12
		ano = hoje.year if hoje.month > 1 else hoje.year - 1

		for funcionario_id, _ in score_por_funcionario.items():
			ajustes, abonos = list(), list()

			for (funcid, _), itens in solicitacoes.items():
				for item in itens:
					if funcid == funcionario_id and item['ano'] == ano and item['mes'] == mes and item['categoria'] == 'ajuste' and item['status']:
						ajustes.append(item)

					if funcid == funcionario_id and item['ano'] == ano and item['mes'] == mes and item['categoria'] == 'abono' and item['status']:
						abonos.append(item)

			total_ajustes = len(ajustes) * 0.01
			total_declaracoes = len([i for i in abonos if i['tipo'] == 'DC']) * 0.04
			total_faltas = len([i for i in abonos if i['tipo'] == 'FT']) * 1.25
			total_atestados = len([i for i in abonos if i['tipo'] not in ['DC', 'FT']]) * 0.08
			total_desconto = total_ajustes + total_atestados + total_declaracoes + total_faltas

			cargo = Funcionario.objects.get(pk=funcionario_id).cargo.slug

			if cargo == 'analista':
				total_desconto * 2.5
			elif cargo == 'estagiario':
				total_desconto * 2
			else:
				total_desconto * 2.25
			
			nota = score_por_funcionario.get(funcionario_id, {'media': 5, 'perc': 100, 'notas': list()})
			nota_final = nota['media'] - total_desconto
			nota_percentual = (nota_final * 100) / 5

			if nota_final > 5:
				nota_final = 5
				nota_percentual = 100

			if nota_final < 0:
				nota_final = 0
				nota_percentual = 0
			
			score_por_funcionario[funcionario_id] = {'media': nota_final, 'perc': nota_percentual, 'notas': nota['notas']}
		
		return score_por_funcionario

	# Gerar lista de datas no intervalo e de funcionários
	datas = [(data_inicio + timedelta(days=i)).date() for i in range((data_fim - data_inicio).days + 1)]
	lista_funcionarios = [{'id': f.id, 'nome': f.nome_completo, 'estagio': f.get_contrato.tipo == 'est'} for f in funcionarios]

	# Inicializar dados para todos os dias filtrados e carregar pontos registrados
	dados, solicitacoes = carregar_pontos(datas, lista_funcionarios)

	# Calcular totais, saldo, hora extra, banco e score para cada funcionário
	score_por_funcionario = calcular_scores_e_dados(lista_funcionarios, dados)
	saldo_por_funcionario = calcular_banco(dados, datas[0], funcionarios)

	# Calcular médias e percentuais finais
	for funcionario, scores in score_por_funcionario.items():
		notas = [s for s in scores['notas'] if s > 0]
		media = sum(notas) / len(notas) if notas else 0
		score_por_funcionario[funcionario].update({'media': media, 'perc': (media / 5) * 100})

	# Calcular fechamento
	if fechamento:
		score_por_funcionario = calcular_scores_fechamento(solicitacoes, score_por_funcionario)
	
	return saldo_por_funcionario, score_por_funcionario


def filtrar_abonos(inicio, final, funcionario):
	data_inico = timezone.localtime(inicio)
	data_final = timezone.localtime(final)

	montar_pontos = dict()
	jornadas_filtradas = dict()
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
			montar_pontos[dia_atual] = list()

		for jornada in jornadas.filter(dia=wd_atual):
			montar_pontos[dia_atual].append(jornada.hora)

	for dia, horas in montar_pontos.items():
		if dia < data_inico.date() or dia > data_final.date():
			continue

		horas_filtradas = list()
		
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


def total_saldo(queryset):
	try:
		if isinstance(queryset, list):
			horarios = queryset
		else:
			horarios = queryset.values_list('hora', flat=True)

	except Exception:
		return None
	
	total = timedelta()

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
