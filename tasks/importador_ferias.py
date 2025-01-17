# ruff: noqa: E402
# ruff: noqa: F401
import logging
import pytz
import os
import sys
import pandas as pd
import django

from pathlib import Path
from dotenv import load_dotenv

load_dotenv(os.path.join(Path(__file__).resolve().parent.parent, '.env'))
sys.path.append(os.getenv('SYSTEM_PATH'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'settings.settings')
django.setup()

from datetime import datetime, timedelta

from agenda.models import Ferias
from agenda.utils import ferias_funcionarios
from funcionarios.models import Funcionario
from settings.settings import BASE_DIR


def parse_date(date_str):
	if isinstance(date_str, pd.Timestamp):
		return date_str.date()
	elif isinstance(date_str, datetime):
		return date_str.date()
	else:
		return datetime.strptime(date_str.strip(), '%d/%m/%Y').date()


def importar_ferias(planilha):
	log_file = f'importador_ferias_{datetime.now().replace(tzinfo=pytz.utc).strftime("%Y-%m-%d_%H-%M-%S")}.log'
	log_path = os.path.join(BASE_DIR, f'logs/tasks/{log_file}')
	logging.basicConfig(filename=log_path, encoding='utf-8', level=logging.INFO, force=True)

	df = pd.read_excel(planilha, dtype={'matricula': str})
	ferias_por_matricula = {}
	for _, row in df.iterrows():
		matricula = f'{int(row["Matrícula"]):06}'
		# abono = int(row['abono']) if not pd.isna(row['abono']) and row['abono'] not in ['', ' '] else 0
		inicio_periodo = parse_date(row['Início'])
		final_periodo = parse_date(row['Vencimento'])
		# inicio_ferias = parse_date(row['inicio_ferias'])
		# final_ferias = parse_date(row['final_ferias']) if not pd.isna(row['final_ferias']) else inicio_ferias + timedelta(days=30-abono)
		ano_referencia = row['Período']

		if matricula not in ferias_por_matricula:
			ferias_por_matricula[matricula] = []

		ferias_por_matricula[matricula].append({'periodo': ano_referencia, 'inicio': inicio_periodo, 'vencimento': final_periodo})

		# try:
		# 	funcionario = Funcionario.objects.get(matricula=matricula)
		# 	Ferias.objects.create(
		# 		funcionario=funcionario,
		# 		ano_referencia=ano_referencia,
		# 		inicio_periodo=inicio_periodo,
		# 		final_periodo=final_periodo,
		# 		inicio_ferias=inicio_ferias,
		# 		final_ferias=final_ferias,
		# 		abono=abono
		# 	)
		# 	logging.info(f'SUCCESS::CREATE::funcionario: {funcionario}, inicio: {inicio_ferias}, final: {final_ferias}, abono: {abono}')
		# except Exception:
		# 	logging.info(f'ERROR::CREATE::matricula: {matricula}, inicio: {inicio_ferias}, final: {final_ferias}, abono: {abono}')

	ferias_calculadas = ferias_funcionarios(Funcionario.objects.all())

	for funcionario, dados in ferias_calculadas.items():
		ferias_abertas = ferias_por_matricula.get(funcionario.matricula)
		if ferias_abertas:
			periodos_abertos = [i['periodo'] for i in ferias_abertas]
			for dado in dados:
				if dado['periodo'] not in periodos_abertos:
					try:
						final = dado['inicio'] + dado['direito']
						Ferias(
							funcionario=funcionario,
							ano_referencia=dado['periodo'],
							inicio_periodo=dado['inicio'],
							final_periodo=dado['vencimento'],
							inicio_ferias=dado['inicio'],
							final_ferias=final,
							abono=0
						).save()

						logging.info(f"SUCCESS::CREATE::funcionario: {funcionario}, inicio: {dado['inicio']}, final: {final}")
					
					except Exception:
						logging.info(f"ERROR::CREATE::matricula: {matricula}, inicio: {dado['inicio']}, final: {final}")


if __name__ == '__main__':
	planilha = os.path.join(BASE_DIR, 'media\\ferias-nova.xlsx')
	importar_ferias(planilha)
