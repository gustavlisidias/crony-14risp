# ruff: noqa: F401
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Max, Min, Q, Value, CharField, Case, When
from django.db.models.functions import TruncDate
from django.http import HttpResponseRedirect
from django.shortcuts import redirect, render
from django.utils import timezone
from django.utils.timezone import make_aware

from datetime import datetime, timedelta
from itertools import chain
from slugify import slugify

from cities_light.models import Region as Estado
from cities_light.models import SubRegion as Cidade
from configuracoes.models import Contrato, Variavel
from funcionarios.models import Funcionario, JornadaFuncionario, Score
from funcionarios.utils import converter_documento
from ponto.models import Ponto, SolicitacaoAbono, SolicitacaoPonto, Feriados, Saldos
from ponto.renderers import RenderToPDF
from ponto.utils import pontos_por_dia
from notifications.models import Notification
from web.models import Moeda
from web.utils import not_none_not_empty, create_log, add_coins


@login_required(login_url='entrar')
def RegistrosPontoView(request):
	funcionarios = Funcionario.objects.filter(data_demissao=None).order_by('nome_completo')
	funcionario = funcionarios.get(usuario=request.user)
	notificacoes = Notification.objects.filter(recipient=request.user, unread=True)

	estados = Estado.objects.all().order_by('name')
	cidades = Cidade.objects.all().order_by('name')
	contratos = Contrato.objects.all().order_by('titulo')
	tipos = [{'key': i[0], 'value': i[1]} for i in SolicitacaoAbono.Tipo.choices]

	# Filtros
	filtros = {'inicio': None, 'final': None, 'funcionarios': None}

	if request.user.get_access == 'admin':
		filtros['funcionarios'] = funcionarios.filter(pk__in=[int(i) for i in request.GET.getlist('funcionarios')]) if request.GET.get('funcionarios') else funcionarios
	elif request.user.get_access == 'manager':
		funcionarios = funcionarios.filter(Q(gerente=funcionario) | Q(pk=funcionario.pk)).distinct()
		filtros['funcionarios'] = funcionarios.filter(pk__in=[int(i) for i in request.GET.getlist('funcionarios')]) if request.GET.get('funcionarios') else funcionarios
	else:
		funcionarios = funcionarios.filter(pk=funcionario.pk)
		filtros['funcionarios'] = funcionarios.filter(pk=funcionario.pk)

	data_ultimo_ponto = Ponto.objects.filter(funcionario__in=funcionarios).values_list('data', flat=True).distinct().order_by('-data').first()
	data_ultimo_ponto = data_ultimo_ponto if data_ultimo_ponto else datetime.today()
	filtros['final'] = request.GET.get('data_final') if request.GET.get('data_final') else data_ultimo_ponto.strftime('%Y-%m-%d')
	filtros['inicio'] = request.GET.get('data_inicial') if request.GET.get('data_inicial') else (data_ultimo_ponto - timedelta(days=6)).strftime('%Y-%m-%d')

	# Pontos e score por dia
	pontos, scores = pontos_por_dia(datetime.strptime(filtros['inicio'], '%Y-%m-%d'), datetime.strptime(filtros['final'], '%Y-%m-%d'), filtros['funcionarios'])

	# Abonos e Solicitações de Ajuste de Ponto
	abonos = SolicitacaoAbono.objects.filter(status=False, funcionario__in=funcionarios).annotate(
		tipo_label=Case(
			When(tipo=SolicitacaoAbono.Tipo.ATESTADO, then=Value('Atestado')),
			When(tipo=SolicitacaoAbono.Tipo.AUSENCIA, then=Value('Ausência Justificada')),
			When(tipo=SolicitacaoAbono.Tipo.DECLARACAO, then=Value('Declaração')),
			When(tipo=SolicitacaoAbono.Tipo.FALTA, then=Value('Falta')),
			output_field=CharField(),
	)).values(
		'inicio__date', 'funcionario__nome_completo', 'funcionario__usuario__id', 'motivo', 
		'aprovador__nome_completo', 'aprovador__usuario__id', 'caminho', 'tipo_label'
	).annotate(id=Min('id'), data=Max('inicio__date')).order_by('inicio__date').distinct()

	ajustes = SolicitacaoPonto.objects.filter(status=False, funcionario__in=funcionarios).values(
		'data', 'funcionario__nome_completo', 'funcionario__usuario__id', 'motivo', 
		'aprovador__nome_completo', 'aprovador__usuario__id'
	).annotate(id=Min('id'), tipo_label=Value('Ajuste', output_field=CharField())).order_by('data').distinct()

	solicitacoes = list(chain(abonos, ajustes))
	solicitacoes.sort(key=lambda x: x.get('inicio__date') or x.get('data'))

	# Fechamentos de Ponto
	fechamentos = Ponto.objects.filter(encerrado=True).values('data_fechamento').annotate(
		de=Min('data'), ate=Max('data')
	).order_by('data_fechamento')
	
	for fechamento in fechamentos:
		fechamento['funcionarios'] = list(Ponto.objects.filter(encerrado=True, data__range=[fechamento['de'], fechamento['ate']]).values('funcionario__id', 'funcionario__nome_completo').distinct())
	
	# Scores
	pontuacoes = Score.objects.filter(fechado=True).order_by('-data_cadastro__date', '-pontuacao')
	for score in pontuacoes:
		try:
			moedas = sum(i.pontuacao for i in Moeda.objects.filter(anomes=score.anomes, funcionario=score.funcionario, fechado=True))
		except Exception:
			moedas = 0
		score.moedas = moedas

	# Grafico
	graph = {'plot': False}
	if pontos and (len(request.GET.getlist('funcionarios')) == 1 or request.user.get_access == 'common'):
		graph['plot'] = True
		graph['notas'] = list(scores.values())[0]
		graph['total'] = timedelta(seconds=0)
		graph['saldo'] = timedelta(seconds=0)
		graph['banco'] = timedelta(seconds=0)

		for _, i in pontos.items():
			for j in i:
				graph['total'] += j['total']
				graph['saldo'] += j['saldo']
				graph['banco'] += j['banco']
	
	context = {
		'funcionarios': funcionarios,
		'funcionario': funcionario,
		'notificacoes': notificacoes,

		'estados': estados,
		'cidades': cidades,
		'contratos': contratos,
		'tipos': tipos,

		'filtros': filtros,
		'pontos': pontos,
		'scores': scores,

		'solicitacoes': solicitacoes,
		'fechamentos': fechamentos,
		'pontuacoes': pontuacoes,
		'graph': graph
	}

	return render(request, 'pages/ponto.html', context)


# Page
@login_required(login_url='entrar')
def RegistrosPontoFuncinarioView(request, func):
	funcionarios = Funcionario.objects.filter(data_demissao=None).order_by('nome_completo')
	funcionario = funcionarios.get(usuario=request.user)
	notificacoes = Notification.objects.filter(recipient=request.user, unread=True)

	colaborador = funcionarios.get(pk=func)

	jornadas = JornadaFuncionario.objects.filter(funcionario=colaborador, final_vigencia=None).order_by('funcionario__id', 'dia', 'ordem')
	
	pontos_funcionario = Ponto.objects.filter(funcionario=colaborador).values_list('data', flat=True).order_by('-data')
	data_ultimo_ponto = pontos_funcionario.first() if pontos_funcionario else datetime.today()
	data_primeiro_ponto = pontos_funcionario.last() if pontos_funcionario else (datetime.today() - timedelta(days=29))

	filtros = {'inicio': None, 'final': None, 'funcionarios': None}
	filtros['final'] = request.GET.get('data_final') if request.GET.get('data_final') else data_ultimo_ponto.strftime('%Y-%m-%d')
	filtros['inicio'] = request.GET.get('data_inicial') if request.GET.get('data_inicial') else data_primeiro_ponto.strftime('%Y-%m-%d')
	pontos, scores = pontos_por_dia(datetime.strptime(filtros['inicio'], '%Y-%m-%d'), datetime.strptime(filtros['final'], '%Y-%m-%d'), funcionarios.filter(pk=colaborador.pk))

	nro_colunas = 0
	dados = {'notas': None, 'total': timedelta(seconds=0), 'saldo': timedelta(seconds=0), 'banco': timedelta(seconds=0)}
	if pontos:
		dados['notas'] = list(scores.values())[0]
		for _, i in pontos.items():
			for j in i:
				dados['total'] += j['total']
				dados['saldo'] += j['saldo']
				dados['banco'] += j['banco']

				if len(j['pontos']) > nro_colunas:
					nro_colunas = len(j['pontos'])

	context = {
		'funcionarios': funcionarios,
		'funcionario': funcionario,
		'notificacoes': notificacoes,
		'colaborador': colaborador,
		'jornadas': jornadas,
		'filtros': filtros,
		'pontos': pontos,
		'dados': dados,
		'nro_colunas': range(nro_colunas),
	}
	return render(request, 'pages/ponto-funcionario.html', context)


# Modal
@login_required(login_url='entrar')
def SolicitarAbonoView(request):
	if not request.method == 'POST':
		messages.warning(request, 'Método não permitido!')
		return redirect('pontos')

	funcionario = Funcionario.objects.get(usuario=request.user)
	admin = Funcionario.objects.filter(data_demissao=None, matricula__in=[i.strip() for i in Variavel.objects.get(chave='RESP_USERS').valor.split(',')]).first()

	inicio = request.POST.get('inicio')
	final = request.POST.get('final')
	tipo = request.POST.get('tipo')
	motivo = request.POST.get('motivo')
	arquivo = request.FILES.get('arquivo')

	nome, documento = None, None
	if arquivo:
		nome, documento = converter_documento(arquivo)
		if nome is None:
			messages.error(request, 'Os documentos devem ser do tipo JPG, PNG, GIF ou PDF!')
			return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))

	if not_none_not_empty(inicio, final, tipo, motivo):
		try:
			solicitacao = SolicitacaoAbono.objects.create(
				funcionario=funcionario,
				inicio=make_aware(datetime.strptime(inicio, '%Y-%m-%dT%H:%M')),
				final=make_aware(datetime.strptime(final, '%Y-%m-%dT%H:%M')),
				tipo=tipo,
				motivo=motivo,
				documento=documento,
				caminho=f'{nome}.pdf' if nome else None,
			)

			solicitacao.aprovador = funcionario.gerente or admin
			solicitacao.save()

			add_coins(funcionario, 5)

			create_log(
				object_model=SolicitacaoAbono,
				object_id=solicitacao.id,
				user=funcionario.usuario,
				message='Nova solicitação de abono criada',
				action=1
			)
			
			messages.success(request, 'Solicitação enviada com sucesso!')

		except Exception as e:
			messages.error(request, e)

	else:
		messages.error(request, 'Preencha todos os campos obrigatórios!')

	return redirect('pontos')


# Modal
@login_required(login_url='entrar')
def AdicionarFeriadoView(request):
	if not request.method == 'POST':
		messages.warning(request, 'Método não permitido!')
		return redirect('pontos')

	try:
		titulo = request.POST.get('titulo')
		data_feriado = request.POST.get('data')
		contrato = request.POST.get('contrato')
		estado = request.POST.get('estado')
		cidade = request.POST.get('cidade')

		if not_none_not_empty(titulo, data_feriado):
			funcionarios = JornadaFuncionario.objects.filter(funcionario__data_demissao=None, final_vigencia=None).order_by('funcionario__id', 'dia', 'ordem').values(
				'funcionario__id', 'contrato__titulo', 'funcionario__estado__pk', 'funcionario__cidade__pk'
			).distinct()

			if contrato:
				funcionarios = funcionarios.filter(contrato__titulo__icontains=contrato.lower())
			
			if estado:
				funcionarios = funcionarios.filter(funcionario__estado__pk=estado)

			if cidade:
				funcionarios = funcionarios.filter(funcionario__cidade__pk=cidade)

			if len(funcionarios) == 0:
				messages.warning(request, 'Feriado não foi adicionado! Não foram encontrados funcionários na modalidade selecionada!')
				return redirect('pontos')

			with transaction.atomic():
				feriado = Feriados.objects.create(
					titulo=titulo,
					data=data_feriado
				)
				
				feriado.funcionarios.set([i['funcionario__id'] for i in funcionarios])
				feriado.save()

				create_log(
					object_model=Feriados,
					object_id=feriado.id,
					user=request.user,
					message='Novo feriado criado',
					action=1
				)

			messages.success(request, 'Feriado adicionado com sucesso!')

		else:
			messages.warning(request, 'Preencha todos os campos obrigatórios!')

	except Exception as e:
		messages.error(request, e)

	return redirect('pontos')


# Modal
@login_required(login_url='entrar')
def AdicionarSaldoView(request):
	if not request.method == 'POST':
		messages.warning(request, 'Método não permitido!')
		return redirect('pontos')

	try:
		data = request.POST.get('data')
		funcionario = Funcionario.objects.get(pk=int(request.POST.get('funcionario')))
		intervalo = request.POST.get('intervalo').strip().split(':') # 00:00:00 ou -00:00:00

		minutos = int(intervalo[1])
		segundos = int(intervalo[2])
		if '-' in intervalo[0]:
			horas = abs(int(intervalo[0])) * 60 * 60
			minutos = minutos * 60
			segundos = (segundos + minutos + horas) * -1
			saldo = timedelta(seconds=segundos)
		else:
			horas = abs(int(intervalo[0]))
			saldo = timedelta(hours=horas, minutes=minutos, seconds=segundos)

		if not_none_not_empty(data):
			saldo = Saldos.objects.create(
				funcionario=funcionario,
				data=data,
				saldo=saldo
			)

			create_log(
				object_model=Saldos,
				object_id=saldo.id,
				user=request.user,
				message=f'Novo saldo criado para {funcionario.nome_completo}',
				action=1
			)
			
			messages.success(request, 'Saldo adicionado com sucesso!')

		else:
			messages.warning(request, 'Preencha todos os campos obrigatórios!')

	except Exception as e:
		messages.error(request, e)

	return redirect('pontos')


# Modal
@login_required(login_url='entrar')
def ExcluirFechamentoView(request):
	if not request.method == 'POST':
		messages.warning(request, 'Método não permitido!')
		return redirect('pontos')
	
	try:
		data_inicial = datetime.strptime(request.POST.get('inicio'), '%d/%m/%Y')
		data_final = datetime.strptime(request.POST.get('final'), '%d/%m/%Y')
		
		if request.POST.get('funcionario'):
			funcionario = Funcionario.objects.get(pk=int(request.POST.get('funcionario')))
			pontos = Ponto.objects.filter(encerrado=True, data__range=[data_inicial, data_final], funcionario=funcionario)

			for ponto in pontos:
				ponto.encerrado = False
				ponto.data_fechamento = None
				ponto.save()

			messages.success(request, 'Pontos reabertos!')

		elif request.POST.get('relatorio'):
			dados_empresa = {'nome': Variavel.objects.get(chave='NOME_EMPRESA').valor, 'cnpj': Variavel.objects.get(chave='CNPJ').valor, 'inscricao': Variavel.objects.get(chave='INSC_ESTADUAL').valor}
			funcionario = Funcionario.objects.get(pk=int(request.POST.get('relatorio')))
			pontos, _ = pontos_por_dia(data_inicial, data_final, funcionario)
			if not pontos:
				raise ValueError('Nenhum ponto encontrado')

			jornadas = JornadaFuncionario.objects.filter(funcionario=funcionario, final_vigencia=None).order_by('funcionario__id', 'dia', 'ordem')
			jornada = {}
			for item in jornadas.order_by('dia', 'hora'):
				if item.dia not in jornada:
					jornada[item.dia] = []
					jornada[item.dia].append({'tipo': item.get_tipo_display(), 'hora': item.hora, 'contrato': item.contrato})

			nro_colunas = 0
			saldos = {'total': timedelta(seconds=0), 'saldo': timedelta(seconds=0), 'credito': timedelta(seconds=0), 'debito': timedelta(seconds=0)}
			for _, dados in pontos.items():
				for dado in dados:
					saldos['total'] += dado['total']
					saldos['saldo'] += dado['saldo']

					if dado['saldo'] < timedelta(0):
						saldos['debito'] += dado['saldo']
					else:
						saldos['credito'] += dado['saldo']

					if len(dado['pontos']) % 2 != 0:
						raise ValueError('Número ímpar de registros de pontos')
					if len(dado['pontos']) > nro_colunas:
						nro_colunas = len(dado['pontos'])
			
			filename = f'espelho_ponto_{funcionario.nome_completo.lower()}.pdf'
			context = {
				'pontos': pontos,
				'saldos': saldos,
				'funcionario': funcionario,
				'periodo': {'inicio': data_inicial, 'final': data_final},
				'nro_colunas': range(nro_colunas),
				'autor': Funcionario.objects.get(usuario=request.user),
				'jornada': jornada,
				'dados_empresa': dados_empresa
			}

			return RenderToPDF(request, 'relatorios/espelho_ponto.html', context, filename).weasyprint()

		else:
			pontos = Ponto.objects.filter(encerrado=True, data__range=[data_inicial, data_final])

			for ponto in pontos:
				ponto.encerrado = False
				ponto.data_fechamento = None
				ponto.save()

			messages.success(request, 'Pontos reabertos!')

	except Exception as e:
		messages.error(request, e)

	return redirect('pontos')


# Page
@login_required(login_url='entrar')
def RegistrarPontoExternoView(request):
	funcionarios = Funcionario.objects.filter(data_demissao=None).order_by('nome_completo')
	funcionario = funcionarios.get(usuario=request.user)
	ponto = Ponto.objects.filter(funcionario=funcionario).order_by('id').last()

	context = {
		'funcionarios': funcionarios,
		'funcionario': funcionario,
		'ponto': datetime.combine(ponto.data, ponto.hora) if ponto else None,
	}
	return render(request, 'pages/ponto-externo.html', context)
