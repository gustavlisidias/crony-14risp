import math
import json

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Min, Q, Max
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.csrf import csrf_exempt
from django.utils.timezone import make_aware

from datetime import datetime, timedelta, time

from cities_light.models import Region as Estado
from cities_light.models import SubRegion as Cidade
from configuracoes.models import Contrato, Variavel
from funcionarios.models import Funcionario, JornadaFuncionario
from funcionarios.utils import converter_documento
from notifications.signals import notify
from ponto.models import Ponto, SolicitacaoAbono, SolicitacaoPonto, Feriados, Saldos, Fechamento
from ponto.report import gerar_pdf_ponto
from ponto.utils import pontos_por_dia
from web.decorators import base_context_required, record_time  # noqa: F401
from web.utils import not_none_not_empty, create_log
from web.views import ADMIN_USER


# Page
# @record_time
@base_context_required
def RegistrosPontoView(request, context):
	funcionarios = context['funcionarios']
	funcionario = context['funcionario']

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

	data_ultimo_ponto = Ponto.objects.filter(funcionario__in=funcionarios, encerrado=False).exclude(motivo='Férias').values_list('data', flat=True).distinct().order_by('-data').first()
	data_ultimo_ponto = data_ultimo_ponto if data_ultimo_ponto else datetime.today()
	filtros['final'] = request.GET.get('data_final', data_ultimo_ponto.strftime('%Y-%m-%d'))
	filtros['inicio'] = request.GET.get('data_inicial', (data_ultimo_ponto - delta).strftime('%Y-%m-%d'))

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
	fechamentos_dict = dict()
	for i in Ponto.objects.exclude(data_fechamento=None).values('data_fechamento', 'data', 'funcionario__id', 'funcionario__nome_completo').distinct():
		if i['data_fechamento'] not in fechamentos_dict:
			fechamentos_dict[i['data_fechamento']] = {'de': None, 'ate': None, 'funcionarios': list()}
		
		if not fechamentos_dict[i['data_fechamento']]['de'] or i['data'] < fechamentos_dict[i['data_fechamento']]['de']:
			fechamentos_dict[i['data_fechamento']]['de'] = i['data']
		
		if not fechamentos_dict[i['data_fechamento']]['ate'] or i['data'] > fechamentos_dict[i['data_fechamento']]['ate']:
			fechamentos_dict[i['data_fechamento']]['ate'] = i['data']
		
		func = {
			'funcionario__id': i['funcionario__id'],
			'funcionario__nome_completo': i['funcionario__nome_completo']
		}

		if func not in fechamentos_dict[i['data_fechamento']]['funcionarios']:
			fechamentos_dict[i['data_fechamento']]['funcionarios'].append(func)
	
	fechamentos = sorted([
		{'data_fechamento': data_fechamento, 'de': dados['de'], 'ate': dados['ate'], 'funcionarios': dados['funcionarios']}
		for data_fechamento, dados in fechamentos_dict.items()
	], key=lambda x: x['de'], reverse=True)

	# Fechamento de Scores + Moedas Mensais
	pontuacoes = Fechamento.objects.filter(funcionario__visivel=True).order_by('-referencia', '-pontuacao', '-moedas')
	for i in pontuacoes:
		i.nota_final = (i.pontuacao * 0.7) + ((math.log(i.moedas, 5)) * 0.3)

	# Pontos, score por dia -> Grafico
	pontos, scores = pontos_por_dia(datetime.strptime(filtros['inicio'], '%Y-%m-%d'), datetime.strptime(filtros['final'], '%Y-%m-%d'), filtros['funcionarios'])
	graph = {'plot': False, 'notas': list(), 'total': timedelta(), 'saldo': timedelta(), 'banco': timedelta()}
	if len(request.GET.getlist('funcionarios')) == 1 or request.user.get_access == 'common':
		colaborador_id = filtros['funcionarios'].first().id
		if pontos and scores:
			data_ultimo_registro = max(pontos.keys(), key=lambda x: x)

			graph['plot'] = True
			graph['notas'] = scores.get(colaborador_id)
			graph['banco'] = pontos.get(data_ultimo_registro).get(colaborador_id).get('banco')

			for _, funcs in pontos.items():
				for __, dados in funcs.items():
					graph['total'] += dados['total']
					graph['saldo'] += dados['saldo']
	
	context.update({
		'funcionarios': funcionarios,
		'funcionario': funcionario,

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
	})

	return render(request, 'pages/ponto.html', context)


# Page
@base_context_required
def RegistrosPontoFuncinarioView(request, context, func):
	funcionarios = context['funcionarios']
	colaborador = Funcionario.objects.get(pk=func)

	jornada = list()
	for i in JornadaFuncionario.objects.filter(funcionario=colaborador, final_vigencia=None).order_by('funcionario__id', 'agrupador', 'dia', 'ordem'):
		if i.dia == 2:
			jornada.append(i.hora)
	
	# pontos_funcionario = Ponto.objects.filter(funcionario=colaborador, encerrado=False).exclude(motivo='Férias').values_list('data', flat=True).order_by('-data')
	pontos_funcionario = Ponto.objects.filter(funcionario=colaborador).exclude(motivo='Férias').values_list('data', flat=True).order_by('-data')
	data_ultimo_ponto = pontos_funcionario.first() if pontos_funcionario else datetime.today()
	data_primeiro_ponto = pontos_funcionario.last() if pontos_funcionario else (datetime.today() - timedelta(days=29))

	filtros = {'inicio': None, 'final': None, 'funcionarios': None}
	filtros['final'] = request.GET.get('data_final', data_ultimo_ponto.strftime('%Y-%m-%d'))
	filtros['inicio'] = request.GET.get('data_inicial', data_primeiro_ponto.strftime('%Y-%m-%d'))

	solicitacoes_ajuste = SolicitacaoPonto.objects.filter(funcionario=colaborador).values('data', 'motivo', 'status').annotate(inicio=Min('hora'), final=Max('hora')).values('data', 'motivo', 'status', 'inicio', 'final')
	solicitacoes_abono = SolicitacaoAbono.objects.filter(funcionario=colaborador)
	solicitacoes = [{'data': i['data'], 'motivo': i['motivo'], 'status': i['status'], 'categoria': 'Ajuste', 'inicio': datetime.combine(i['data'], i['inicio']), 'final': datetime.combine(i['data'], i['final'])} for i in solicitacoes_ajuste]
	solicitacoes.extend([{'data': i.inicio.date, 'motivo': i.motivo, 'status': i.status, 'categoria': i.get_tipo, 'inicio': i.inicio, 'final': i.final } for i in solicitacoes_abono])

	pontos, scores = pontos_por_dia(datetime.strptime(filtros['inicio'], '%Y-%m-%d'), datetime.strptime(filtros['final'], '%Y-%m-%d'), funcionarios.filter(pk=colaborador.pk))
	graph, nro_colunas = {'plot': False, 'notas': list(), 'total': timedelta(), 'saldo': timedelta(), 'banco': timedelta()}, 0
	if pontos and scores:
		data_ultimo_registro = max(pontos.keys(), key=lambda x: x)
		
		graph['plot'] = True
		graph['notas'] = scores.get(colaborador.id)
		graph['banco'] = pontos.get(data_ultimo_registro).get(colaborador.id).get('banco')

		for _, funcs in pontos.items():
			for func, dados in funcs.items():
				graph['total'] += dados['total']
				graph['saldo'] += dados['saldo']

				if len(dados['pontos']) > nro_colunas:
					nro_colunas = len(dados['pontos'])

	context.update({
		'colaborador': colaborador,
		'jornada': jornada,
		'filtros': filtros,
		'pontos': pontos,
		'graph': graph,
		'nro_colunas': range(nro_colunas),
		'solicitacoes': solicitacoes
	})

	return render(request, 'pages/ponto-funcionario.html', context)


# Modal
@login_required(login_url='entrar')
def EditarPontoView(request, data, func):
	if not request.method == 'POST':
		messages.warning(request, 'Método não permitido!')
		return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))

	funcionario = Funcionario.objects.get(pk=func)
	autor = Funcionario.objects.get(usuario=request.user)
	data = datetime.strptime(data, '%Y-%m-%d').date()
	novos_pontos = request.POST.getlist('hora')
	motivo = request.POST.get('motivo')

	if not_none_not_empty(funcionario, data, novos_pontos):
		try:
			if request.user.get_access == 'admin':
				with transaction.atomic():
					Ponto.objects.filter(funcionario=funcionario, data=data).delete()
					for hora in novos_pontos:
						novo_ponto = Ponto.objects.create(funcionario=funcionario, hora=hora, data=data, autor_modificacao=autor)

						create_log(
							object_model=Ponto,
							object_id=novo_ponto.id,
							user=request.user,
							message='Ponto ajustado',
							action=1
						)

				messages.success(request, 'Ponto alterado!')

			else:
				if SolicitacaoPonto.objects.filter(data=data, funcionario=funcionario, status=False).exists():
					messages.error(request, 'Já foi aberta uma solicitação para este dia. Exclua ou edite a solicitação pendente!')
					return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))
				
				for hora in novos_pontos:
					solicitacao = SolicitacaoPonto.objects.create(
						funcionario=funcionario,
						aprovador=funcionario.gerente or ADMIN_USER,
						data=data,
						hora=hora,
						motivo=motivo,
					)

					create_log(
						object_model=SolicitacaoPonto,
						object_id=solicitacao.id,
						user=request.user,
						message='Solicitacao de ponto criada',
						action=1
					)
				
				notify.send(
					sender=funcionario.usuario,
					recipient=funcionario.gerente.usuario if funcionario.gerente else ADMIN_USER.usuario,
					verb='Solicitação de ponto recebida',
				)

				messages.success(request, 'Solicitação enviada!')

		except Exception as e:
			messages.error(request, e)

	else:
		messages.error(request, 'Preencha todos os campos obrigatórios!')

	return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))


# Modal
@login_required(login_url='entrar')
def SolicitarAbonoView(request):
	if not request.method == 'POST':
		messages.warning(request, 'Método não permitido!')
		return redirect('pontos')

	funcionario = Funcionario.objects.get(pk=int(request.POST.get('colaborador'))) if not_none_not_empty(request.POST.get('colaborador')) else Funcionario.objects.get(usuario=request.user)

	categoria = request.POST.get('categoria')
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

	if not_none_not_empty(categoria, tipo, motivo):		
		try:
			solicitacao = SolicitacaoAbono(
				funcionario=funcionario,
				tipo=tipo,
				categoria=categoria,
				motivo=motivo,
				documento=documento,
				caminho=f'{nome}.pdf' if nome else None,
			)

			if categoria == 'P':
				solicitacao.inicio = make_aware(datetime.strptime(inicio, '%Y-%m-%dT%H:%M'))
				solicitacao.final = make_aware(datetime.strptime(final, '%Y-%m-%dT%H:%M'))

				if solicitacao.inicio > solicitacao.final:
					messages.error(request, 'A data inicial não pode ser maior que a data final!')
					return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))
			else:
				solicitacao.inicio = make_aware(datetime.strptime(request.POST.get('data'), '%Y-%m-%d'))
				solicitacao.final = None

			solicitacao.aprovador = funcionario.gerente or ADMIN_USER
			solicitacao.save()
			
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

	return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))


# Modal
@login_required(login_url='entrar')
def AdicionarFeriadoView(request):
	if not request.method == 'POST':
		messages.warning(request, 'Método não permitido!')
		return redirect('pontos')

	try:
		titulo = request.POST.get('titulo')
		data_feriado = request.POST.get('data')
		regiao = request.POST.get('regiao')
		estado = request.POST.get('estado')
		cidade = request.POST.get('cidade')

		if not_none_not_empty(titulo, data_feriado):
			feriado = Feriados.objects.create(
				titulo=titulo,
				data=data_feriado,
				regiao=regiao,
				estado=Estado.objects.get(pk=int(estado)) if estado else None,
				cidade=Cidade.objects.get(pk=int(cidade)) if cidade else None
			)

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

	return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))


# Modal
@login_required(login_url='entrar')
def AdicionarSaldoView(request):
	if not request.method == 'POST':
		messages.warning(request, 'Método não permitido!')
		return redirect('pontos')

	try:
		data = datetime.strptime(request.POST.get('data_saldo'), '%Y-%m-%d').date() if request.POST.get('data_saldo') else None
		funcionario = Funcionario.objects.get(pk=int(request.POST.get('funcionario_saldo')))
		intervalo = request.POST.get('total_saldo').strip().split(':') # 00:00:00 ou -00:00:00
		adicionar_desconto = request.POST.get('folha') == 'on'
		saldo_banco = request.POST.get('banco') == 'on'

		if not data:
			messages.warning(request, 'Preencha todos os campos obrigatórios!')
			return redirect('pontos')
		
		if adicionar_desconto and saldo_banco:
			messages.warning(request, 'Você deve selecionar apenas 1 opção: "Desconto em Folha da Pagamento" ou "Saldo em Banco"!')
			return redirect('pontos')

		with transaction.atomic():
			if not Ponto.objects.filter(funcionario=funcionario, data=data).exists():
				Ponto(
					funcionario=funcionario,
					data=data,
					hora=time(),
					autor_modificacao=Funcionario.objects.get(usuario=request.user)
				).save()

			saldo = timedelta(hours=abs(int(intervalo[0])), minutes=int(intervalo[1]), seconds=int(intervalo[2]))

			if '-' in intervalo[0]:
				saldo *= -1

			if adicionar_desconto:
				for i in Ponto.objects.filter(funcionario=funcionario, data=data):
					i.motivo = f'Desconto de 20% em Folha de Pagamento. Adicionado saldo de {intervalo[0]}h{intervalo[1]}min.'
					i.save()
				
				if data.weekday() in [5, 6]:
					saldo = saldo / 2
				else:
					saldo = saldo / 1.5

			if saldo_banco:
				if data.weekday() in [5, 6]:
					saldo = saldo / 2
				else:
					saldo = saldo / 1.5

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

	except Exception as e:
		messages.error(request, e)

	return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))


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

	return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))


# CMD - CURL
@csrf_exempt
def RegistrarPontoExternoView(request):
	if request.method != 'POST':
		return JsonResponse({'status': 'error', 'message': 'Método não permitido'}, status=405)

	try:
		funcionario = Funcionario.objects.get(matricula=request.GET.get('matricula'))

		conf_permissao = Variavel.objects.get(chave='REGISTRO_EXTERNO').valor
		conf_matriculas = Variavel.objects.get(chave='MATRICULAS_EXTERNAS').valor

		permitir = conf_permissao == 'True'
		matriculas = [i.strip() for i in conf_matriculas.split(',')]

		body = request.body.decode('utf-8-sig')
		response = json.loads(body)

		if permitir and funcionario.matricula in matriculas:
			registros_ponto = list()

			if not isinstance(response, list):
				registros_ponto.append(response)
			else:
				registros_ponto = response

			for registro in registros_ponto:
				ponto = Ponto.objects.create(
					funcionario=funcionario,
					data=datetime.strptime(registro.get('data'), '%d/%m/%Y'),
					hora=registro.get('hora'),
					motivo='Importação de registro externo',
					autor_modificacao=funcionario
				)

				create_log(
					object_model=Ponto,
					object_id=ponto.id,
					user=funcionario.usuario,
					message='Ponto externo cadastrado',
					action=1
				)
			
			return JsonResponse({'status': 'success', 'message': f'Foram salvos {len(registros_ponto)} registro(s).'})
		
		else:
			return JsonResponse({'status': 'error', 'message': 'Sua matrícula não está liberada para registros externos. Fale com o setor de Recursos Humanos.'}, status=400)

	except Exception as e:
		return JsonResponse({'status': 'error', 'message': str(e)}, status=400)
