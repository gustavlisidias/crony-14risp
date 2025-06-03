from django.apps import apps
from django.contrib.admin.models import LogEntry, ADDITION, CHANGE, DELETION
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import MultipleObjectsReturned, ObjectDoesNotExist
from django.db import models
from django.db.models.query import QuerySet
from django.shortcuts import get_object_or_404
from django.utils import timezone

from datetime import datetime, date, time
from typing import Type, Literal

from configuracoes.models import Usuario


def not_none_not_empty(*args):
	for arg in args:
		if isinstance(arg, list) and not arg:
			return False
		if arg in (None, ""):
			return False
	return True


def add_years(d, years):
	try:
		return d.replace(year=d.year + years)
	except ValueError:
		return d + (date(d.year + years, 1, 1) - date(d.year, 1, 1))
	  

def add_coins(funcionario, value, motivo):
	model = apps.get_model('web', 'Moeda')

	try:
		moeda = model.objects.create(funcionario=funcionario, pontuacao=value, motivo=motivo)

		create_log(
			object_model=model,
			object_id=moeda.id,
			user=moeda.funcionario.usuario,
			message=f'Moeda adicionada (+{value}) - {motivo}',
			action=1
		)

	except MultipleObjectsReturned:
		model.objects.filter(fechado=False, funcionario=funcionario, data_cadastro__month=timezone.now().month).update(fechado=True)
		model.objects.create(
			funcionario=funcionario,
			pontuacao=value,
			fechado=False
		)

	except ObjectDoesNotExist:
		model.objects.create(
			funcionario=funcionario,
			pontuacao=value,
			fechado=False
		)
	
	except Exception as e:
		print(f'\n\nErro ao adicionar moedas: {e}\n\n')
	

def create_log(
	object_model: Type[models.Model],
	object_id: int,
	user: Usuario,
	message: str,
	action: Literal[1, 2, 3]
) -> LogEntry:
	
	ACTION_MAP = {
		1: ADDITION,
		2: CHANGE,
		3: DELETION,
	}

	obj = get_object_or_404(object_model, pk=object_id)
	content_type = ContentType.objects.get_for_model(object_model)

	object_log = LogEntry.objects.create(
		user=user,
		content_type=content_type,
		object_id=obj.pk,
		object_repr=str(obj),
		action_flag=ACTION_MAP[action],
		change_message=message
	)

	return object_log


def parse_date(data):
	try:
		if isinstance(data, str):
			if '-' in data:
				try:
					return datetime.strptime(data, '%Y-%m-%d')
				except Exception:
					return datetime.strptime(data, '%d-%m-%Y')
			if '/' in data:
				return datetime.strptime(data, '%d/%m/%Y')
		elif isinstance(data, datetime):
			return data
		elif isinstance(data, date):
			return datetime.combine(data, datetime.min.time())
		elif isinstance(data, time):
			return datetime.combine(datetime.min.date(), data)
		else:
			return None
	except Exception:
		return None
	

def parse_employee(objeto):
	from funcionarios.models import Funcionario
	try:
		if objeto is None:
			return None
		elif isinstance(objeto, list):
			return Funcionario.objects.filter(pk__in=objeto)
		elif isinstance(objeto, QuerySet):
			return objeto
		else:
			return Funcionario.objects.filter(pk=objeto.pk)
	except Exception:
		return None


def get_object_or_none(model, **kwargs):
	try:
		return model.objects.get(**kwargs)
	except ObjectDoesNotExist:
		return None
