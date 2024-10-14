import time

from django.db.models import Case, When, Value
from django.db.models.query import QuerySet
from django.utils import timezone

from datetime import date, datetime, timedelta, time as create_time

from funcionarios.models import Score, JornadaFuncionario, Funcionario
from ponto.models import SolicitacaoAbono, SolicitacaoPonto, Ponto, Saldos, Feriados


def filtrar_abonos(solicitacao):
	data_inico = timezone.localtime(solicitacao.inicio)
	data_final = timezone.localtime(solicitacao.final)

	montar_pontos = {}
	jornadas_filtradas = {}
	nro_dias = (data_final.date() - data_inico.date()).days

	if data_inico.date() == data_final.date():
		wd_incio = 1 if data_inico.date().weekday() + 2 == 8 else data_inico.date().weekday() + 2
		jornadas = JornadaFuncionario.objects.filter(funcionario=solicitacao.funcionario, final_vigencia=None, dia=wd_incio).order_by('funcionario__id', 'dia', 'ordem')
	else:
		jornadas = JornadaFuncionario.objects.filter(funcionario=solicitacao.funcionario, final_vigencia=None).order_by('funcionario__id', 'dia', 'ordem')

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


def parse_date(data):
	try:
		if isinstance(data, str):
			if '-' in data:
				try:
					return datetime.strptime(data, '%Y-%m-%d')
				except Exception:
					return datetime.strptime(data, '%d-%m-%Y')
			if '/' in data:
				return datetime.strptime(data, '%d/%m/%Y')
		elif isinstance(data, datetime):
			return data
		elif isinstance(data, date):
			return datetime.combine(data, datetime.min.time())
		elif isinstance(data, time):
			return datetime.combine(datetime.min.date(), data)
		else:
			return None
	except Exception:
		return None
	

def parse_employee(objeto):
	try:
		if objeto is None:
			return None
		elif isinstance(objeto, list):
			return Funcionario.objects.filter(pk__in=objeto)
		elif isinstance(objeto, QuerySet):
			return objeto
		else:
			return Funcionario.objects.filter(pk=objeto.pk)
	except Exception:
		return None
	

def pontos_por_dia(data_inicial=None, data_final=None, funcionarios=None, fechamento=False):
	data_inicial = parse_date(data_inicial)
	data_final = parse_date(data_final)
	funcionarios = parse_employee(funcionarios)

	if not (data_inicial and data_final and funcionarios):
		return None, None

	pontos = Ponto.objects.filter(data__range=[data_inicial, data_final], funcionario__in=funcionarios).order_by('funcionario', 'data', 'hora')
	jornadas = JornadaFuncionario.objects.filter(funcionario__in=funcionarios).annotate(
		vencimento=Case(
			When(final_vigencia__isnull=True, then=Value(date.today())),
			default='final_vigencia'
		)
	).order_by('funcionario', 'dia', 'ordem')
	scores = {score.funcionario.id: score.pontuacao for score in Score.objects.filter(fechado=False)}

	if not (pontos and jornadas):
		return None, None
	
	solicitacoes = SolicitacaoPonto.objects.filter(funcionario__in=funcionarios, status=False).values('funcionario__id', 'data').distinct()
	abonos = SolicitacaoAbono.objects.filter(funcionario__in=funcionarios, status=False).values('funcionario__id', 'inicio__date').distinct()

	feriados = {}
	for i in Feriados.objects.all():
		feriados[i.data] = i.funcionarios.all()

	saldos = {}
	for i in Saldos.objects.all().order_by('funcionario__id', 'data'):
		if i.funcionario.id not in saldos:
			saldos[i.funcionario.id] = {}
		if i.data not in saldos[i.funcionario.id]:
			saldos[i.funcionario.id][i.data] = timedelta(seconds=0)
		saldos[i.funcionario.id][i.data] += i.saldo

	pendencias = [{'data': i['data'], 'funcionario': i['funcionario__id']} for i in solicitacoes]
	pendencias.extend([{'data': i['inicio__date'], 'funcionario': i['funcionario__id']} for i in abonos])

	dias_por_funcionario = {data_atual: [] for data_atual in (data_inicial + timedelta(days=n) for n in range((data_final - data_inicial).days + 1))}
	score_por_funcionario = {}

	inicio = time.time()

	for data in dias_por_funcionario:
		for funcionario in funcionarios:
			
			pontos_funcionario, encerrado = [], False
			motivo = None
			for i in pontos.filter(funcionario=funcionario, data=data):
				pontos_funcionario.append(i.hora)
				if i.encerrado:
					encerrado = True
				if i.motivo:
					motivo = i.motivo
				if not motivo and i.data.weekday() in [5, 6]:
					motivo = '.'

			if data.weekday() in [5, 6] and motivo is None:
				motivo = 'Descanso remunerado'
			
			dias_por_funcionario[data].append({
				'funcionario': funcionario,
				'pontos': pontos_funcionario,
				'encerrado': encerrado,
				'pendente': funcionario.id in [i['funcionario'] for i in pendencias if i['data'] == data.date() and i['funcionario'] == funcionario.id],
				'motivo': motivo,
				'total': timedelta(seconds=0),
				'saldo': saldos.get(funcionario.id, {}).get(data.date(), timedelta(seconds=0)),
				'score': scores.get(funcionario.id, 0),
				'banco': timedelta(seconds=0),
				'regra': ''
			})
	
	fim = time.time()
	print(f'\ndias por funcionario: {fim - inicio}')
	
	inicio = time.time()
	
	for dia, dados in dias_por_funcionario.items():
		for dado in dados:
			
			if dado['funcionario'] not in score_por_funcionario:
				score_por_funcionario[dado['funcionario']] = [0, 0, []]
			
			pontos = dado['pontos']
			qtd_pontos = len(pontos)

			if qtd_pontos > 0:
				# Calculo do total diário
				# Só posso calcular o total de duplas entrada-saida
				if qtd_pontos % 2 == 0:
					for i in range(0, qtd_pontos, 2):
						dado['total'] += timedelta(
							hours=(pontos[i+1].hour - pontos[i].hour),
							minutes=(pontos[i+1].minute - pontos[i].minute),
							seconds=(pontos[i+1].second - pontos[i].second)
						)
				###########################################################

				# Calculo do saldo diário
				weekday = 1 if dia.weekday() + 2 == 8 else dia.weekday() + 2
				jornada = jornadas.filter(funcionario=dado['funcionario'], inicio_vigencia__lte=dia.date(), vencimento__gt=dia.date(), dia=weekday).values_list('hora', flat=True)
				qtd_jornada = len(jornada)

				tolerancia = timedelta(minutes=10) if dado['funcionario'].get_contrato.slug.split('-')[0] == 'clt' else timedelta(minutes=5)
				total_esperado = timedelta(seconds=0)
				
				if jornada:
					for i in range(0, qtd_jornada, 2):
						total_esperado += timedelta(
							hours=(jornada[i+1].hour - jornada[i].hour),
							minutes=(jornada[i+1].minute - jornada[i].minute),
							seconds=(jornada[i+1].second - jornada[i].second)
						)

				# Saldo negativo no dia, vindo por saldos.get(funcionario.id, {}).get(data.date(), timedelta(seconds=0)),
				if dado['saldo'] < timedelta(0):
					dado['score'] -= 0.25
				
				# Trabalhei menos
				if (dado['total'] + tolerancia) < total_esperado:
					dado['saldo'] += dado['total'] - total_esperado
					dado['score'] -= 0.25
				
				# Trabalhei mais	
				if dado['total'] > total_esperado:
					dado['saldo'] += dado['total'] - total_esperado
				###########################################################

				# Calculo do Banco de Horas
				if dado['saldo'] > timedelta(0):
					feriado = feriados.get(dia.date())
					if (feriado and dado['funcionario'] in feriado) or (weekday in [1, 7]):
						dado['banco'] = dado['saldo'] * 2
						dado['regra'] = f"{round(dado['saldo'].total_seconds() / 3600, 2)}h +100%"
					
					elif dado['pontos'][-1] > create_time(22, 0):
						noturno = datetime.combine(datetime.today(), dado['pontos'][-1]) - datetime.combine(datetime.today(), create_time(22, 0))
						total_noturno = noturno + noturno * 1.1
						saldo_restante = dado['saldo'] - noturno
					
						if saldo_restante > timedelta(minutes=120):
							saldo_apos_2horas = saldo_restante - timedelta(minutes=120) + (saldo_restante - timedelta(minutes=120)) * 0.8
							dado['banco'] = total_noturno + timedelta(minutes=192) + saldo_apos_2horas
							dado['regra'] = f"2.0h +60%, {round((saldo_restante - timedelta(minutes=120)).total_seconds() / 3600, 2)} +80%, {round(noturno.total_seconds() / 3600, 2)}h +110%"
						else:
							dado['banco'] = total_noturno + (saldo_restante + saldo_restante * 0.6)
							dado['regra'] = f"{round(saldo_restante.total_seconds() / 3600, 2)}h +60%, {round(noturno.total_seconds() / 3600, 2)}h +110%"
					
					elif dado['saldo'] > timedelta(minutes=120):
						dado['banco'] = timedelta(minutes=192) + (dado['saldo'] - timedelta(minutes=120)) + ((dado['saldo'] - timedelta(minutes=120)) * 0.8)
						dado['regra'] = f"2.0h +60%, {round((dado['saldo'] - timedelta(minutes=120)).total_seconds() / 3600, 2)}h +80%"
					else:
						dado['banco'] = dado['saldo'] + (dado['saldo'] * 0.6)
						dado['regra'] = f"{round(dado['saldo'].total_seconds() / 3600, 2)}h +60%"
				else:
					dado['banco'] = dado['saldo']
				###########################################################

				# Calculo do score diário
				if qtd_jornada == qtd_pontos:
					for j, p in zip(jornada, pontos):
						periodo = [datetime.combine(datetime.today(), j) - tolerancia, datetime.combine(datetime.today(), j) + tolerancia]
						registro = datetime.combine(datetime.today(), p)
						if not (registro >= periodo[0] and registro <= periodo [1]):
							dado['score'] -= 0.25
				
				# Normalizando o score diário final
				dado['score'] = 5 if dado['score'] > 5 else dado['score']
				score_por_funcionario[dado['funcionario']][2].append(dado['score'])
				###########################################################
	
	fim = time.time()
	print(f'score por funcionario: {fim - inicio}\n')

	for funcionario, notas in score_por_funcionario.items():
		if notas[2]:
			media = sum(notas[2]) / len(notas[2])
			notas[0] = media
			notas[1] = media * 100 / 5
	
	if fechamento:
		mes = datetime.today().month - 1

		for funcionario in funcionarios:
			ajustes = SolicitacaoPonto.objects.filter(funcionario=funcionario, status=True, data_cadastro__month=mes)
			abonos = SolicitacaoAbono.objects.filter(funcionario=funcionario, status=True, data_cadastro__month=mes)
			cargo = funcionario.cargo.slug

			total_ajustes = ajustes.count() * 0.01
			total_declaracoes = abonos.filter(tipo=SolicitacaoAbono.Tipo.DECLARACAO).count() * 0.04
			total_atestados = abonos.exclude(tipo__in=[SolicitacaoAbono.Tipo.DECLARACAO, SolicitacaoAbono.Tipo.FALTA]).count() * 0.08
			total_faltas = abonos.filter(tipo=SolicitacaoAbono.Tipo.FALTA).count() * 1.25
			total_desconto = total_ajustes + total_atestados + total_declaracoes + total_faltas

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
