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

from datetime import datetime, timedelta

from agenda.models import Ferias
from funcionarios.models import Funcionario
from settings.settings import BASE_DIR


def parse_date(date_str):
	if isinstance(date_str, pd.Timestamp):
		return date_str.date()
	elif isinstance(date_str, datetime):
		return date_str
	else:
		return datetime.strptime(date_str, '%d/%m/%Y').date()


def importar_ferias(planilha):
	log_file = f'importador_ferias_{datetime.now().replace(tzinfo=pytz.utc).strftime("%Y-%m-%d_%H-%M-%S")}.log'
	log_path = os.path.join(BASE_DIR, f'logs/tasks/{log_file}')
	logging.basicConfig(filename=log_path, encoding='utf-8', level=logging.INFO, force=True)

	df = pd.read_excel(planilha, dtype={'matricula': str})
	for _, row in df.iterrows():
		matricula = f'{int(row["matricula"]):06}'
		abono = int(row['abono']) if not pd.isna(row['abono']) and row['abono'] not in ['', ' '] else 0
		inicio_periodo = parse_date(row['inicio_periodo'])
		final_periodo = parse_date(row['final_periodo'])
		inicio_ferias = parse_date(row['inicio_ferias'])
		final_ferias = parse_date(row['final_ferias']) if not pd.isna(row['final_ferias']) else inicio_ferias + timedelta(days=30-abono)
		ano_referencia = inicio_periodo.year - 1

		try:
			funcionario = Funcionario.objects.get(matricula=matricula)
			Ferias.objects.create(
				funcionario=funcionario,
				ano_referencia=ano_referencia,
				inicio_periodo=inicio_periodo,
				final_periodo=final_periodo,
				inicio_ferias=inicio_ferias,
				final_ferias=final_ferias,
				abono=abono
			)
			logging.info(f'SUCCESS::CREATE::funcionario: {funcionario}, inicio: {inicio_ferias}, final: {final_ferias}, abono: {abono}')
		except Exception:
			logging.info(f'ERROR::CREATE::matricula: {matricula}, inicio: {inicio_ferias}, final: {final_ferias}, abono: {abono}')


if __name__ == '__main__':
	planilha = os.path.join(BASE_DIR, 'documentacao\\ferias_maria-jesus.xlsx')
	importar_ferias(planilha)
