import argparse
import json
import logging
import pytz
import os
import sys
import django

sys.path.append('C:\inetpub\wwwroot\crony')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'settings.settings')
django.setup()

from datetime import datetime

from django.core.mail import EmailMessage
from django.db.models import Q

from configuracoes.models import Variavel
from funcionarios.models import Funcionario, TipoDocumento, Documento
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

	allowed_extensions = ['pdf', 'png', 'jpg', 'jpeg', 'docx']

	if nodes:
		for node in nodes:
			try:
				caminho_arquivo = os.path.normpath(node)
				codigo = caminho_arquivo.split('\\')[-2].split('-')[0].strip()
				nome_repartido = caminho_arquivo.split('\\')[-1].split('.')[0].split('_')

				extension = caminho_arquivo.split('\\')[-1].split('.')[-1]
				if extension not in allowed_extensions:
					raise InvalidExtension(node, allowed_extensions)

				with open(caminho_arquivo, 'rb') as f:
					documento = f.read()

				if not documento or len(codigo) not in [3, 6]:
					raise InvalidCodeOrDocument(node)
				
				if documento and len(codigo) == 6:
					funcionario = Funcionario.objects.get(matricula=codigo)
					tipo = TipoDocumento.objects.get(codigo=nome_repartido[0].strip())
					caminho = f'{nome_repartido[1].strip()}.{extension}'

					try:
						data_documento = datetime.strptime(nome_repartido[2].strip(), '%d-%m-%Y')
					except Exception:
						data_documento = datetime.now()

				if documento and len(codigo) == 3:
					funcionario = None
					tipo = TipoDocumento.objects.get(codigo=codigo)
					caminho = f'{nome_repartido[0].strip()}.{extension}'

					try:
						data_documento = datetime.strptime(nome_repartido[1].strip(), '%d-%m-%Y')
					except Exception:
						data_documento = datetime.now()

				if not Documento.objects.filter(funcionario=funcionario, caminho=caminho, data_documento=data_documento, tipo=tipo).exists():
					Documento.objects.create(caminho=caminho, documento=documento, data_documento=data_documento, tipo=tipo, funcionario=funcionario)
					logging.info(f'SUCCESS::CREATE::funcionario: {funcionario}, nome: {caminho}, tipo: {tipo}, data: {data_documento}')
				else:
					Documento.objects.filter(funcionario=funcionario, caminho=caminho, data_documento=data_documento, tipo=tipo).update(documento=documento)
					logging.info(f'SUCCESS::UPDATE::funcionario: {funcionario}, nome: {caminho}, tipo: {tipo}, data: {data_documento}')
			
			except Exception as e:
				logging.info(f'Raise exception in {node}: {e}')
				continue

	else:
		diretorios = [i.valor for i in Variavel.objects.filter(Q(chave='PATH_DOCS') | Q(chave='PATH_DOCS_EMP'))]

		for pasta in diretorios:
			for root, _, files in os.walk(pasta):
				for file in files:
					try:
						extension = file.split('.')[-1]
						if extension not in allowed_extensions:
							raise InvalidExtension(file, allowed_extensions)

						caminho_arquivo = os.path.join(root, file)
						codigo = root.split('\\')[-1].split('-')[0].strip()
						nome_repartido = file.split('.')[0].split('_')

						with open(caminho_arquivo, 'rb') as f:
							documento = f.read()

						if not documento or len(codigo) not in [3, 6]:
							raise InvalidCodeOrDocument(file)

						if documento and len(codigo) == 6:
							funcionario = Funcionario.objects.get(matricula=codigo)
							tipo = TipoDocumento.objects.get(codigo=nome_repartido[0].strip())
							caminho = f'{nome_repartido[1].strip()}.{extension}'

							try:
								data_documento = datetime.strptime(nome_repartido[2].strip(), '%d-%m-%Y')
							except Exception:
								data_documento = datetime.now()

						if documento and len(codigo) == 3:
							funcionario = None
							tipo = TipoDocumento.objects.get(codigo=codigo)
							caminho = f'{nome_repartido[0].strip()}.{extension}'

							try:
								data_documento = datetime.strptime(nome_repartido[1].strip(), '%d-%m-%Y')
							except Exception:
								data_documento = datetime.now()

						if not Documento.objects.filter(funcionario=funcionario, caminho=caminho, data_documento=data_documento, tipo=tipo).exists():
							Documento.objects.create(caminho=caminho, documento=documento, data_documento=data_documento, tipo=tipo, funcionario=funcionario)
							logging.info(f'SUCCESS::CREATE::funcionario: {funcionario}, nome: {caminho}, tipo: {tipo}, data: {data_documento}')
						else:
							Documento.objects.filter(funcionario=funcionario, caminho=caminho, data_documento=data_documento, tipo=tipo).update(documento=documento)
							logging.info(f'SUCCESS::UPDATE::funcionario: {funcionario}, nome: {caminho}, tipo: {tipo}, data: {data_documento}')

					except Exception as e:
						logging.info(f'Raise exception in {file}: {e}')
						continue
	
	email = EmailMessage(
		subject='Log de Importação (Crony)',
		body='Email automático, por favor não responda!',
		from_email=DEFAULT_FROM_EMAIL,
		to=['ronilda@14ri.com.br',]
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
