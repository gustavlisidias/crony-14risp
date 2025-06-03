import sys

from django.contrib import admin
from django.utils.html import format_html

from agenda.admin import FuncionarioForm
from web.models import Postagem, Curtida, Comentario, Humor, Ouvidoria, MensagemOuvidoria, Celebracao, Moeda


@admin.register(Postagem)
class PostagemAdmin(admin.ModelAdmin):
	form = FuncionarioForm
	list_display = ('titulo', 'texto', 'data_cadastro') # colunas da tabela
	search_fields = ('titulo', 'texto') # campos de pesquisa aberta
	ordering = ('-data_cadastro',) # ordenção da tabela
	change_list_template = 'admin/datatables/change_list.html'
	list_per_page = sys.maxsize
	
	def changelist_view(self, request, extra_context=None):
		if extra_context is None:
			extra_context = dict()
		extra_context['pdf_title'] = "Crony | Histórico de Postagens"
		return super().changelist_view(request, extra_context=extra_context)


@admin.register(Curtida)
class CurtidaAdmin(admin.ModelAdmin):
	form = FuncionarioForm
	list_display = ('content_type', 'object_id', 'content_object', 'funcionario', 'data_cadastro') # colunas da tabela
	search_fields = ('content_object', 'funcionario__nome_completo') # campos de pesquisa aberta
	ordering = ('-data_cadastro',) # ordenção da tabela


@admin.register(Comentario)
class ComentarioAdmin(admin.ModelAdmin):
	form = FuncionarioForm
	list_display = ('content_type', 'object_id', 'content_object', 'funcionario', 'data_cadastro') # colunas da tabela
	search_fields = ('content_object', 'funcionario__nome_completo') # campos de pesquisa aberta
	ordering = ('-data_cadastro',) # ordenção da tabela


@admin.register(Humor)
class HumorAdmin(admin.ModelAdmin):
	form = FuncionarioForm
	list_display = ('humor', 'funcionario', 'data_cadastro') # colunas da tabela
	search_fields = ('funcionario__nome_completo',) # campos de pesquisa aberta
	ordering = ('-data_cadastro',) # ordenção da tabela
	change_list_template = 'admin/datatables/change_list.html'
	list_per_page = sys.maxsize

	def changelist_view(self, request, extra_context=None):
		if extra_context is None:
			extra_context = dict()
		extra_context['pdf_title'] = "Crony | Humor por Funcionário"
		return super().changelist_view(request, extra_context=extra_context)


@admin.register(Celebracao)
class CelebracaoAdmin(admin.ModelAdmin):
	form = FuncionarioForm
	list_display = ('titulo', 'celebrante', 'data_celebracao') # colunas da tabela
	search_fields = ('titulo', 'texto', 'celebrante__nome_completo') # campos de pesquisa aberta
	ordering = ('-data_celebracao', 'celebrante__nome_completo') # ordenção da tabela


@admin.register(Ouvidoria)
class OuvidoriaAdmin(admin.ModelAdmin):
	
	class MensagemInline(admin.TabularInline):
		model = MensagemOuvidoria
		extra = 0
		fields = ('mensagem_formatada', 'data_cadastro')
		readonly_fields = ('mensagem_formatada', 'data_cadastro')
		can_delete = True

		def mensagem_formatada(self, obj):
			return format_html(obj.mensagem)
		
		mensagem_formatada.short_description = 'Mensagem'

	form = FuncionarioForm
	list_display = ('assunto', 'categoria', 'get_funcionario', 'status', 'anonimo')
	search_fields = ('funcionario__nome_completo', 'assunto', 'descricao')
	ordering = ('-data_cadastro',)
	inlines = [MensagemInline]
	
	def get_readonly_fields(self, request, obj=None):
		if obj and obj.anonimo:
			return ('anonimo',)
		return ('anonimo', 'funcionario')

	def get_exclude(self, request, obj=None):
		if obj and obj.anonimo:
			return ('funcionario', 'descricao')
		return ('descricao',)
	
	def get_funcionario(self, obj):
		return 'Anônimo' if obj.anonimo else obj.funcionario.nome_completo if obj.funcionario else 'Não Informado'
	
	get_funcionario.short_description = 'Funcionário'


@admin.register(Moeda)
class MoedaAdmin(admin.ModelAdmin):
	form = FuncionarioForm
	list_display = ('funcionario', 'pontuacao', 'motivo', 'data_cadastro') # colunas da tabela
	search_fields = ('funcionario__nome_completo', 'motivo') # campos de pesquisa aberta
	ordering = ('-data_cadastro__date', '-pontuacao', 'funcionario__nome_completo') # ordenção da tabela
