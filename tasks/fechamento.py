# ruff: noqa: E402, F401
import logging
import os
import sys
import calendar

import django
import pytz

from pathlib import Path
from dotenv import load_dotenv

load_dotenv(os.path.join(Path(__file__).resolve().parent.parent, '.env'))
sys.path.append(os.getenv('SYSTEM_PATH'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'settings.settings')
django.setup()

from datetime import datetime
from dateutil.relativedelta import relativedelta

from funcionarios.models import Funcionario, Score
from ponto.utils import pontos_por_dia
from settings.settings import BASE_DIR
from web.models import Moeda


def fechamento_pontuacoes():
	'''
	No primeiro dia de cada mês, verifico as moedas em aberto
	Filtrando a referencia ano-mes na data de hoje -1 mês
	Exemplo: hoje é 01/09/2024 a referencia é 202408, todas as moedas abertas nessa referencia serão fechadas
	'''
	if datetime.today().day == 1:
		log_file = f'fechamento_{datetime.now().replace(tzinfo=pytz.utc).strftime("%Y-%m-%d_%H-%M-%S")}.log'
		log_path = os.path.join(BASE_DIR, f'logs/tasks/{log_file}')
		logging.basicConfig(filename=log_path, encoding='utf-8', level=logging.INFO, force=True)
		
		try:
			mes = datetime.today().month - 1 if datetime.today().month > 1 else 12
			ano = datetime.today().year if datetime.today().month > 1 else datetime.today().year - 1
			ultimo_dia = calendar.monthrange(datetime.today().year, datetime.today().month - 1)[1] if datetime.today().month > 1 else 31

			anomes = int(f'{ano}{mes:02}')
			data_inicial = f'{ano}-{mes:02}-01'
			data_final = f'{ano}-{mes:02}-{ultimo_dia}'
			
			funcionarios = Funcionario.objects.filter(data_demissao=None).order_by('nome_completo')
			_, scores = pontos_por_dia(data_inicial, data_final, funcionarios, True)
		
			for moeda in Moeda.objects.filter(fechado=False, anomes=anomes, funcionario__in=funcionarios):
				moeda.fechado = True
				moeda.save()

			for score in Score.objects.filter(fechado=False, anomes=anomes, funcionario__in=funcionarios):
				scores_fechados = Score.objects.filter(fechado=True, anomes=anomes, funcionario=score.funcionario)
				total_scores_fechados = sum([i.pontuacao for i in scores_fechados])
				nro_scores_fechados = len(scores_fechados) + 1
				nota_calculada = scores.get(score.funcionario.id)['media']

				pontuacao = (nota_calculada + total_scores_fechados) / nro_scores_fechados
				scores_fechados.delete()

				score.pontuacao = pontuacao
				score.fechado = True
				score.save()
			
			for funcionario in funcionarios:
				Score.objects.create(funcionario=funcionario)
			
			logging.info('Fechamento mensal realizado!')

		except Exception as e:
			logging.info(f'Fechamento mensal não foi realizado: {e}')


if __name__ == '__main__':
	fechamento_pontuacoes()
