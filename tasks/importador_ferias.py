# ruff: noqa: E402
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

from datetime import datetime
from collections import defaultdict

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
	
	ferias_por_matricula = defaultdict(list)

	df = pd.read_excel(planilha, dtype={'matricula': str})
	for _, row in df.iterrows():
		matricula = f'{int(row["matricula"]):06}'
		ano_referencia = row['periodo']
		abono = int(row['abono']) if not pd.isna(row['abono']) and row['abono'] not in ['', ' '] else 0
		inicio_periodo = parse_date(row['inicio'])
		final_periodo = parse_date(row['final'])
		inicio_ferias = parse_date(row['entrada'])
		final_ferias = parse_date(row['saida'])

		if not pd.isna(inicio_ferias):
			ferias_por_matricula[matricula].append({
				'periodo': ano_referencia,
				'inicio_periodo': inicio_periodo,
				'final_periodo': final_periodo,
				'inicio_ferias': inicio_ferias,
				'final_ferias': final_ferias,
				'abono': abono
			})

	for matricula, dados in ferias_por_matricula.items():
		for dado in dados:
			try:
				funcionario = Funcionario.objects.filter(matricula=matricula)
				calculo_ferias = ferias_funcionarios(funcionario).get(funcionario.first())
				
				inicio_periodo, final_periodo = None, None
				for calculo in calculo_ferias:
					if calculo['periodo'] == dado['periodo']:
						inicio_periodo = calculo['inicio']
						final_periodo = calculo['vencimento']

				Ferias(
					funcionario=funcionario.first(),
					ano_referencia=dado['periodo'],
					inicio_ferias=dado['inicio_ferias'],
					final_ferias=dado['final_ferias'],
					inicio_periodo=inicio_periodo,
					final_periodo=final_periodo,
					abono=dado['abono']
				).save()

				logging.info(f"SUCCESS::CREATE::matricula: {matricula}, periodo: {dado['periodo']}, inicio: {inicio_periodo}, vencimento: {final_periodo}")
			
			except Exception as e:
				logging.info(f"ERROR::CREATE::matricula: {matricula}, periodo: {dado['periodo']}, inicio: {inicio_periodo}, vencimento: {final_periodo}")
				logging.error(e)


if __name__ == '__main__':
	planilha = os.path.join(BASE_DIR, 'documentacao/ferias_14risp.xlsx')
	importar_ferias(planilha)
