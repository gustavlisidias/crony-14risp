import io
import os
import re
import pytz

from django.contrib import messages
from django.contrib.auth.hashers import make_password
from django.db import transaction
from django.db.utils import IntegrityError
from django.shortcuts import redirect

from datetime import date, datetime
from pathlib import Path
from PIL import Image

from cities_light.models import Region as Estado
from cities_light.models import SubRegion as Cidade
from configuracoes.models import Usuario, Jornada, Variavel, Contrato
from cursos.models import Curso, CursoFuncionario
from funcionarios.models import Funcionario, HistoricoFuncionario, JornadaFuncionario, Perfil, Score, Cargo, Setor
from ponto.models import Ponto
from web.models import Celebracao
from web.utils import not_none_not_empty, add_coins


def converter_documento(file):
	nome = '_'.join(file.name.split('.')[:-1])
	extensao = file.name.split('.')[-1]
	documento = file.read()

	if extensao.lower() not in ['jpg', 'jpeg', 'png', 'pdf']:
		return None, None

	elif extensao.lower() == 'pdf':
		return nome, documento

	else:
		img = Image.open(io.BytesIO(documento))
		pdf_io = io.BytesIO()
		img.save(pdf_io, 'PDF')
		return nome, pdf_io.getvalue()


def obter_arvore(caminho):
	dados = {'text': os.path.basename(caminho), 'path': caminho}
	dados['children'] = []

	try:
		for item in os.listdir(caminho):
			# verificar se o documento já está salvo no banco
			caminho_completo = os.path.join(caminho, item)
			if os.path.isdir(caminho_completo):
				dados['children'].append(obter_arvore(caminho_completo))
			else:
				dados['children'].append({'text': item, 'type': 'file', 'path': caminho_completo})

	except Exception as e:
		dados['children'].append({'text': f'Erro: {str(e)}'})

	return dados


def cadastro_funcionario(request, funcionario=None, editar=False):
	funcionarios = Funcionario.objects.filter(data_demissao=None).order_by('nome_completo')
	
	# Dados do Funcionario
	matricula = request.POST.get('matricula') # required
	nome_completo = request.POST.get('nome_completo') # required
	nome_social = request.POST.get('nome_social') if not_none_not_empty(request.POST.get('nome_social')) else None
	nome_mae = request.POST.get('nome_mae') if not_none_not_empty(request.POST.get('nome_mae')) else None
	nome_pai = request.POST.get('nome_pai') if not_none_not_empty(request.POST.get('nome_pai')) else None
	email = request.POST.get('email') # required
	email_sec = request.POST.get('email_sec') if not_none_not_empty(request.POST.get('email_sec')) else None
	contato = None
	contato_sec = None
	resp_contato_sec = request.POST.get('resp_contato_sec') if not_none_not_empty(request.POST.get('resp_contato_sec')) else None
	cpf = request.POST.get('cpf') # required
	rg = request.POST.get('rg') # required
	sexo = request.POST.get('sexo') # required
	estado_civil = request.POST.get('estado_civil') # required
	estado = Estado.objects.get(pk=request.POST.get('estado')) # required
	cidade = Cidade.objects.get(pk=request.POST.get('cidade')) # required
	rua = request.POST.get('rua') # required
	numero = request.POST.get('numero') # required
	complemento = request.POST.get('complemento') if not_none_not_empty(request.POST.get('complemento')) else None
	cep = request.POST.get('cep') # required
	setor = Setor.objects.get(pk=request.POST.get('setor')) # required
	cargo = Cargo.objects.get(pk=request.POST.get('cargo')) # required
	gerente = Funcionario.objects.get(pk=request.POST.get('gerente')) if not_none_not_empty(request.POST.get('gerente')) else None
	salario = 0
	data_expedicao = request.POST.get('data_expedicao') if not_none_not_empty(request.POST.get('data_expedicao')) else None
	data_nascimento = request.POST.get('data_nascimento') # required
	data_contratacao = request.POST.get('data_contratacao') # required
	data_demissao = request.POST.get('data_demissao') if not_none_not_empty(request.POST.get('data_demissao')) else None
	data_inicio_ferias = request.POST.get('data_inicio_ferias') if not_none_not_empty(request.POST.get('data_inicio_ferias')) else None
	conta_banco = request.POST.get('conta_banco') if not_none_not_empty(request.POST.get('conta_banco')) else None

	# Dados adicionais
	contrato = Contrato.objects.get(pk=int(request.POST.get('contrato'))) if not_none_not_empty(request.POST.get('contrato')) else None
	is_gerente = True if not_none_not_empty(request.POST.get('staff')) else False

	# Dados do Usuario do Funcionario
	if len(nome_completo.split()) > 1:
		first_name = ' '.join(nome_completo.split()[:-1])
		last_name = nome_completo.split()[-1]
		username = f'{nome_completo.split()[0].lower()}.{last_name.lower()}'
	else:
		first_name = nome_completo.lower()
		last_name = ' '
		username = first_name

	if not_none_not_empty(request.POST.get('salario')) and request.POST.get('salario') != 'R$ ':
		salario = float(re.sub(r'[^0-9]', '', request.POST.get('salario'))) / 100

	if not_none_not_empty(request.POST.get('contato')) and request.POST.get('contato') != '(__) _____-____':
		contato = request.POST.get('contato')

	if not_none_not_empty(request.POST.get('contato_sec')) and request.POST.get('contato_sec') != '(__) _____-____':
		contato_sec = request.POST.get('contato_sec')

	if not editar:
		try:
			if Usuario.objects.filter(username=username).exists():			
				username = matricula

			with transaction.atomic():
				usuario = Usuario.objects.create(
					username=username,
					first_name=first_name,
					last_name=last_name,
					email=email,
					password=make_password('Senha@123'),
					is_gerente=is_gerente,
					is_active=False if data_demissao else True
				)

				funcionario = Funcionario.objects.create(
					usuario=usuario,
					matricula=matricula,
					nome_completo=nome_completo,
					nome_social=nome_social,
					nome_mae=nome_mae,
					nome_pai=nome_pai,
					email=email,
					email_sec=email_sec,
					contato=contato,
					contato_sec=contato_sec,
					resp_contato_sec=resp_contato_sec,
					cpf=cpf,
					rg=rg,
					sexo=sexo,
					estado_civil=estado_civil,
					estado=estado,
					cidade=cidade,
					rua=rua,
					numero=numero,
					complemento=complemento,
					cep=cep,
					setor=setor,
					cargo=cargo,
					gerente=gerente,
					salario=salario,
					data_expedicao=data_expedicao,
					data_nascimento=data_nascimento,
					data_contratacao=data_contratacao,
					data_demissao=data_demissao,
					data_inicio_ferias=data_inicio_ferias,
					conta_banco=conta_banco
				)

				# Gerando jornada de trabalho do funcionário com base no Contrato selecionado
				jornadas = Jornada.objects.filter(contrato=contrato).order_by('contrato__id', 'dia', 'ordem')
				for jornada in jornadas:
					JornadaFuncionario.objects.create(
						funcionario=funcionario,
						contrato=jornada.contrato,
						tipo=jornada.tipo,
						dia=jornada.dia,
						hora=jornada.hora,
						ordem=jornada.ordem
					)
				
				# Criando Perfil do Funcionario
				Perfil.objects.create(funcionario=funcionario)

				# Criar Score inicial do Funcionario
				Score.objects.create(funcionario=funcionario)

				# Gravo as informações no Histórico de Funcionários
				HistoricoFuncionario(
					funcionario=funcionario,
					setor=setor,
					cargo=cargo,
					contrato=contrato,
					salario=salario
				).save()

				# Atribuir cursos ao novo Funcionário
				cursos = Curso.objects.filter(contrato=jornadas.first().contrato)
				for curso in cursos:
					CursoFuncionario(funcionario=funcionario, curso=curso).save()

				# Criar celebração de chegada do novo Funcionario
				celebracao = Celebracao.objects.create(
					titulo='Bem-vindo',
					texto=f'Seja muito bem vindo(a) {funcionario.nome_completo}! Estamos felizes com a sua chegada!',
					celebrante=funcionario,
					data_celebracao=date.today()
				)
				celebracao.funcionario.set([i.id for i in funcionarios])
				celebracao.save()

				# Criar pasta no servidor
				pasta = Path(Variavel.objects.get(chave='PATH_DOCS_EMP').valor, f'{matricula} - {nome_completo.title()}')
				os.makedirs(pasta, exist_ok=True)
				
			return messages.success(request, 'Funcionário(a) criado(a) com sucesso!')
					
		except IntegrityError as e:
			return messages.error(request, f'Funcionário(a) não foi criado(a)! O campo Matrícula deve ser único. {e}')

		except Exception as e:
			return messages.error(request, f'Funcionário(a) não foi criado(a): {e}!')

	else:
		try:
			if Usuario.objects.exclude(pk=funcionario.usuario.id).filter(username=username).exists():
				username = matricula

			with transaction.atomic():
				if cargo and funcionario.cargo != cargo:
					add_coins(funcionario, 250)

				# Faço o fechamento dos pontos em aberto se data_demissao
				if data_demissao:
					pontos = Ponto.objects.filter(funcionario=funcionario, data_fechamento=None)
					if pontos:
						for ponto in pontos:
							ponto.encerrado = True
							ponto.data_fechamento = datetime.now().replace(tzinfo=pytz.utc)
							ponto.save()

				funcionario.usuario.username=username
				funcionario.usuario.first_name=first_name
				funcionario.usuario.last_name=last_name
				funcionario.usuario.email=email
				funcionario.usuario.is_gerente=is_gerente
				funcionario.usuario.is_active=False if data_demissao else True
				funcionario.usuario.save()
				
				funcionario.matricula=matricula
				funcionario.nome_completo=nome_completo
				funcionario.nome_social=nome_social
				funcionario.nome_mae=nome_mae
				funcionario.nome_pai=nome_pai
				funcionario.email=email
				funcionario.email_sec=email_sec
				funcionario.contato=contato
				funcionario.contato_sec=contato_sec
				funcionario.resp_contato_sec=resp_contato_sec
				funcionario.cpf=cpf
				funcionario.rg=rg
				funcionario.sexo=sexo
				funcionario.estado_civil=estado_civil
				funcionario.estado=estado
				funcionario.cidade=cidade
				funcionario.rua=rua
				funcionario.numero=numero
				funcionario.complemento=complemento
				funcionario.cep=cep
				funcionario.setor=setor
				funcionario.cargo=cargo
				funcionario.gerente=gerente
				funcionario.salario=salario
				funcionario.data_expedicao=data_expedicao
				funcionario.data_nascimento=data_nascimento
				funcionario.data_contratacao=data_contratacao
				funcionario.data_demissao=data_demissao
				funcionario.data_inicio_ferias=data_inicio_ferias
				funcionario.conta_banco=conta_banco
				funcionario.save()

				# Gravo as informações anteriores no Histórico de Funcionários
				HistoricoFuncionario(
					funcionario=funcionario,
					setor=funcionario.setor,
					cargo=funcionario.cargo,
					contrato=funcionario.get_contrato,
					salario=funcionario.salario,
				).save()

			return messages.success(request, 'Funcionário(a) alterado(a) com sucesso!')

		except Exception as e:
			return messages.error(request, f'Funcionário(a) não foi alterado(a): {e}!')


def atualizar_perfil_funcionario(request, funcionario):
	nome_completo = request.POST.get('nome_completo')
	nome_social = request.POST.get('nome_social') if not_none_not_empty(request.POST.get('nome_social')) else ''
	nome_mae = request.POST.get('nome_mae') if not_none_not_empty(request.POST.get('nome_mae')) else ''
	nome_pai = request.POST.get('nome_pai') if not_none_not_empty(request.POST.get('nome_pai')) else ''
	email = request.POST.get('email')
	email_sec = request.POST.get('email_sec') if not_none_not_empty(request.POST.get('email_sec')) else ''
	contato = ''
	contato_sec = ''
	resp_contato_sec = request.POST.get('resp_contato_sec') if not_none_not_empty(request.POST.get('resp_contato_sec')) else ''
	cpf = request.POST.get('cpf')
	rg = request.POST.get('rg')
	estado_civil = request.POST.get('estado_civil')
	estado = Estado.objects.get(pk=int(request.POST.get('estado')))
	cidade = Cidade.objects.get(pk=int(request.POST.get('cidade')))
	rua = request.POST.get('rua')
	numero = request.POST.get('numero')
	complemento = request.POST.get('complemento') if not_none_not_empty(request.POST.get('complemento')) else None
	cep = request.POST.get('cep')
	data_nascimento = request.POST.get('data_nascimento')
	data_expedicao = request.POST.get('data_expedicao')

	if len(nome_completo.split()) > 1:
		first_name = ' '.join(nome_completo.split()[:-1])
		last_name = nome_completo.split()[-1]
		username = f'{nome_completo.split()[0].lower()}.{last_name.lower()}'
	else:
		first_name = nome_completo.lower()
		last_name = ' '
		username = first_name

	if not_none_not_empty(request.POST.get('contato')) and request.POST.get('contato').startswith('('):
		contato = request.POST.get('contato')

	if not_none_not_empty(request.POST.get('contato_sec')) and request.POST.get('contato_sec').startswith('('):
		contato_sec = request.POST.get('contato_sec')

	try:
		if Usuario.objects.exclude(pk=funcionario.usuario.id).filter(username=username).exists():
			username = funcionario.matricula

		with transaction.atomic():
			funcionario.usuario.username=username
			funcionario.usuario.first_name=first_name
			funcionario.usuario.last_name=last_name
			funcionario.usuario.email=email
			funcionario.usuario.save()
			
			funcionario.nome_completo=nome_completo
			funcionario.nome_social=nome_social
			funcionario.nome_mae=nome_mae
			funcionario.nome_pai=nome_pai
			funcionario.email=email
			funcionario.email_sec=email_sec
			funcionario.contato=contato
			funcionario.contato_sec=contato_sec
			funcionario.resp_contato_sec=resp_contato_sec
			funcionario.cpf=cpf
			funcionario.rg=rg
			funcionario.estado_civil=estado_civil
			funcionario.estado=estado
			funcionario.cidade=cidade
			funcionario.rua=rua
			funcionario.numero=numero
			funcionario.complemento=complemento
			funcionario.cep=cep
			funcionario.data_expedicao=data_expedicao
			funcionario.data_nascimento=data_nascimento
			funcionario.save()

	except Exception as e:
		messages.error(request, f'Funcionário(a) não foi alterado(a): {e}!')
		return redirect('perfil')
