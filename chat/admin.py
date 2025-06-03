# ruff: noqa: F401
from django import forms
from django.contrib import admin
from django.contrib.admin import SimpleListFilter
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from datetime import datetime, timedelta

from agenda.admin import FuncionarioForm
from chat.models import Sala, Mensagem, Arquivo
from funcionarios.models import Funcionario


class MensagemDataCadastroFilter(SimpleListFilter):
	title = _('Data das Mensagens')
	parameter_name = 'mensagem_data'

	def lookups(self, request, model_admin):
		return [
			('today', _('Hoje')),
			('last_3_days', _('Últimos 3 dias')),
			('last_7_days', _('Últimos 7 dias')),
			('this_month', _('Este mês')),
			('last_month', _('Último mês')),
		]

	def queryset(self, request, queryset):
		if self.value():
			now = datetime.now()
			if self.value() == 'today':
				start_date = now.replace(hour=0, minute=0, second=0)
			elif self.value() == 'last_3_days':
				start_date = now - timedelta(days=3)
			elif self.value() == 'last_7_days':
				start_date = now - timedelta(days=7)
			elif self.value() == 'this_month':
				start_date = now.replace(day=1)
			elif self.value() == 'last_month':
				start_date = now.replace(month=now.month - 1 if now.month > 1 else 12)
			else:
				return queryset

			return queryset.filter(mensagens_sala__data_cadastro__gte=start_date).distinct()

		return queryset


class MensagemInline(admin.TabularInline):
	model = Mensagem
	extra = 0
	fields = ('mensagem_formatada', 'lido', 'data_cadastro')
	readonly_fields = ('mensagem_formatada', 'lido', 'data_cadastro')
	can_delete = True

	def mensagem_formatada(self, obj):
		return format_html(obj.mensagem)

	def get_queryset(self, request):
		qs = super().get_queryset(request)
		
		sala_id = request.resolver_match.kwargs.get('object_id')
		if not sala_id:
			return qs.none()
		
		data_inicio = request.GET.get('data_inicio')
		data_fim = request.GET.get('data_fim')

		if data_inicio and data_fim:
			return qs.filter(sala_id=sala_id, data_cadastro__date__range=[data_inicio, data_fim])
		
		return qs


class ArquivoInline(admin.TabularInline):
	model = Arquivo
	extra = 0
	fields = ('arquivo', 'lido', 'data_cadastro')
	readonly_fields = ('arquivo', 'lido', 'data_cadastro')
	can_delete = True

	def get_queryset(self, request):
		qs = super().get_queryset(request)
		
		sala_id = request.resolver_match.kwargs.get('object_id')
		if not sala_id:
			return qs.none()
		
		data_inicio = request.GET.get('data_inicio')
		data_fim = request.GET.get('data_fim')

		if data_inicio and data_fim:
			return qs.filter(sala_id=sala_id, data_cadastro__date__range=[data_inicio, data_fim])
		
		return qs


@admin.register(Sala)
class SalaAdmin(admin.ModelAdmin):
	form = FuncionarioForm
	list_display = ('uuid', 'tipo', 'data_cadastro', 'funcionarios_list', 'quantidade_mensagens')
	search_fields = ('uuid', 'nome', 'funcionarios__nome_completo')
	list_filter = ('tipo', 'data_cadastro', MensagemDataCadastroFilter)
	ordering = ('-data_modificacao',)
	inlines = [MensagemInline, ArquivoInline]
	change_form_template = 'admin/mensagem/change_form.html'
	
	def funcionarios_list(self, obj):
		return ', '.join([f.nome_completo for f in obj.funcionarios.all()])
	
	def quantidade_mensagens(self, obj):
		'''Exibe a quantidade de mensagens na sala.'''
		return obj.mensagens_sala.count()
	
	funcionarios_list.short_description = 'Participantes'
	quantidade_mensagens.short_description = 'Qtd Mensagens'
