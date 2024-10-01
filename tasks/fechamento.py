# ruff: noqa: E402
import logging
import os
import sys

import django
import pytz

sys.path.append('C:\inetpub\wwwroot\crony')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'settings.settings')
django.setup()

from datetime import datetime

from funcionarios.models import Funcionario, JornadaFuncionario, Score
from ponto.models import Ponto
from ponto.utils import pontos_funcionarios
from settings.settings import BASE_DIR
from web.models import Moeda


def fechamento_pontuacoes():
	'''
	No primeiro dia de cada mês, verifico as moedas em aberto
	Filtrando a referencia ano-mes na data de hoje -1 mês
	Exemplo: hoje é 01/09/2024 a referencia é 202408, todas as moedas abertas nessa referencia serão fechadas
	'''
	primeiro_dia_mes = datetime.today().day == 8
	if primeiro_dia_mes:
		log_file = f'fechamento_{datetime.now().replace(tzinfo=pytz.utc).strftime("%Y-%m-%d_%H-%M-%S")}.log'
		log_path = os.path.join(BASE_DIR, f'logs/tasks/{log_file}')
		logging.basicConfig(filename=log_path, encoding='utf-8', level=logging.INFO, force=True)
		
		try:
			anomes = int(datetime.today().replace(month=datetime.today().month - 1).strftime('%Y%m'))
			for moeda in Moeda.objects.filter(fechado=False, anomes=anomes):
				moeda.fechado = True
				moeda.save()

			# Fazer o fechamento dos scores de pontualidade
			funcionarios = Funcionario.objects.filter(data_demissao=None).order_by('nome_completo')
			pontos = Ponto.objects.filter(funcionario__in=[i.id for i in funcionarios], data__month=datetime.today().month - 1)
			jornadas = JornadaFuncionario.objects.filter(funcionario__in=[i.id for i in funcionarios])
			_, scores = pontos_funcionarios(pontos, jornadas, True)
			
			for f, s in scores.items():
				for score in Score.objects.filter(fechado=False, anomes=anomes):
					if score.funcionario.nome_completo == f:
						score.pontuacao = s[0]
						score.fechado = True
						score.save()

			for funcionario in funcionarios:
				Score.objects.create(funcionario=funcionario)
			
			logging.info('Fechamento mensal realizado!')

		except Exception as e:
			logging.info(f'Fechamento mensal não foi realizado: {e}')


if __name__ == '__main__':
	fechamento_pontuacoes()
