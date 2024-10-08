import datetime

from django import template
from configuracoes.models import Jornada
from funcionarios.models import Funcionario, Perfil


register = template.Library()


@register.filter
def value_to_integer(value):
	try:
		if isinstance(value, list):
			return [int(i) for i in value]
		else:
			return int(value)
	except Exception:
		return 0


@register.filter
def photo(value, url=None):
	try:
		funcionario = Funcionario.objects.get(pk=int(value))
		foto = Perfil.objects.get(funcionario=funcionario).foto
		if url:
			return foto.url if foto else '/static/images/avatar.jpg'
		else:
			return foto
		
	except Exception:
		return None


@register.filter
def theme(value):
	try:
		funcionario = Funcionario.objects.get(pk=int(value))
		tema = Perfil.objects.get(funcionario=funcionario).tema
		return tema
		
	except Exception:
		return 'light'


@register.filter
def index(sequence, position):
	try:
		index = sequence[position]
		if index != datetime.time(0) and index != datetime.time(23, 59):
			return index
		else:
			return None
	except IndexError:
		return None


@register.filter
def weekday(value):	
	if value:
		weekday = 1 if value == 8 else value
		dia_semana = [i[1] for i in Jornada.Semana.choices if i[0] == int(weekday)][0]
		return dia_semana
	else:
		return None
	

@register.filter
def timedelta(value):
	if value.days < 0:
		total = datetime.timedelta(seconds=86400) - value
		horas = total.seconds // 3600
		minutos = (total.seconds // 60) % 60
		formatted_time = '{:02}h {:02}m -'.format(horas, minutos)
	else:
		horas = value.seconds // 3600 + value.days * 24
		minutos = (value.seconds // 60) % 60
		formatted_time = '{:02}h {:02}m'.format(horas, minutos)

	return formatted_time


@register.filter
def sincedelta(value):
	if isinstance(value, datetime.timedelta):
		days = value.days
		seconds = value.seconds
		if days == 1:
			return '1 dia atrás'
		elif days > 1:
			return f'{days} dias atrás'
		elif days == 0:
			if seconds >= 3600:
				return f'{round(seconds / 3600)} horas atrás'
			elif seconds >= 60:
				return f'{round(seconds / 60)} minutos atrás'
			else:
				return f'{seconds} segundos atrás'
	return 'hoje'


@register.filter
def floatdelta(value):
	if isinstance(value, datetime.timedelta):
		if value.days < 0:
			total = datetime.timedelta(seconds=86400) - value
			formatted_time = total.seconds / 3600 * -1
		else:
			formatted_time = value.seconds / 3600
		
		return formatted_time
	else:
		return ''
	

@register.filter
def absolute_days(value):
	return abs(value.days)


@register.filter
def item_from_dict(dictionary, key):
	return dict(dictionary).get(key)


@register.filter
def value_to_string(value):
	return str(value)


@register.filter
def replace(value, args):
	value1, value2 = args.split(', ')
	old_value = value1.encode().decode('unicode_escape')
	new_value = value2.encode().decode('unicode_escape')
	return value.replace(old_value, new_value)


@register.filter
def query_to_list(query, key):
	return list(query.values_list(key, flat=True))


@register.filter
def even(value):
	return True if (value % 2) == 0 else False


@register.filter
def is_today(value):
	return True if datetime.datetime.strptime(value, '%Y-%m-%d').date() == datetime.date.today() else False


@register.filter
def soma(obj, value):
	soma = round(float(obj) + float(value), 2)
	return soma


@register.filter
def filter_range(obj, value):
	if isinstance(obj, list):
		return obj[:value]
	else:
		return obj
