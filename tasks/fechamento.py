# ruff: noqa: E402
import logging
import os
import sys
import calendar

import django
import pytz

from pathlib import Path
from dotenv import load_dotenv
from collections import defaultdict

load_dotenv(os.path.join(Path(__file__).resolve().parent.parent, '.env'))
sys.path.append(os.getenv('SYSTEM_PATH'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'settings.settings')
django.setup()

from datetime import date, datetime, time

from funcionarios.models import Funcionario, Score
from ponto.models import Fechamento
from ponto.utils import pontos_por_dia
from settings.settings import BASE_DIR
from web.models import Moeda


def fechamento_pontuacoes():
	hoje = date.today()

	if hoje.day == 1:
		log_file = f'fechamento_{datetime.now().replace(tzinfo=pytz.utc).strftime("%Y-%m-%d_%H-%M-%S")}.log'
		log_path = os.path.join(BASE_DIR, f'logs/tasks/{log_file}')
		logging.basicConfig(filename=log_path, encoding='utf-8', level=logging.INFO, force=True)
		
		try:
			mes = hoje.month - 1 if hoje.month > 1 else 12
			ano = hoje.year if hoje.month > 1 else hoje.year - 1
			ultimo_dia = calendar.monthrange(hoje.year, hoje.month - 1)[1] if hoje.month > 1 else 31

			data_inicial = datetime.combine(date(ano, mes, 1), time())
			data_final = datetime.combine(date(ano, mes, ultimo_dia), time())

			funcionarios = Funcionario.objects.filter(data_demissao=None).order_by('nome_completo')
			_, scores = pontos_por_dia(data_inicial, data_final, funcionarios, True)

			# Salvo todas as médias do período, para cada funcionário
			for funcid, score in scores.items():
				funcionario = Funcionario.objects.get(pk=funcid)
				pontuacao = score['media']
				Score.objects.create(funcionario=funcionario, pontuacao=pontuacao, data_cadastro=data_final)

			# Crio objeto com o total de moeda/pontuacao por funcionario nesse periodo de fechamento
			moedas, pontuacoes = defaultdict(lambda: defaultdict(int)), defaultdict(lambda: defaultdict(int))

			for moeda in Moeda.objects.filter(data_cadastro__date__month=mes, data_cadastro__date__year=ano).order_by('-pontuacao'):
				referencia = moeda.data_cadastro.strftime('%Y%m')
				moedas[moeda.funcionario][referencia] += moeda.pontuacao

			for pontuacao in Score.objects.filter(data_cadastro__date__month=mes, data_cadastro__date__year=ano).order_by('-pontuacao'):
				referencia = pontuacao.data_cadastro.strftime('%Y%m')
				pontuacoes[pontuacao.funcionario][referencia] += pontuacao.pontuacao

			for funcionario, referencias in pontuacoes.items():
				for referencia, pontuacao in referencias.items():
					qtd_registros = Score.objects.filter(funcionario=funcionario, data_cadastro__date__month=mes, data_cadastro__date__year=ano).count()
					pontuacoes[funcionario][referencia] = pontuacoes[funcionario][referencia] / qtd_registros if qtd_registros else 0

			# Para cada funcionario, verifico a referencia dos objetos criados e salvo o fechamento
			referencia = f'{ano}{mes:02}'
			for funcionario in funcionarios:
				# print(referencia, funcionario, pontuacoes[funcionario].get(referencia, 1), moedas[funcionario].get(referencia, 1))
					
				fechamento = Fechamento.objects.create(
					funcionario=funcionario,
					pontuacao=pontuacoes[funcionario].get(referencia, 1),
					moedas=moedas[funcionario].get(referencia, 1),
					referencia=referencia
				)

				logging.info(f'Funcionario: {fechamento.funcionario.nome_completo} - Ref: {fechamento.referencia} - Pontuacao: {fechamento.pontuacao} - Moeda {fechamento.moedas}')
			
			logging.info('Fechamento mensal realizado!')

		except Exception as e:
			logging.info(f'Fechamento mensal não foi realizado: {e}')


if __name__ == '__main__':
	fechamento_pontuacoes()
