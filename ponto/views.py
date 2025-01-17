from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Min, Q, Max
from django.http import HttpResponseRedirect
from django.shortcuts import redirect, render
from django.utils import timezone
from django.utils.timezone import make_aware

from datetime import datetime, timedelta, date

from cities_light.models import Region as Estado
from cities_light.models import SubRegion as Cidade
from configuracoes.models import Contrato, Variavel
from funcionarios.models import Funcionario, JornadaFuncionario, Score
from funcionarios.utils import converter_documento
from ponto.models import Ponto, SolicitacaoAbono, SolicitacaoPonto, Feriados, Saldos
from ponto.report import gerar_pdf_ponto
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
	tipos = {i[0]: i[1] for i in SolicitacaoAbono.Tipo.choices}

	# Filtros
	filtros = {'inicio': None, 'final': None, 'funcionarios': None}
	if request.user.get_access == 'admin':
		funcionarios = funcionarios.filter(visivel=True)
		filtros['funcionarios'] = funcionarios.filter(pk__in=[int(i) for i in request.GET.getlist('funcionarios')]) if request.GET.get('funcionarios') else funcionarios
		delta = timedelta(days=0)
	elif request.user.get_access == 'manager':
		funcionarios = funcionarios.filter(Q(gerente=funcionario) | Q(pk=funcionario.pk)).distinct()
		filtros['funcionarios'] = funcionarios.filter(pk__in=[int(i) for i in request.GET.getlist('funcionarios')]) if request.GET.get('funcionarios') else funcionarios
		delta = timedelta(days=2)
	else:
		funcionarios = funcionarios.filter(pk=funcionario.pk)
		filtros['funcionarios'] = funcionarios.filter(pk=funcionario.pk)
		delta = timedelta(days=6)

	data_ultimo_ponto = Ponto.objects.filter(funcionario__in=funcionarios).exclude(motivo='Férias').values_list('data', flat=True).distinct().order_by('-data').first()
	data_ultimo_ponto = data_ultimo_ponto if data_ultimo_ponto else datetime.today()
	filtros['final'] = request.GET.get('data_final') if request.GET.get('data_final') else data_ultimo_ponto.strftime('%Y-%m-%d')
	filtros['inicio'] = request.GET.get('data_inicial') if request.GET.get('data_inicial') else (data_ultimo_ponto - delta).strftime('%Y-%m-%d')

	# Pontos e score por dia
	pontos, scores = pontos_por_dia(datetime.strptime(filtros['inicio'], '%Y-%m-%d'), datetime.strptime(filtros['final'], '%Y-%m-%d'), filtros['funcionarios'])

	# Abonos e Solicitações de Ajuste de Ponto
	solicitacoes_ajuste = SolicitacaoPonto.objects.filter(funcionario__in=funcionarios, status=False).values('funcionario__usuario__id', 'funcionario__nome_completo', 'aprovador__usuario__id' ,'aprovador__nome_completo', 'data', 'motivo').annotate(id=Min('id')).order_by('data').distinct()
	solicitacoes_abono = SolicitacaoAbono.objects.filter(funcionario__in=funcionarios, status=False).values('id', 'funcionario__usuario__id', 'funcionario__nome_completo', 'aprovador__usuario__id' ,'aprovador__nome_completo', 'inicio__date', 'motivo', 'tipo', 'caminho').order_by('inicio__date').distinct()
	
	solicitacoes = [{
		'id': i['id'], 'funcionario': i['funcionario__nome_completo'], 'funcionario_id': i['funcionario__usuario__id'], 
		'aprovador': i['aprovador__nome_completo'], 'aprovador_id': i['aprovador__usuario__id'], 
		'data': i['data'], 'motivo': i['motivo'], 'tipo': 'Ajuste', 'caminho': None
	} for i in solicitacoes_ajuste]

	solicitacoes.extend([{
		'id': i['id'], 'funcionario': i['funcionario__nome_completo'], 'funcionario_id': i['funcionario__usuario__id'], 
		'aprovador': i['aprovador__nome_completo'], 'aprovador_id': i['aprovador__usuario__id'], 
		'data': i['inicio__date'], 'motivo': i['motivo'], 'tipo': tipos.get(i['tipo']), 'caminho': i['caminho']
	} for i in solicitacoes_abono])

	solicitacoes = sorted(solicitacoes, key=lambda x: x['data'])

	# Fechamentos de Ponto
	fechamentos_dict = {}
	for i in Ponto.objects.filter(encerrado=True).exclude(data_fechamento=None).values('data_fechamento', 'data', 'funcionario__id', 'funcionario__nome_completo').distinct():
		if i['data_fechamento'] not in fechamentos_dict:
			fechamentos_dict[i['data_fechamento']] = {'de': None, 'ate': None, 'funcionarios': []}
		
		if not fechamentos_dict[i['data_fechamento']]['de'] or i['data'] < fechamentos_dict[i['data_fechamento']]['de']:
			fechamentos_dict[i['data_fechamento']]['de'] = i['data']
		
		if not fechamentos_dict[i['data_fechamento']]['ate'] or i['data'] > fechamentos_dict[i['data_fechamento']]['ate']:
			fechamentos_dict[i['data_fechamento']]['ate'] = i['data']
		
		ele = {
			'funcionario__id': i['funcionario__id'],
			'funcionario__nome_completo': i['funcionario__nome_completo']
		}

		if ele not in fechamentos_dict[i['data_fechamento']]['funcionarios']:
			fechamentos_dict[i['data_fechamento']]['funcionarios'].append(ele)
	
	fechamentos = [
		{'data_fechamento': data_fechamento, 'de': dados['de'], 'ate': dados['ate'], 'funcionarios': dados['funcionarios']}
		for data_fechamento, dados in fechamentos_dict.items()
	]

	# Scores Mensais
	anomes = int(f'{date.today().year}{date.today().month:02}')
	moedas = Moeda.objects.filter(fechado=True, anomes__lt=anomes, funcionario__visivel=True).values('funcionario__id', 'pontuacao', 'anomes')
	pontuacoes = Score.objects.filter(fechado=True, anomes__lt=anomes, funcionario__visivel=True).order_by('-data_cadastro__date', '-pontuacao')
	for score in pontuacoes:
		score.moedas = sum([q['pontuacao'] for q in moedas if q['funcionario__id'] == score.funcionario.id and q['anomes'] == score.anomes])

	# Grafico
	graph = {'plot': False}
	if pontos and (len(request.GET.getlist('funcionarios')) == 1 or request.user.get_access == 'common'):
		graph['plot'] = True
		graph['notas'] = scores.get(filtros['funcionarios'].first().id)
		graph['total'] = timedelta(seconds=0)
		graph['saldo'] = timedelta(seconds=0)

		for _, funcs in pontos.items():
			for func, dados in funcs.items():
				graph['total'] += dados['total']
				graph['saldo'] += dados['saldo']
	
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

	jornada = []
	for i in JornadaFuncionario.objects.filter(funcionario=colaborador, final_vigencia=None).order_by('funcionario__id', 'agrupador', 'dia', 'ordem'):
		if i.dia == 2:
			jornada.append(i.hora)
	
	pontos_funcionario = Ponto.objects.filter(funcionario=colaborador).values_list('data', flat=True).order_by('-data')
	data_ultimo_ponto = pontos_funcionario.first() if pontos_funcionario else datetime.today()
	data_primeiro_ponto = pontos_funcionario.last() if pontos_funcionario else (datetime.today() - timedelta(days=29))

	filtros = {'inicio': None, 'final': None, 'funcionarios': None}
	filtros['final'] = request.GET.get('data_final') if request.GET.get('data_final') else data_ultimo_ponto.strftime('%Y-%m-%d')
	filtros['inicio'] = request.GET.get('data_inicial') if request.GET.get('data_inicial') else data_primeiro_ponto.strftime('%Y-%m-%d')
	pontos, scores = pontos_por_dia(datetime.strptime(filtros['inicio'], '%Y-%m-%d'), datetime.strptime(filtros['final'], '%Y-%m-%d'), funcionarios.filter(pk=colaborador.pk))

	solicitacoes_ajuste = SolicitacaoPonto.objects.filter(funcionario=colaborador).values('data', 'motivo', 'status').annotate(inicio=Min('hora'), final=Max('hora')).values('data', 'motivo', 'status', 'inicio', 'final')
	solicitacoes_abono = SolicitacaoAbono.objects.filter(funcionario=colaborador)
	solicitacoes = [{'data': i['data'], 'motivo': i['motivo'], 'status': i['status'], 'categoria': 'Ajuste', 'inicio': datetime.combine(i['data'], i['inicio']), 'final': datetime.combine(i['data'], i['final'])} for i in solicitacoes_ajuste]
	solicitacoes.extend([{'data': i.inicio.date, 'motivo': i.motivo, 'status': i.status, 'categoria': i.get_tipo, 'inicio': i.inicio, 'final': i.final } for i in solicitacoes_abono])

	nro_colunas = 0
	graph = {'notas': scores.get(colaborador.id), 'total': timedelta(seconds=0), 'saldo': timedelta(seconds=0)}
	if pontos:
		for _, funcs in pontos.items():
			for func, dados in funcs.items():
				graph['total'] += dados['total']
				graph['saldo'] += dados['saldo']

				if len(dados['pontos']) > nro_colunas:
					nro_colunas = len(dados['pontos'])

	context = {
		'funcionarios': funcionarios,
		'funcionario': funcionario,
		'notificacoes': notificacoes,
		'colaborador': colaborador,
		'jornada': jornada,
		'filtros': filtros,
		'pontos': pontos,
		'graph': graph,
		'nro_colunas': range(nro_colunas),
		'solicitacoes': solicitacoes
	}
	return render(request, 'pages/ponto-funcionario.html', context)


# Modal
@login_required(login_url='entrar')
def SolicitarAbonoView(request):
	if not request.method == 'POST':
		messages.warning(request, 'Método não permitido!')
		return redirect('pontos')

	funcionario = Funcionario.objects.get(pk=int(request.POST.get('colaborador'))) if not_none_not_empty(request.POST.get('colaborador')) else Funcionario.objects.get(usuario=request.user)
	admin = Funcionario.objects.filter(data_demissao=None, matricula__in=[i.strip() for i in Variavel.objects.get(chave='RESP_USERS').valor.split(',')]).first()

	solicitacao = request.POST.get('solicitacao')
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

	if not_none_not_empty(solicitacao, tipo, motivo):
		if solicitacao == 'tempo':
			dia = datetime.strptime(request.POST.get('data'), '%Y-%m-%d').date()
			weekday = 1 if dia.weekday() + 2 == 8 else dia.weekday() + 2

			pontos_dia = Ponto.objects.filter(funcionario=funcionario, data=dia, alterado=False).order_by('hora')
			jornada_dia = JornadaFuncionario.objects.filter(funcionario=funcionario, dia=weekday, final_vigencia=None).order_by('ordem')

			if pontos_dia:
				inicio = make_aware(datetime.combine(dia, pontos_dia.last().hora))
			else:
				inicio = make_aware(datetime.combine(dia, jornada_dia.first().hora))
			
			final = make_aware(datetime.combine(dia, jornada_dia.last().hora))
		else:
			inicio = make_aware(datetime.strptime(inicio, '%Y-%m-%dT%H:%M'))
			final = make_aware(datetime.strptime(final, '%Y-%m-%dT%H:%M'))
		
		try:
			solicitacao = SolicitacaoAbono.objects.create(
				funcionario=funcionario,
				inicio=inicio,
				final=final,
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
			funcionarios = JornadaFuncionario.objects.filter(funcionario__data_demissao=None, final_vigencia=None).order_by('funcionario__id', 'agrupador', 'dia', 'ordem').values(
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
			funcionario = Funcionario.objects.get(pk=int(request.POST.get('relatorio')))
			response = gerar_pdf_ponto(request, funcionario, data_inicial, data_final)
			return response if response else redirect('pontos')

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

	if request.POST:
		conf_permissao = Variavel.objects.filter(chave='REGISTRO_EXTERNO').first()
		conf_matriculas = Variavel.objects.filter(chave='MATRICULAS_EXTERNAS').first()

		permitir = conf_permissao.valor == 'True' if conf_permissao else False
		matriculas = [i.strip() for i in conf_matriculas.valor.split(',')] if conf_matriculas else []
		funcionario = Funcionario.objects.get(usuario=request.user)
		
		if permitir and funcionario.matricula in matriculas:
			ponto = Ponto.objects.create(
				funcionario=funcionario,
				data=timezone.localdate(),
				hora=timezone.localtime(),
				autor_modificacao=funcionario
			)

			create_log(
				object_model=Ponto,
				object_id=ponto.id,
				user=funcionario.usuario,
				message='Ponto cadastrado',
				action=1
			)

			messages.success(request, 'Ponto registrado com sucesso!')
		
		else:
			messages.error(request, 'Ponto não registrado! Este usuário não está liberado para registros externos.')

		return redirect('registrar-externo')

	context = {
		'funcionarios': funcionarios,
		'funcionario': funcionario,
		'ponto': datetime.combine(ponto.data, ponto.hora) if ponto else None,
	}

	return render(request, 'pages/ponto-externo.html', context)
