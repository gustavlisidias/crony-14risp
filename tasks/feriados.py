# ruff: noqa: E402
import logging
import os
import sys

import django
import pytz

from pathlib import Path
from dotenv import load_dotenv

load_dotenv(os.path.join(Path(__file__).resolve().parent.parent, '.env'))
sys.path.append(os.getenv('SYSTEM_PATH'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'settings.settings')
django.setup()

from django.db import transaction

from datetime import date, datetime, time, timedelta

from funcionarios.models import Funcionario, JornadaFuncionario
from ponto.models import Feriados, Ponto, Saldos
from ponto.utils import total_saldo
from settings.settings import BASE_DIR


def abonar_feriados():
	log_file = f'feriados_{datetime.now().replace(tzinfo=pytz.utc).strftime("%Y-%m-%d_%H-%M-%S")}.log'
	log_path = os.path.join(BASE_DIR, f'logs/tasks/{log_file}')
	logging.basicConfig(filename=log_path, encoding='utf-8', level=logging.INFO, force=True)

	ontem = date.today() - timedelta(1)
	weekday = 1 if ontem.weekday() + 2 == 8 else ontem.weekday() + 2
	feriados = Feriados.objects.filter(data=ontem)

	if feriados:
		for feriado in feriados:
			try:
				if feriado.regiao == Feriados.Regiao.NACIONAL:
					funcionarios = Funcionario.objects.filter(data_demissao=None)
				elif feriado.regiao == Feriados.Regiao.ESTADUAL:
					funcionarios = Funcionario.objects.filter(data_demissao=None, estado=feriado.estado)
				else:
					funcionarios = Funcionario.objects.filter(data_demissao=None, estado=feriado.estado, cidade=feriado.cidade)
					
				with transaction.atomic():				
					for funcionario in funcionarios:
						ponto_funcionario = Ponto.objects.filter(funcionario=funcionario, data=ontem)

						jornada_funcionario = JornadaFuncionario.objects.filter(
							funcionario=funcionario, final_vigencia=None, dia=weekday
						).order_by('agrupador', 'dia', 'ordem').values_list('hora', flat=True)

						saldo = total_saldo(jornada_funcionario)

						if ponto_funcionario.exists():
							ponto_funcionario.update(
								motivo=feriado.titulo,
								alterado=True,
								autor_modificacao=Funcionario.objects.get(pk=1)
							)
						else:
							Ponto(
								funcionario=funcionario,
								data=ontem,
								hora=time(),
								motivo=feriado.titulo,
								alterado=True,
								autor_modificacao=Funcionario.objects.get(pk=1)
							).save()

						Saldos(
							funcionario=funcionario,
							saldo=saldo,
							data=ontem
						).save()

					logging.info(f'Feriado {feriado.titulo} rodou o saldo com sucesso para {len(funcionarios)} funcionários')

			except Exception as e:
				logging.info(f'Ocorreu um erro ao abonar o feriado {feriado.titulo}: {e}')
				
	else:
		logging.info(f'Nenhum feriado encontrado no dia {ontem}')


if __name__ == '__main__':
	abonar_feriados()
