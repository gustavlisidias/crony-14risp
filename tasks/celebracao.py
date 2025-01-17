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

from datetime import date, datetime

from django.db.models import Case, CharField, Q, Value, When

from funcionarios.models import Funcionario
from notifications.signals import notify
from settings.settings import BASE_DIR
from web.models import Celebracao


def create_celebrations():
	log_file = f'celebracao_{datetime.now().replace(tzinfo=pytz.utc).strftime("%Y-%m-%d_%H-%M-%S")}.log'
	log_path = os.path.join(BASE_DIR, f'logs/tasks/{log_file}')
	logging.basicConfig(filename=log_path, encoding='utf-8', level=logging.INFO, force=True)

	hoje = date.today()

	funcionarios = Funcionario.objects.filter(data_demissao=None).order_by('nome_completo')
	celebracoes = funcionarios.filter(Q(data_nascimento__month=hoje.month, data_nascimento__day=hoje.day) | Q(data_contratacao__month=hoje.month, data_contratacao__day=hoje.day)).annotate(
		celebracao=Case(
			When(Q(data_nascimento__month=hoje.month, data_nascimento__day=hoje.day), then=Value('aniversario')),
			When(Q(data_contratacao__month=hoje.month, data_contratacao__day=hoje.day), then=Value('tempo_de_empresa')),
			output_field=CharField(),
		)
	)

	if celebracoes:
		for funcionario in celebracoes:
			if funcionario.celebracao == 'aniversario':
				texto = f'''Hoje temos um aniversariante na empresa. Nada melhor que celebrar com ele(a), não é mesmo?
				Vamos dar parabéns para {funcionario.get_tag}! Ficamos muito felizes que você decidiu passar esta data tão especial conosco!
				Feliz aniversário!'''
				nova_celebracao = Celebracao.objects.create(
					titulo='Aniversário',
					texto=texto,
					celebrante=funcionario,
					data_celebracao=hoje
				)

			else:
				texto = f'{funcionario.get_tag} completa hoje mais um ano na nossa empresa. Vamos comemorar com ele(a)??'
				nova_celebracao = Celebracao.objects.create(
					titulo='Tempo de Empresa',
					texto=texto,
					celebrante=funcionario,
					data_celebracao=hoje
				)

			notify.send(
				sender=Funcionario.objects.get(pk=1).usuario,
				recipient=funcionario.usuario,
				verb='Você foi marcado em uma nova celebração!'
			)

			if nova_celebracao:
				nova_celebracao.funcionario.set([i.id for i in funcionarios])
				nova_celebracao.save()
				logging.info(f'Nova celebração salva: {nova_celebracao.titulo} de {nova_celebracao.celebrante}')
	
	else:
		logging.info(f'Sem celebrações no dia {hoje}')


if __name__ == '__main__':
	create_celebrations()
