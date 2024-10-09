# ruff: noqa: E402
import logging
import os
import sys

import django
import pandas as pd
import pytz

sys.path.append('C:\inetpub\wwwroot\crony')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'settings.settings')
django.setup()

from datetime import datetime

from django.db import transaction

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

	pontos_funcionarios = {}
	df = pd.read_excel(planilha, dtype={'Nome': str})

	for _, row in df.iterrows():
		funcionario = row['Nome'].strip().title()
		data = row['Data']

		if data not in pontos_funcionarios:
			pontos_funcionarios[data] = {}
		
		if funcionario not in pontos_funcionarios[data]:
			pontos_funcionarios[data][funcionario] = []
		
		if not pd.isna(row['1 Saída']):
			pontos_funcionarios[data][funcionario].append(row['1 Entrada'])
			pontos_funcionarios[data][funcionario].append(row['1 Saída'])

		if not pd.isna(row['2 Saída']):
			pontos_funcionarios[data][funcionario].append(row['2 Entrada'])
			pontos_funcionarios[data][funcionario].append(row['2 Saída'])

		if not pd.isna(row['3 Saída']):
			pontos_funcionarios[data][funcionario].append(row['3 Entrada'])
			pontos_funcionarios[data][funcionario].append(row['3 Saída'])

		if not pd.isna(row['4 Saída']):
			pontos_funcionarios[data][funcionario].append(row['4 Entrada'])
			pontos_funcionarios[data][funcionario].append(row['4 Saída'])

		if not pd.isna(row['5 Saída']):
			pontos_funcionarios[data][funcionario].append(row['5 Entrada'])
			pontos_funcionarios[data][funcionario].append(row['5 Saída'])

	for data, funcionarios in pontos_funcionarios.items():
		for funcionario, pontos in funcionarios.items():
			if len(pontos) % 2 != 0:
				logging.error(f'Quantidade de pontos para o funcionário {funcionario} no dia {data} não batem para entrada-saida')
				continue
			else:
				horas = [datetime.strptime(str(i), '%H:%M').time() for i in pontos]
			
			try:
				with transaction.atomic():
					funcionario = Funcionario.objects.get(nome_completo=funcionario)
					Ponto.objects.filter(funcionario=funcionario, data=data).delete()

					for hora in horas:
						Ponto.objects.create(
							data=data,
							hora=hora,
							funcionario=funcionario,
							motivo='Importação PontoMais'
						)
				
				logging.info(f'Ponto criado com sucesso para o funcionario {funcionario.nome_completo} no dia {data}')
			except Exception as e:
				logging.error(f'Não foi possível criar o ponto para o funcionario {funcionario} no dia {data}: {e}')


if __name__ == '__main__':
	planilha = os.path.join(BASE_DIR, 'media\\pontos.xlsx')
	importar_pontos(planilha)
