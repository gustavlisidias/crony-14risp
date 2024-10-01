# ruff: noqa: E402
# ruff: noqa: F401
import logging
import pytz
import os
import sys
import pandas as pd
import django

sys.path.append('C:\inetpub\wwwroot\crony')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'settings.settings')
django.setup()

from datetime import datetime

from funcionarios.models import Funcionario, HistoricoFuncionario
from settings.settings import BASE_DIR


def parse_date(date_str):
	if isinstance(date_str, pd.Timestamp):
		return date_str.date()
	elif isinstance(date_str, datetime):
		return date_str
	else:
		return datetime.strptime(date_str, '%d/%m/%Y').date()


def importar_historico(planilha):
	log_file = f'importador_historico_{datetime.now().replace(tzinfo=pytz.utc).strftime("%Y-%m-%d_%H-%M-%S")}.log'
	log_path = os.path.join(BASE_DIR, f'logs/tasks/{log_file}')
	logging.basicConfig(filename=log_path, encoding='utf-8', level=logging.INFO, force=True)

	df = pd.read_excel(planilha, dtype={'matricula': str})
	for _, row in df.iterrows():
		matricula = f'{int(row["matricula"]):06}'
		data_alteracao = parse_date(row['data_cadastro'])
		salario = float(row['salario'])
		motivo = row['motivo'] if not pd.isna(row['motivo']) else None

		try:
			funcionario = Funcionario.objects.get(matricula=matricula)
			HistoricoFuncionario.objects.create(
				funcionario=funcionario,
				setor=funcionario.setor,
				cargo=funcionario.cargo,
				contrato=funcionario.get_contrato,
				salario=salario,
				data_alteracao=data_alteracao,
				observacao=motivo
			)
			logging.info(f'SUCCESS::CREATE::funcionario: {funcionario}, data: {data_alteracao}, salario: {salario}, motivo: {motivo}')
		except Exception as e:
			logging.info(f'ERROR::CREATE::matricula: {matricula}, data: {data_alteracao}, salario: {salario}, motivo: {motivo}, e: {e}')


if __name__ == '__main__':
	planilha = os.path.join(BASE_DIR, 'documentacao\\salarios_14risp.xlsx')
	importar_historico(planilha)
