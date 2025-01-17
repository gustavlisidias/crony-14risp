# ruff: noqa: E402
# ruff: noqa: F401
import argparse
import json
import logging
import pytz
import os
import sys
import django

from pathlib import Path
from dotenv import load_dotenv

load_dotenv(os.path.join(Path(__file__).resolve().parent.parent, '.env'))
sys.path.append(os.getenv('SYSTEM_PATH'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'settings.settings')
django.setup()

from datetime import datetime
from pathlib import Path

from django.core.mail import EmailMessage
from django.db.models import Q

from configuracoes.models import Variavel
from funcionarios.models import Funcionario, TipoDocumento, Documento
from funcionarios.utils import allowed_extensions
from settings.settings import BASE_DIR, DEFAULT_FROM_EMAIL


class InvalidExtension(Exception):
	def __init__(self, file, allowed_extensions):
		self.file = file
		self.allowed_extensions = allowed_extensions
		message = f'Extensão inválida em {self.file}, certifique de que o arquivo esteja em algum dos formatos: {self.allowed_extensions}'
		super().__init__(message)


class InvalidCodeOrDocument(Exception):
	def __init__(self, file):
		self.file = file
		message = f'Não foi indentificado o código ou não foi possível realizar a leitura do arquivo em {self.file}'
		super().__init__(message)


def criar_pastas():
	pasta_colaboradores_ativos = Variavel.objects.get(chave='PATH_DOCS_EMP').valor
	pasta_colaboradores_inativos = os.path.join(pasta_colaboradores_ativos, 'Demitidos')
	pasta_diversos = Variavel.objects.get(chave='PATH_DOCS').valor

	# Criar pasta para funcionários demitidos
	if not os.path.exists(pasta_colaboradores_inativos):
		os.makedirs(pasta_colaboradores_inativos)

	# Criar pasta para funcionários ativos
	for i in Funcionario.objects.filter(data_demissao=None):
		nome_pasta = f'{i.matricula} - {i.nome_completo}'
		path = os.path.join(pasta_colaboradores_ativos, nome_pasta)

		if not os.path.exists(path):
			os.makedirs(path)

	# Criar pasta para funcionários inativos
	for i in Funcionario.objects.exclude(data_demissao=None):
		nome_pasta = f'{i.matricula} - {i.nome_completo}'
		path = os.path.join(pasta_colaboradores_inativos, nome_pasta)

		if not os.path.exists(path):
			os.makedirs(path)

	# Criar pastas para tipos de documento
	for i in TipoDocumento.objects.all():
		nome_pasta = f"{i.codigo} - {i.tipo}"
		path = os.path.join(pasta_diversos, nome_pasta)
		if not os.path.exists(path):
			os.makedirs(path)


def importar_documentos(nodes):
	log_file = f'importacao_documentos_{datetime.now().replace(tzinfo=pytz.utc).strftime("%Y-%m-%d_%H-%M-%S")}.log'
	log_path = os.path.join(BASE_DIR, f'logs/tasks/{log_file}')
	logging.basicConfig(filename=log_path, encoding='utf-8', level=logging.INFO, force=True)

	# Importação de pastas
	if nodes:
		for node in nodes:
			caminho = os.path.normpath(node)
			nome_arquivo, extensao = caminho.split('\\')[-1].split('.')

			if extensao in allowed_extensions:
				try:
					codigo = caminho.split('\\')[-2].split('-')[0].strip()
					nome_repartido = nome_arquivo.split('_')

					if codigo.isdigit() and len(codigo) == 3:
						funcionario = None
						tipo = TipoDocumento.objects.get(codigo=codigo)
						data_documento = datetime.strptime(nome_repartido[0].strip(), '%Y-%m-%d') if len(nome_repartido) == 2 else datetime.now()
					
					elif codigo.isdigit() and len(codigo) == 6:
						funcionario = Funcionario.objects.get(matricula=codigo)

						if len(nome_repartido) == 3:
							tipo = TipoDocumento.objects.get(codigo=nome_repartido[1].strip())
							data_documento = datetime.strptime(nome_repartido[0].strip(), '%Y-%m-%d')
						else:
							tipo = TipoDocumento.objects.get(codigo=nome_repartido[0].strip())
							data_documento = datetime.now()
					
					else:
						raise InvalidCodeOrDocument(nome_arquivo)
					
					if not Documento.objects.filter(caminho=caminho).exists():
						Documento(tipo=tipo, data_documento=data_documento, funcionario=funcionario, caminho=caminho).save()
						logging.info(f'SUCCESS::CREATE::{caminho}')
					else:
						logging.info(f'SUCCESS::NOT CREATE::{caminho}')

				except Exception as e:
					logging.info(f'Raise exception in {nome_arquivo}: {e}')
					continue

	# Importador total dos diretorios
	else:
		diretorios = [i.valor for i in Variavel.objects.filter(Q(chave='PATH_DOCS') | Q(chave='PATH_DOCS_EMP'))]

		for pasta in diretorios:
			for root, _, files in os.walk(pasta):
				for file in files:
					nome_arquivo, extensao = file.split('.')
					caminho = os.path.join(root, file)

					if extensao in allowed_extensions:
						try:						
							codigo = root.split('\\')[-1].split('-')[0].strip()
							nome_repartido = nome_arquivo.split('_')

							if codigo.isdigit() and len(codigo) == 3:
								funcionario = None
								tipo = TipoDocumento.objects.get(codigo=codigo)
								data_documento = datetime.strptime(nome_repartido[0].strip(), '%Y-%m-%d') if len(nome_repartido) == 2 else datetime.now()
							
							elif codigo.isdigit() and len(codigo) == 6:
								funcionario = Funcionario.objects.get(matricula=codigo)

								if len(nome_repartido) == 3:
									tipo = TipoDocumento.objects.get(codigo=nome_repartido[1].strip())
									data_documento = datetime.strptime(nome_repartido[0].strip(), '%Y-%m-%d')
								else:
									tipo = TipoDocumento.objects.get(codigo=nome_repartido[0].strip())
									data_documento = datetime.now()
							
							else:
								raise InvalidCodeOrDocument(file)
							
							if not Documento.objects.filter(caminho=caminho).exists():
								Documento(tipo=tipo, data_documento=data_documento, funcionario=funcionario, caminho=caminho).save()
								logging.info(f'SUCCESS::CREATE::{caminho}')
							else:
								logging.info(f'SUCCESS::NOT CREATE::{caminho}')

						except Exception as e:
							logging.info(f'Raise exception in {file}: {e}')
							continue
	
	email = EmailMessage(
		subject='Log de Importação (Crony)',
		body='Email automático, por favor não responda!',
		from_email=DEFAULT_FROM_EMAIL,
		to=['gustavo@novadigitalizacao.com.br', 'ronilda@14ri.com.br']
	)
	email.attach_file(log_path)
	email.send(fail_silently=False)


if __name__ == '__main__':
	parser = argparse.ArgumentParser(description='Importar Documentos')
	parser.add_argument('--nodes', help='Caminho para o arquivo que contém a lista de arquivos', required=False)

	args = parser.parse_args()
	nodes = None

	if args.nodes:
		with open(args.nodes, 'r') as file:
			nodes = json.load(file)

	criar_pastas()
	importar_documentos(nodes)
