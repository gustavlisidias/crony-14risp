import logging
import json
import os
import pytz

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import F
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import redirect
from django.utils import timezone
from django.utils.timezone import now

from datetime import datetime, timedelta, time

from configuracoes.models import Variavel, Contrato
from funcionarios.models import Documento, Funcionario, TipoDocumento, JornadaFuncionario
from ponto.models import Ponto, SolicitacaoAbono, SolicitacaoPonto, Saldos
from ponto.report import gerar_pdf_ponto
from ponto.utils import filtrar_abonos, total_saldo
from notifications.signals import notify
from settings.settings import BASE_DIR
from web.report import gerar_relatorio_csv
from web.utils import not_none_not_empty, create_log


@login_required(login_url='entrar')
def RegistrarPontoView(request):
	if not request.method == 'POST':
		messages.warning(request, 'Método não permitido!')
		return JsonResponse({'message': 'forbidden'}, status=404)

	log_file = 'log_pontos.log'
	log_path = os.path.join(BASE_DIR, f'logs/{log_file}')
	logging.basicConfig(filename=log_path, encoding='utf-8', level=logging.INFO, force=True)
	
	try:
		registro_externo = Variavel.objects.filter(chave='REGISTRO_EXTERNO').first()
		host_externo = Variavel.objects.filter(chave='HOST_EXTERNO').first()
		matriculas_externo = Variavel.objects.filter(chave='MATRICULAS_EXTERNAS').first()
		funcionario = Funcionario.objects.get(usuario=request.user)

		permitir = registro_externo.valor == 'True' if registro_externo else False
		hosts = [i.strip() for i in host_externo.valor.split(',')] if host_externo else []
		matriculas = [i.strip() for i in matriculas_externo.valor.split(',')] if host_externo else []

		logging.info(f'permitir: {permitir}, host: {str(request.get_host())}, hosts_liberados: {hosts}, matriculas_liberadas: {matriculas}, funcionario_matricula: {funcionario.matricula}')
		
		if permitir and str(request.get_host().split(':')[0]) in hosts:
			if funcionario.matricula not in matriculas:
				messages.error(request, 'Ponto não registrado! Registro externo ou matrícula não configurada!')
				return JsonResponse({'message': 'error'}, status=400)
			
		if not permitir and str(request.get_host().split(':')[0]) in hosts:
			messages.error(request, 'Ponto não registrado! Registro externo não liberado!')
			return JsonResponse({'message': 'error'}, status=400)
		
		ponto = Ponto.objects.create(funcionario=funcionario, data=timezone.localdate(), hora=timezone.localtime())

		create_log(
			object_model=Ponto,
			object_id=ponto.id,
			user=funcionario.usuario,
			message='Ponto cadastrado',
			action=1
		)
		
		messages.success(request, 'Ponto registrado com sucesso!')
		return JsonResponse({'message': 'success'}, status=200)

	except Exception as e:
		messages.error(request, f'Ponto não registrado: {e}')
		return JsonResponse({'message': e}, status=400)


@login_required(login_url='entrar')
def ConsultarPontoView(request, data, func):
	if not request.method == 'GET':
		return JsonResponse({'message': 'forbidden'}, status=404)

	try:
		funcionario = Funcionario.objects.get(pk=func)
		ponto = list(Ponto.objects.filter(funcionario=funcionario, data=data).values('hora').order_by('hora'))
		return JsonResponse(ponto, safe=False, status=200)

	except Exception as e:
		return JsonResponse({'message': e}, status=400)
	

@login_required(login_url='entrar')
def ConsultarSolicitacaoView(request, solic, categoria):
	if not request.method == 'GET':
		return JsonResponse({'message': 'forbidden'}, status=404)

	try:
		if categoria.lower() != 'ajuste':
			solicitacao = list(SolicitacaoAbono.objects.filter(pk=solic).values_list(
				'id', 'funcionario__nome_completo', 'inicio', 'final', 'motivo'
			))
			return JsonResponse({'solicitacao': solicitacao, 'categoria': 'abono'}, safe=False, status=200)
		
		else:
			solicitacao = SolicitacaoPonto.objects.get(pk=solic)
			solicitacoes = list(SolicitacaoPonto.objects.filter(funcionario=solicitacao.funcionario, data=solicitacao.data, status=False).values_list(
				'id', 'funcionario__nome_completo', 'data', 'hora', 'motivo'
			))
			pontos = list(Ponto.objects.filter(funcionario=solicitacao.funcionario, data=solicitacao.data).values_list('hora', flat=True).order_by('data', 'hora'))
			return JsonResponse({'solicitacao': solicitacoes, 'categoria': 'ajuste', 'pontos': pontos}, safe=False, status=200)

	except Exception as e:
		return JsonResponse({'message': e}, status=400)


@login_required(login_url='entrar')
def EditarPontoView(request, data, func):
	if not request.method == 'POST':
		messages.warning(request, 'Método não permitido!')
		return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))

	funcionario = Funcionario.objects.get(pk=func)
	data = datetime.strptime(data, '%Y-%m-%d').date()
	novos_pontos = request.POST.getlist('hora')
	motivo = request.POST.get('motivo')
	gerente = Funcionario.objects.get(usuario=request.user).gerente
	admin = Funcionario.objects.filter(data_demissao=None, matricula__in=[i.strip() for i in Variavel.objects.get(chave='RESP_USERS').valor.split(',')]).first()

	if not_none_not_empty(funcionario, data, novos_pontos):
		try:
			if request.user.get_access == 'admin':
				with transaction.atomic():
					Ponto.objects.filter(funcionario=funcionario, data=data).delete()
					for hora in novos_pontos:
						novo_ponto = Ponto.objects.create(funcionario=funcionario, hora=hora, data=data)

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
						aprovador=gerente or admin,
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

				if gerente:
					notify.send(
						sender=funcionario.usuario,
						recipient=gerente.usuario,
						verb='Solicitação de ponto recebida',
					)

				else:
					notify.send(
						sender=funcionario.usuario,
						recipient=admin.usuario,
						verb='Solicitação de ponto recebida',
					)

				messages.success(request, 'Solicitação enviada!')

		except Exception as e:
			messages.error(request, e)

	else:
		messages.error(request, 'Preencha todos os campos obrigatórios!')

	return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))


@login_required(login_url='entrar')
def AprovarSolicitacaoView(request, solic, categoria):
	if not request.method == 'POST':
		messages.warning(request, 'Método não permitido!')
		return JsonResponse({'message': 'forbidden'}, status=404)

	try:		
		if categoria.lower() == 'ajuste':
			modelo = SolicitacaoPonto
			message = 'Solicitação de Ajuste de Ponto aprovada'
			solicitacao = modelo.objects.get(pk=solic)

			if request.user.get_access != 'admin' and solicitacao.aprovador.usuario != request.user:
				messages.warning(request, 'Você não tem permissão para aprovar esta solicitação!')
				return JsonResponse({'message': 'Você não tem permissão para aprovar esta solicitação!'}, status=200)
			
			solicitacoes = SolicitacaoPonto.objects.filter(funcionario=solicitacao.funcionario, data=solicitacao.data, status=False)
			with transaction.atomic():
				Ponto.objects.filter(funcionario=solicitacao.funcionario, data=solicitacao.data).delete()

				for ponto in solicitacoes:
					Ponto(
						data=ponto.data, 
						hora=ponto.hora,
						funcionario=ponto.funcionario,
						alterado=True,
						motivo=ponto.motivo
					).save()

					ponto.status = True
					ponto.save()

				solicitacao.aprovador = Funcionario.objects.get(usuario=request.user)
				solicitacao.status = True
				solicitacao.save()

		else:
			modelo = SolicitacaoAbono
			message = 'Solicitação de Abono aprovada'
			solicitacao = modelo.objects.get(pk=solic)

			if request.user.get_access != 'admin' and solicitacao.aprovador.usuario != request.user:
				messages.warning(request, 'Você não tem permissão para aprovar esta solicitação!')
				return JsonResponse({'message': 'Você não tem permissão para aprovar esta solicitação!'}, status=200)

			jornada_para_abonar = filtrar_abonos(solicitacao.inicio, solicitacao.final, solicitacao.funcionario)
			for dia, pontos in jornada_para_abonar.items():

				if not Ponto.objects.filter(funcionario=solicitacao.funcionario, data=dia).exists():
					Ponto(
						funcionario=solicitacao.funcionario,
						data=dia,
						hora=time(0, 0),
						motivo=solicitacao.motivo,
						alterado=True,
						encerrado=True
					).save()
				
				else:
					Ponto.objects.filter(funcionario=solicitacao.funcionario, data=dia).update(motivo=solicitacao.motivo)

				saldo = total_saldo(pontos)

				if saldo != timedelta(0):
					if solicitacao.tipo == SolicitacaoAbono.Tipo.FALTA:
						saldo *= -1

					Saldos(
						funcionario=solicitacao.funcionario,
						saldo=saldo,
						data=dia
					).save()

			if solicitacao.caminho:
				tipo = TipoDocumento.objects.get(tipo=solicitacao.get_tipo_display())
				Documento(
					funcionario=solicitacao.funcionario,
					tipo=tipo,
					documento=solicitacao.documento,
					caminho=solicitacao.caminho,
					data_documento=timezone.localdate(),
				).save()

			solicitacao.aprovador = Funcionario.objects.get(usuario=request.user)
			solicitacao.status = True
			solicitacao.save()
		
		create_log(
			object_model=modelo,
			object_id=solicitacao.id,
			user=request.user,
			message=message,
			action=2
		)

		if request.user != solicitacao.funcionario.usuario:
			notify.send(
				sender=request.user,
				recipient=solicitacao.funcionario.usuario,
				verb=message,
			)

		messages.success(request, 'Solicitação aprovada com sucesso!')
		return JsonResponse({'message': 'Solicitação aprovada com sucesso!'}, status=200)

	except Exception as e:
		messages.error(request, e)
		return JsonResponse({'message': e}, status=400)
	

@login_required(login_url='entrar')
def ReprovarSolicitacaoView(request, solic, categoria):
	if not request.method == 'POST':
		messages.warning(request, 'Método não permitido!')
		return JsonResponse({'message': 'forbidden'}, status=404)

	try:
		if categoria.lower() == 'ajuste':
			solicitacao = SolicitacaoPonto.objects.get(pk=solic)
			solicitacoes = SolicitacaoPonto.objects.filter(funcionario=solicitacao.funcionario, data=solicitacao.data)
			modelo = SolicitacaoPonto
			message = 'Solicitação de Ajuste de Ponto excluída'

		else:
			solicitacao = SolicitacaoAbono.objects.get(pk=solic)
			solicitacoes = SolicitacaoAbono.objects.filter(funcionario=solicitacao.funcionario, inicio=solicitacao.inicio, final=solicitacao.final)
			modelo = SolicitacaoAbono
			message = 'Solicitação de Abono excluída'

		if solicitacao.funcionario.usuario != request.user and request.user.get_access == 'common':
			messages.warning(request, 'Você não tem permissão para remover esta solicitação!')
			return JsonResponse({'message': 'Você não tem permissão para remover esta solicitação!'}, status=200)

		create_log(
			object_model=modelo,
			object_id=solicitacao.id,
			user=request.user,
			message=message,
			action=3
		)

		if request.user != solicitacao.funcionario.usuario:
			notify.send(
				sender=request.user,
				recipient=solicitacao.funcionario.usuario,
				verb=message,
				description=request.POST.get('motivo')
			)
		
		solicitacoes.delete()
		messages.success(request, 'Solicitação removida com sucesso!')
		return JsonResponse({'message': 'Solicitação removida com sucesso!'}, status=200)

		
	except Exception as e:
		messages.error(request, e)
		return JsonResponse({'message': e}, status=400)
	

@login_required(login_url='entrar')
def AprovarSolicitacoesView(request):
	if not request.method == 'POST':
		messages.warning(request, 'Método não permitido!')
		return JsonResponse({'message': 'forbidden'}, status=404)
	
	if not json.loads(request.body) and not request.POST:
		messages.warning(request, 'Nenhuma solicitação foi alterada pois não foi enviado nenhum dado!')
		return JsonResponse({'message': 'Solicitações aprovadas com sucesso!'}, status=200)

	try:
		data = json.loads(request.body)
		for ident in data:
			categoria, solic = ident['value'].split('-')

			if categoria.lower() == 'ajuste':
				modelo = SolicitacaoPonto
				message = 'Solicitação de Ajuste de Ponto aprovada'
				solicitacao = modelo.objects.get(pk=solic)

				if request.user.get_access != 'admin' and solicitacao.aprovador.usuario != request.user:
					messages.warning(request, 'Você não tem permissão para aprovar esta solicitação!')
					return JsonResponse({'message': 'Você não tem permissão para aprovar esta solicitação!'}, status=200)
				
				solicitacoes = SolicitacaoPonto.objects.filter(funcionario=solicitacao.funcionario, data=solicitacao.data, status=False)
				with transaction.atomic():
					Ponto.objects.filter(funcionario=solicitacao.funcionario, data=solicitacao.data).delete()

					for ponto in solicitacoes:
						Ponto(
							data=ponto.data, 
							hora=ponto.hora,
							funcionario=ponto.funcionario,
							alterado=True,
							motivo=ponto.motivo
						).save()

						ponto.status = True
						ponto.save()

					solicitacao.aprovador = Funcionario.objects.get(usuario=request.user)
					solicitacao.status = True
					solicitacao.save()

			else:
				modelo = SolicitacaoAbono
				message = 'Solicitação de Abono aprovada'
				solicitacao = modelo.objects.get(pk=solic)

				if request.user.get_access != 'admin' and solicitacao.aprovador.usuario != request.user:
					messages.warning(request, 'Você não tem permissão para aprovar esta solicitação!')
					return JsonResponse({'message': 'Você não tem permissão para aprovar esta solicitação!'}, status=200)

				jornada_para_abonar = filtrar_abonos(solicitacao.inicio, solicitacao.final, solicitacao.funcionario)
				for dia, pontos in jornada_para_abonar.items():

					if not Ponto.objects.filter(funcionario=solicitacao.funcionario, data=dia).exists():
						Ponto(
							funcionario=solicitacao.funcionario,
							data=dia,
							hora=time(0, 0),
							motivo=solicitacao.motivo,
							alterado=True,
							encerrado=True
						).save()
					
					else:
						Ponto.objects.filter(funcionario=solicitacao.funcionario, data=dia).update(motivo=solicitacao.motivo)

					saldo = total_saldo(pontos)

					if saldo != timedelta(0):
						if solicitacao.tipo == SolicitacaoAbono.Tipo.FALTA:
							saldo *= -1

						Saldos(
							funcionario=solicitacao.funcionario,
							saldo=saldo,
							data=dia
						).save()

				if solicitacao.caminho:
					tipo = TipoDocumento.objects.get(tipo=solicitacao.get_tipo_display())
					Documento(
						funcionario=solicitacao.funcionario,
						tipo=tipo,
						documento=solicitacao.documento,
						caminho=solicitacao.caminho,
						data_documento=timezone.localdate(),
					).save()

				solicitacao.aprovador = Funcionario.objects.get(usuario=request.user)
				solicitacao.status = True
				solicitacao.save()
			
			create_log(
				object_model=modelo,
				object_id=solicitacao.id,
				user=request.user,
				message=message,
				action=2
			)

			if request.user != solicitacao.funcionario.usuario:
				notify.send(
					sender=request.user,
					recipient=solicitacao.funcionario.usuario,
					verb=message,
				)

		messages.success(request, 'Solicitações aprovadas com sucesso!')
		return JsonResponse({'message': 'Solicitações aprovadas com sucesso!'}, status=200)

	except Exception as e:
		messages.error(request, e)
		return JsonResponse({'message': e}, status=400)
	

@login_required(login_url='entrar')
def ReprovarSolicitacoesView(request):
	if not request.method == 'POST':
		messages.warning(request, 'Método não permitido!')
		return JsonResponse({'message': 'forbidden'}, status=404)
	
	if not json.loads(request.body) and not request.POST:
		messages.warning(request, 'Nenhuma solicitação foi alterada pois não foi enviado nenhum dado!')
		return JsonResponse({'message': 'Solicitações aprovadas com sucesso!'}, status=200)
	
	try:
		data = json.loads(request.body)
		for ident in data:
			categoria, solic = ident['value'].split('-')

			if categoria.lower() == 'ajuste':
				solicitacao = SolicitacaoPonto.objects.get(pk=solic)
				solicitacoes = SolicitacaoPonto.objects.filter(funcionario=solicitacao.funcionario, data=solicitacao.data)
				modelo = SolicitacaoPonto
				message = 'Solicitação de Ajuste de Ponto excluída'

			else:
				solicitacao = SolicitacaoAbono.objects.get(pk=solic)
				solicitacoes = SolicitacaoAbono.objects.filter(funcionario=solicitacao.funcionario, inicio=solicitacao.inicio, final=solicitacao.final)
				modelo = SolicitacaoAbono
				message = 'Solicitação de Abono excluída'

			create_log(
				object_model=modelo,
				object_id=solicitacao.id,
				user=request.user,
				message=message,
				action=3
			)

			if request.user != solicitacao.funcionario.usuario:
				notify.send(
					sender=request.user,
					recipient=solicitacao.funcionario.usuario,
					verb=message,
					description='Reprovado'
				)
			
			solicitacoes.delete()

		messages.success(request, 'Solicitações removidas com sucesso!')
		return JsonResponse({'message': 'Solicitações removidas com sucesso!'}, status=200)

	except Exception as e:
		messages.error(request, e)
		return JsonResponse({'message': e}, status=400)


@login_required(login_url='entrar')
def RelatoriosPontoView(request):
	if not request.method == 'POST':
		messages.warning(request, 'Método não permitido!')
		return JsonResponse({'message': 'forbidden'}, status=404)
	
	contratos = Contrato.objects.filter(pk__in=[int(i) for i in request.POST.getlist('contrato')]) if not_none_not_empty(request.POST.get('contrato')) else Contrato.objects.all()
	
	jornadas_funcionarios = JornadaFuncionario.objects.filter(contrato__id__in=[i.id for i in contratos], final_vigencia=None).order_by(
		'funcionario__id', 'agrupador', 'dia', 'ordem'
	).values('funcionario__id').distinct()

	funcionarios = Funcionario.objects.filter(data_demissao=None, pk__in=[i['funcionario__id'] for i in jornadas_funcionarios]).order_by('nome_completo')

	if not_none_not_empty(request.POST.getlist('funcionarios')):
		funcionarios = funcionarios.filter(pk__in=[int(i) for i in request.POST.getlist('funcionarios')])
	
	if not funcionarios:
		messages.warning(request, 'Nenhum funcionário encontrado com este filtro!')
		return redirect('pontos')
	
	data_inicial = request.POST.get('relatorio_inicio') if not_none_not_empty(request.POST.get('relatorio_inicio')) else (now() - timedelta(days=30)).strftime('%Y-%m-%d')
	data_final = request.POST.get('relatorio_final') if not_none_not_empty(request.POST.get('relatorio_final')) else now().strftime('%Y-%m-%d')
	
	if request.POST.get('tipo') == '0':	
		response = gerar_pdf_ponto(request, funcionarios, data_inicial, data_final)
		return response if response else redirect('pontos')
			
	elif request.POST.get('tipo') == '1':
		filename = 'relatorio_abonos'
		colunas = ['Início', 'Final', 'Motivo', 'Status', 'Tipo', 'Funcionario', 'Aprovador']
		solicitacoes = SolicitacaoAbono.objects.filter(funcionario__in=funcionarios, inicio__date__range=[data_inicial, data_final]).annotate(
			tipo_display=F('tipo'), aprovador_nome=F('aprovador__nome_completo'), funcionario_nome=F('funcionario__nome_completo')
		).values('inicio', 'final', 'tipo_display', 'motivo', 'status', 'aprovador_nome', 'funcionario_nome')
		
		dataset = []
		for solicitacao in solicitacoes:
			solicitacao['tipo_display'] = dict(SolicitacaoAbono.Tipo.choices).get(solicitacao['tipo_display'])
			dataset.append(list(solicitacao.values()))

		return gerar_relatorio_csv(colunas, dataset, filename)
		
	elif request.POST.get('tipo') == '2':
		filename = 'relatorio_ajustes'
		colunas = ['Data', 'Hora', 'Motivo', 'Status', 'Funcionario', 'Aprovador']
		dataset = list(SolicitacaoPonto.objects.filter(
			funcionario__in=funcionarios, data__range=[data_inicial, data_final]
		).values_list('data', 'hora', 'motivo', 'status', 'funcionario__nome_completo', 'aprovador__nome_completo').distinct())

		return gerar_relatorio_csv(colunas, dataset, filename)
	
	elif request.POST.get('tipo') == '3':
		filename = 'relatorio_alteracoes'
		colunas = ['Funcionario', 'Data', 'Hora', 'Data Cadastro']

		pontos_filtrados = list(Ponto.objects.filter(
			funcionario__in=funcionarios, data_cadastro__date__range=[data_inicial, data_final]
		).values_list('funcionario__nome_completo', 'data', 'hora', 'data_cadastro'))

		dataset = []
		for i in pontos_filtrados:
			data = (i[0], i[1], i[2], i[3].astimezone(pytz.timezone('America/Sao_Paulo')))
			dataset.append(data)

		return gerar_relatorio_csv(colunas, dataset, filename)

	else:
		return redirect('pontos')
