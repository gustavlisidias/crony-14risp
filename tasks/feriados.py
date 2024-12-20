# ruff: noqa: E402
import logging
import os
import sys

import django
import pytz

sys.path.append('C:\inetpub\wwwroot\crony')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'settings.settings')
django.setup()

from django.db import transaction

from datetime import date, datetime, time

from funcionarios.models import JornadaFuncionario
from ponto.models import Feriados, Ponto, Saldos
from ponto.utils import total_saldo
from settings.settings import BASE_DIR


def abonar_feriados():
	log_file = f'feriados_{datetime.now().replace(tzinfo=pytz.utc).strftime("%Y-%m-%d_%H-%M-%S")}.log'
	log_path = os.path.join(BASE_DIR, f'logs/tasks/{log_file}')
	logging.basicConfig(filename=log_path, encoding='utf-8', level=logging.INFO, force=True)

	hoje = date.today()
	weekday = 1 if hoje.weekday() + 2 == 8 else hoje.weekday() + 2
	feriados = Feriados.objects.filter(data=hoje)

	if feriados:
		for feriado in feriados:
			try:
				with transaction.atomic():
					for funcionario in feriado.funcionarios.all():
						ponto_funcionario = Ponto.objects.filter(funcionario=funcionario, data=feriado.data).exists()

						jornada_funcionario = JornadaFuncionario.objects.filter(
							funcionario=funcionario, final_vigencia=None, dia=weekday
						).order_by('agrupador', 'dia', 'ordem').values_list('hora', flat=True)

						saldo = total_saldo(jornada_funcionario)

						if not ponto_funcionario:
							Ponto(
								funcionario=funcionario,
								data=hoje,
								hora=time(0),
								motivo=feriado.titulo,
								alterado=True,
								encerrado=True
							).save()

						Saldos(
							funcionario=funcionario,
							saldo=saldo,
							data=hoje
						).save()

					logging.info(f'Feriado {feriado.titulo} rodou o saldo com sucesso para {len(feriado.funcionarios.all())} funcionários')

			except Exception as e:
				logging.info(f'Ocorreu um erro ao abonar o feriado {feriado.titulo}: {e}')
				
	else:
		logging.info(f'Nenhum feriado encontrado no dia {hoje}')


if __name__ == '__main__':
	abonar_feriados()
