# ruff: noqa: E402
import logging
import os
import sys

import django
import pandas as pd
import pytz

from pathlib import Path
from dotenv import load_dotenv

load_dotenv(os.path.join(Path(__file__).resolve().parent.parent, '.env'))
sys.path.append(os.getenv('SYSTEM_PATH'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'settings.settings')
django.setup()

from datetime import datetime

from funcionarios.models import Funcionario
from ponto.models import Ponto
from settings.settings import BASE_DIR


def importar_pontos(planilha):
	log_file = f'importador_pontos_{datetime.now().replace(tzinfo=pytz.utc).strftime("%Y-%m-%d_%H-%M-%S")}.log'
	log_path = os.path.join(BASE_DIR, f'logs/tasks/{log_file}')
	logging.basicConfig(filename=log_path, encoding='utf-8', level=logging.INFO, force=True)

	for funcionario in Funcionario.objects.all():
		funcionario.nome_completo = funcionario.nome_completo.strip()
		funcionario.save()
	
	df = pd.read_excel(planilha, dtype={'nome': str})
	for _, row in df.iterrows():
		matricula = int(row['matricula'])
		data = row['data'].date()
		hora = datetime.strptime(row['hora'], '%H:%M').time()
		alterado = True if row['alterado'] == 'true' else False
		motivo = row['motivo']
		encerrado = True if row['encerrado'] == 'true' else False
		data_fechamento = row['data_fechamento'].date() if not pd.isna(row['data_fechamento']) else None
		data_modificacao = datetime.strptime(row['data_cadastro'], '%Y-%m-%d %H:%M:%S.%f %z')

		try:
			funcionario = Funcionario.objects.get(matricula=f'{matricula:06}')
			Ponto(
				funcionario=funcionario,
				data=data,
				hora=hora,
				alterado=alterado,
				motivo=motivo,
				encerrado=encerrado,
				data_fechamento=data_fechamento,
				data_modificacao=data_modificacao,
				autor_modificacao=Funcionario.objects.get(pk=1)
			).save()
			logging.info(f"SUCCESS::CREATE::MATRICULA {matricula}")
		except Exception as e:
			logging.info(f"ERROR::CREATE::MATRICULA {matricula}::{e}")


if __name__ == '__main__':
	planilha = os.path.join(BASE_DIR, 'media\\pontos.xlsx')
	importar_pontos(planilha)
