# ruff: noqa: E402
import logging
import os
import sys

import django
import pytz

sys.path.append('C:\inetpub\wwwroot\crony')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'settings.settings')
django.setup()

from datetime import date, datetime

from funcionarios.models import JornadaFuncionario
from ponto.models import Feriados, Ponto
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
				for funcionario in feriado.funcionarios.all():
					jornada_funcionario = JornadaFuncionario.objects.filter(funcionario=funcionario, final_vigencia=None, dia=weekday).order_by('funcionario__id', 'dia', 'ordem')

					for horario in jornada_funcionario:
						Ponto(
							funcionario=funcionario,
							data=hoje,
							hora=horario.hora,
							motivo=feriado.titulo,
							alterado=True,
							encerrado=True
						).save()

			except Exception as e:
				logging.info(f'Ocorreu um erro ao abonar o feriado {feriado.titulo}: {e}')
				
	else:
		logging.info(f'Nenhum feriado encontrado no dia {hoje}')


if __name__ == '__main__':
	abonar_feriados()
