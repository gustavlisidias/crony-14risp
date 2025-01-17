import json
import re
import os

from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpResponseRedirect
from django.shortcuts import redirect, render
from django.utils.http import url_has_allowed_host_and_scheme

from pathlib import Path

from agenda.models import TipoAtividade
from configuracoes.models import Jornada, Usuario, Variavel, Contrato
from funcionarios.models import Cargo, Funcionario, Setor, TipoDocumento
from notifications.models import Notification
from web.utils import not_none_not_empty


# Page
def RegistrationView(request):
	if request.user.is_authenticated:
		return redirect('inicio')

	if request.method == 'POST':
		first_name = request.POST.get('first_name')
		last_name = request.POST.get('last_name')
		email = request.POST.get('email')
		password1 = request.POST.get('password1')
		password2 = request.POST.get('password2')

		if not_none_not_empty(first_name, last_name, email, password1, password2):
			if password1 != password2:
				messages.error(request, 'As senhas fornecidas não são compatíveis')
				return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))

			full_name = f'{first_name} {last_name}'
			username = f'{full_name.split()[0].lower()}.{full_name.split()[-1].lower()}'
			Usuario.objects.create_user(
				username=username,
				email=email,
				password=password1,
				first_name=first_name,
				last_name=last_name,
			)

			user = authenticate(request, username=username, password=password1)
			if user:
				login(request, user)
				return redirect('inicio')

	return render(request, 'autenticacao/registrar.html')


# Page
def LoginView(request):
	if request.user.is_authenticated:
		return redirect('inicio')
	
	if request.method == 'POST':
		username = request.POST.get('username')
		password = request.POST.get('password')

		user = authenticate(request, username=username, password=password)
		if user is not None:
			login(request, user)

			next_url = request.GET.get('next', None)

			if next_url is None:
				return redirect('inicio')
			elif not url_has_allowed_host_and_scheme(url=next_url, allowed_hosts={request.get_host()}, require_https=request.is_secure()):
				return redirect('inicio')
			else:
				return redirect(next_url)
			
		else:
			if Usuario.objects.filter(username=username).exists():
				messages.error(request, 'Senha incorreta. Por favor, tente novamente.')
			else:
				messages.error(request, 'Usuário não encontrado.')
			return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))

	return render(request, 'autenticacao/entrar.html')


# Action
def LogoutView(request):
	logout(request)
	return redirect('entrar')


# Page
@login_required(login_url='entrar')
def ConfiguracoesView(request):
	funcionario = Funcionario.objects.get(usuario=request.user)
	notificacoes = Notification.objects.filter(recipient=request.user, unread=True)

	variaveis = Variavel.objects.all()
	setores = Setor.objects.all()
	cargos = Cargo.objects.all()
	tipos_documento = TipoDocumento.objects.all().order_by('-codigo')
	tipos_atividade = TipoAtividade.objects.all().order_by('-data_cadastro')
	tipos_contrato = [{'key': i[0], 'value': i[1]} for i in Contrato.Tipo.choices]

	jornadas = {}
	for item in Jornada.objects.all().order_by('contrato__id', 'dia', 'ordem'):
		if item.contrato not in jornadas:
			jornadas[item.contrato] = {}

		if item.dia not in jornadas[item.contrato]:
			jornadas[item.contrato][item.dia] = []

		jornadas[item.contrato][item.dia].append({'tipo': item.get_tipo_display(), 'hora': item.hora})

	if request.method == 'POST':
		# Formulário para alterar/salvar caminhos das pastas, email, cnpj, nome da empresa e inscrição estadual
		nome_empresa = request.POST.get('nome_empresa')
		cnpj = request.POST.get('cnpj')
		insc_estadual = request.POST.get('insc_estadual')
		email = request.POST.get('email')
		caminho_documentos = request.POST.get('caminho_documentos')
		caminho_funcionarios = request.POST.get('caminho_funcionarios')

		if not_none_not_empty(caminho_documentos, caminho_funcionarios):
			Variavel.objects.update_or_create(chave='NOME_EMPRESA', defaults={'valor': nome_empresa})
			Variavel.objects.update_or_create(chave='CNPJ', defaults={'valor': cnpj})
			Variavel.objects.update_or_create(chave='INSC_ESTADUAL', defaults={'valor': insc_estadual})
			Variavel.objects.update_or_create(chave='EMAIL', defaults={'valor': email})
			Variavel.objects.update_or_create(chave='PATH_DOCS', defaults={'valor': caminho_documentos})
			Variavel.objects.update_or_create(chave='PATH_DOCS_EMP', defaults={'valor': caminho_funcionarios})

			messages.success(request, 'Dados salvos com sucesso!')
			return redirect('configuracoes')

		# Formulário para alterar/salvar Setores, Cargos, Tipos de Atividades e Tipos de Documentos
		novos_setores = request.POST.getlist('setor')
		novos_cargos = request.POST.getlist('cargo')
		novos_tipos = request.POST.getlist('tipo')
		novas_cores = request.POST.getlist('cor')
		novos_documentos = request.POST.getlist('documento')
		novos_codigos = request.POST.getlist('codigo')

		if not_none_not_empty(novos_setores, novos_cargos, novos_tipos, novas_cores, novos_documentos):
			try:
				with transaction.atomic():
					setores_cadastrados = list(Setor.objects.values_list('setor', flat=True))
					for setor in novos_setores:
						if setor not in setores_cadastrados:
							Setor(setor=setor).save()

					for setor in setores_cadastrados:
						if setor not in novos_setores:
							Setor.objects.filter(setor=setor).delete()

					###########################################################################

					cargos_cadastrados = list(Cargo.objects.values_list('cargo', flat=True))
					for cargo in novos_cargos:
						if cargo not in cargos_cadastrados:
							Cargo(cargo=cargo).save()

					for cargo in cargos_cadastrados:
						if cargo not in novos_cargos:
							Cargo.objects.filter(cargo=cargo).delete()

					###########################################################################

					# Lista com as atividades enviadas pelo cliente
					tipos_cadastrados = list(TipoAtividade.objects.values_list('tipo', flat=True))

					# Para cada nova atividade, se não foi cadastrada, crio na tabela TipoAtividade
					for index, tipo in enumerate(novos_tipos):
						if tipo not in tipos_cadastrados:
							TipoAtividade(tipo=tipo, cor=novas_cores[index]).save()

					# Para cada atividade cadastrada, se não está listado nas atividades enviados, removo
					for tipo in tipos_cadastrados:
						if tipo not in novos_tipos:
							TipoAtividade.objects.filter(tipo=tipo).delete()

					###########################################################################

					# Lista com os documentos enviados pelo cliente
					docs_cadastrados = list(TipoDocumento.objects.values_list('tipo', flat=True))

					# Para cada novo documento, se não foi cadastrado, crio na tabela TipoDocumento
					for index, documento in enumerate(novos_documentos):
						if documento not in docs_cadastrados:
							TipoDocumento(tipo=documento, codigo=novos_codigos[index]).save()

					# Para cada documento cadastrado, se não está listado nos documentos enviados, removo
					for documento in docs_cadastrados:
						if documento not in novos_documentos:
							TipoDocumento.objects.filter(tipo=documento).delete()

					# Criar pasta no servidor
					for i in TipoDocumento.objects.all():
						pasta = Path(Variavel.objects.get(chave='PATH_DOCS').valor, f'{i.codigo} - {i.tipo}')
						os.makedirs(pasta, exist_ok=True)

					messages.success(request, 'Dados salvos com sucesso!')

			except Exception as e:
				messages.error(request, f'Dados não foram salvos: {e}!')

			return redirect('configuracoes')

		# Formulário para alterar/salvar Contratos e Jornadas de Trabalho
		novas_jornadas = request.POST.get('jornadas')

		if not_none_not_empty(novas_jornadas):
			for contrato in Contrato.objects.all().order_by('id'):
				name = f'jornada-{contrato.id}'
				if request.POST.get(name):
					try:
						with transaction.atomic():
							for dia, horarios in json.loads(request.POST.get(name)).items():
								Jornada.objects.filter(contrato=contrato, dia=dia).delete()
								for index, (tipo, hora) in enumerate(horarios.items()):
									Jornada.objects.create(
										contrato=contrato,
										dia=dia,
										hora=hora,
										tipo=tipo[0].upper(),
										ordem=(index + 1)
									)
					except Exception as e:
						messages.error(request, f'Jornadas não foram salvas: {e}!')
				else:
					Jornada.objects.filter(contrato=contrato).delete()
					contrato.delete()

			messages.success(request, 'Jornadas foram salvas com sucesso!')
			return redirect('configuracoes')

		# Formulário para alterar/salvar configurações de registro de ponto externo
		matriculas = request.POST.get('matriculas_externo')
		registrar = request.POST.get('registrar_externo', 'False')
		if not_none_not_empty(matriculas):
			try:
				Variavel.objects.update_or_create(chave='REGISTRO_EXTERNO', defaults={'valor': registrar})
				Variavel.objects.update_or_create(chave='MATRICULAS_EXTERNAS', defaults={'valor': matriculas})

				messages.success(request, 'Configurações de registro de ponto externo salvas com sucesso!')
				return redirect('configuracoes')
			
			except Exception as e:
				messages.error(request, f'Configurações de registro de ponto externo não foram salvas! {e}')
				return redirect('configuracoes')

	context = {
		'funcionario': funcionario,
		'notificacoes': notificacoes,
		'variaveis': variaveis,
		'jornadas': jornadas,
		'setores': setores,
		'cargos': cargos,
		'tipos_documento': tipos_documento,
		'tipos_atividade': tipos_atividade,
		'tipos_contrato': tipos_contrato
	}

	return render(request, 'pages/configuracoes.html', context)


# Modal
@login_required(login_url='entrar')
def AdicionarJornadaView(request):
	if not request.method == 'POST':
		messages.warning(request, 'Método não permitido!')
		return redirect('configuracoes')
	
	try:
		contrato = Contrato.objects.create(titulo=request.POST.get('titulo'), descricao=request.POST.get('descricao'), tipo=request.POST.get('tipo'))
		horas = re.findall(r'\d{2}:\d{2}', request.POST.get('descricao'))

		if len(horas) % 2 != 0:
			messages.error(request, 'Jornada não pode ser criada pois o número de entradas e saídas são diferentes!')
		else:
			for dia in range(1, 8):
				for index, hora in enumerate(horas):
					tipo = 'E' if index % 2 == 0 else 'S'
					hora = '00:00' if dia in [1, 7] else hora
					Jornada.objects.create(
						contrato=contrato,
						tipo=tipo,
						dia=dia,
						hora=hora,
						ordem=(index + 1)
					)
			messages.success(request, 'Jornada criada com sucesso!')

	except Exception as e:
		messages.error(request, f'Jornada não foi criada: {e}!')

	return redirect('configuracoes')
