# ruff: noqa: E402
import calendar
import logging
import os
import sys

import django
import pytz

sys.path.append('C:\inetpub\wwwroot\crony')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'settings.settings')
django.setup()

from datetime import datetime

from funcionarios.models import Funcionario, Score  # noqa: F401
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
			anomes = int(datetime.today().replace(month=datetime.today().month - 1).strftime('%Y%m'))
			funcionarios = Funcionario.objects.filter(data_demissao=None).order_by('nome_completo')
			data_inicial = f'{datetime.today().year}-{datetime.today().month - 1:02}-01'
			data_final = f'{datetime.today().year}-{datetime.today().month - 1:02}-{calendar.monthrange(datetime.today().year, datetime.today().month - 1)[1]}'
			_, scores = pontos_por_dia(data_inicial, data_final, funcionarios, True)
		
			for moeda in Moeda.objects.filter(fechado=False, anomes=anomes, funcionario__in=funcionarios):
				moeda.fechado = True
				moeda.save()

			for score in Score.objects.filter(fechado=False, anomes=anomes, funcionario__in=funcionarios):
				scores_fechados = Score.objects.filter(fechado=True, anomes=anomes, funcionario=score.funcionario)
				total_scores_fechados = sum([i.pontuacao for i in scores_fechados])
				nro_scores_fechados = len(scores_fechados) + 1
				nota_calculada = scores.get(score.funcionario, [0])[0]

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
