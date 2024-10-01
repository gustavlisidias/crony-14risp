# ruff: noqa: E402
import logging
import os
import sys
import random

import django
import pandas as pd
import pytz

sys.path.append('C:\inetpub\wwwroot\crony')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'settings.settings')
django.setup()

from datetime import datetime, timedelta

from cities_light.models import Region as Estado
from cities_light.models import SubRegion as Cidade
from django.contrib.auth.hashers import make_password
from django.db import transaction
from django.utils.timezone import make_aware

from agenda.models import Ferias
from configuracoes.models import Jornada, Usuario
from funcionarios.models import (
	Cargo,
	Funcionario,
	JornadaFuncionario,
	Perfil,
	Score,
	Setor,
)
from settings.settings import BASE_DIR


def gerar_cpf():
    bloco1 = f'{random.randint(0, 999):03}'
    bloco2 = f'{random.randint(0, 999):03}'
    bloco3 = f'{random.randint(0, 999):03}'
    bloco4 = f'{random.randint(0, 99):02}'
    numero_formatado = f'{bloco1}.{bloco2}.{bloco3}-{bloco4}'
    return numero_formatado


def gerar_rg():
    bloco1 = f'{random.randint(0, 99):02}'
    bloco2 = f'{random.randint(0, 999):03}'
    bloco3 = f'{random.randint(0, 999):03}'
    bloco4 = f'{random.randint(0, 99):02}'
    numero_formatado = f'{bloco1}.{bloco2}.{bloco3}-{bloco4}'
    return numero_formatado


def parse_date(date_str):
	if pd.isna(date_str):
		return None
	if isinstance(date_str, pd.Timestamp):
		return date_str.date()
	if isinstance(date_str, datetime):
		return date_str
	try:
		return datetime.strptime(date_str, '%d/%m/%Y').date()
	except ValueError:
		return None


def adicionar_ferias(funcionario):
	data_admissao = funcionario.data_contratacao
	ano_inicio = data_admissao.year + 1
	ano_final = 2023

	# Criar objetos de férias para cada ano
	for ano in range(ano_inicio, ano_final + 1):
		inicio_ferias = make_aware(datetime(ano, data_admissao.month, data_admissao.day))
		final_ferias = inicio_ferias + timedelta(days=30)  # Assumindo 30 dias de férias
		
		Ferias.objects.create(
			funcionario=funcionario,
			inicio=inicio_ferias,
			final=final_ferias,
			abono=0,
			decimo=False
		)


def importar_funcionario(planilha):
	log_file = f'importador_funcionarios_{datetime.now().replace(tzinfo=pytz.utc).strftime("%Y-%m-%d_%H-%M-%S")}.log'
	log_path = os.path.join(BASE_DIR, f'logs/tasks/{log_file}')
	logging.basicConfig(filename=log_path, encoding='utf-8', level=logging.INFO, force=True)

	df = pd.read_excel(planilha, dtype={'matricula': str})
	for _, row in df.iterrows():
		matricula = row['matricula']
		nome_completo = row['nome_completo']
		nome_social = row['nome_social'] if not pd.isna(row['nome_social']) else None
		nome_mae = row['nome_mae'] if not pd.isna(row['nome_mae']) else None
		nome_pai = row['nome_pai'] if not pd.isna(row['nome_pai']) else None
		email = row['email'] if not pd.isna(row['email']) else None
		email_sec = row['email_sec'] if not pd.isna(row['email_sec']) else None
		contato = row['contato'] if not pd.isna(row['contato']) else None
		contato_sec = row['contato_sec'] if not pd.isna(row['contato_sec']) else None
		resp_contato_sec = row['resp_contato_sec'] if not pd.isna(row['resp_contato_sec']) else None
		cpf = row['cpf'] if not pd.isna(row['cpf']) else gerar_cpf()
		rg = row['rg'] if not pd.isna(row['rg']) else gerar_rg()
		sexo = row['sexo'] if not pd.isna(row['sexo']) else 'M'
		estado_civil = row['estado_civil'] if not pd.isna(row['estado_civil']) else 'S'
		estado = Estado.objects.get(pk=row['estado']) if not pd.isna(row['estado']) else None
		cidade = Cidade.objects.get(pk=row['cidade']) if not pd.isna(row['cidade']) else None
		rua = row['rua'] if not pd.isna(row['rua']) else None
		numero = row['numero'] if not pd.isna(row['numero']) else None
		complemento = row['complemento'] if not pd.isna(row['complemento']) else None
		cep = row['cep'] if not pd.isna(row['cep']) else None
		setor = Setor.objects.get(pk=row['setor'])
		cargo = Cargo.objects.get(pk=row['cargo'])
		gerente = Funcionario.objects.get(matricula=row['responsavel']) if not pd.isna(row['responsavel']) else None
		salario = row['salario'] if not pd.isna(row['salario']) else 0
		data_expedicao = parse_date(row['data_expedicao']) if not pd.isna(row['data_expedicao']) else None
		data_nascimento = parse_date(row['data_nascimento']) if not pd.isna(row['data_nascimento']) else None
		data_contratacao = parse_date(row['data_contratacao']) if not pd.isna(row['data_contratacao']) else None
		data_demissao = parse_date(row['data_demissao']) if not pd.isna(row['data_demissao']) else None
		observacoes = row['observacoes'] if not pd.isna(row['observacoes']) else 'Observação:'
		conta_banco = row['conta_banco'] if not pd.isna(row['conta_banco']) else None
		contrato = row['contrato'] if not pd.isna(row['contrato']) else None

		# Dados do Usuario do Funcionario
		if len(nome_completo.split()) > 1:
			first_name = ' '.join(nome_completo.split()[:-1])
			last_name = nome_completo.split()[-1]
			username = f'{nome_completo.split()[0].lower()}.{last_name.lower()}'
		else:
			first_name = nome_completo.lower()
			last_name = ' '
			username = first_name

		is_gerente = True if row['gerente'] == 'S' else False
		email = email if email else f'{"".join(nome_completo.split()).lower()}@email.com'

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
					conta_banco=conta_banco,
					observacoes=observacoes
				)

				# Gerando jornada de trabalho do funcionário com base no Contrato selecionado
				jornadas = Jornada.objects.filter(contrato__id=contrato).order_by('contrato__id', 'dia', 'ordem')
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

				# Criar férias
				adicionar_ferias(funcionario)
				
			logging.info(f'Funcionário(a) {funcionario} foi criado(a) com sucesso!')

		except Exception as e:
			logging.info(f'Funcionário(a) não foi criado(a): {e}!')
		

if __name__ == '__main__':
	planilha = os.path.join(BASE_DIR, 'documentacao\\FUNCIONARIOS 2.xlsx')
	importar_funcionario(planilha)
