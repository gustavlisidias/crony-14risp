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

from django.core.mail import EmailMessage

from datetime import datetime, timedelta

from settings.settings import BASE_DIR, EMAIL_HOST_USER
from web.models import Humor


def relatorio_semanal():
	log_file = f'humores_{datetime.now().replace(tzinfo=pytz.utc).strftime("%Y-%m-%d_%H-%M-%S")}.log'
	log_path = os.path.join(BASE_DIR, f'logs/tasks/{log_file}')
	logging.basicConfig(filename=log_path, encoding='utf-8', level=logging.INFO, force=True)

	inicio = (datetime.now() - timedelta(days=7)).date()
	final = (datetime.now() - timedelta(days=1)).date()

	try:
		humores = Humor.objects.filter(data_cadastro__date__range=[inicio, final])

		total_feliz = humores.filter(humor='5').count()
		total_alegre = humores.filter(humor='4').count()
		total_neutro = humores.filter(humor='3').count()
		total_triste = humores.filter(humor='2').count()
		total_deprimido = humores.filter(humor='1').count()
		media = sum(int(i.humor) for i in humores) / len(humores)

		subject = 'Relatório Semanal de Humores - Crony'
		message = f'Na semana de {inicio.strftime("%d/%m/%Y")} até {final.strftime("%d/%m/%Y")} houve {len(humores)} humores enviados com uma média de {media}\n\nTotal Feliz: {total_feliz}\nTotal Alegre: {total_alegre}\nTotal Neutro: {total_neutro}\nTotal Triste: {total_triste}\nTotal Deprimido: {total_deprimido}'
		destinatarios = ['ronilda@14ri.com.br',]
		email = EmailMessage(subject, message, EMAIL_HOST_USER, destinatarios)
		email.send()

		logging.info('Relatorio semanal enviado com sucesso!')

	except Exception as e:
		logging.info(f'Relatorio semanal não foi realizado: {e}')


if __name__ == '__main__':
	relatorio_semanal()
