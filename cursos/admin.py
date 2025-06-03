import sys

from django.contrib import admin

from agenda.admin import FuncionarioForm
from cursos.models import Curso, Etapa, CursoFuncionario, ProgressoEtapa


@admin.register(Curso)
class CursoAdmin(admin.ModelAdmin):
	list_display = ('titulo', 'descricao', 'observacao', 'tipo', 'certificado', 'data_cadastro') # colunas da tabela
	search_fields = ('titulo', 'descricao', 'tipo') # campos de pesquisa aberta
	ordering = ('-data_cadastro',) # ordenção da tabela


@admin.register(Etapa)
class EtapaAdmin(admin.ModelAdmin):
	list_display = ('titulo', 'texto', 'data_cadastro') # colunas da tabela
	search_fields = ('titulo', 'texto') # campos de pesquisa aberta
	ordering = ('titulo',) # ordenção da tabela


@admin.register(CursoFuncionario)
class CursoFuncionarioAdmin(admin.ModelAdmin):
	form = FuncionarioForm
	list_display = ('curso', 'funcionario', 'data_cadastro', 'data_conclusao') # colunas da tabela
	search_fields = ('curso__titulo', 'funcionario__nome_completo') # campos de pesquisa aberta
	ordering = ('-data_conclusao',) # ordenção da tabela
	change_list_template = 'admin/datatables/change_list.html'
	list_per_page = sys.maxsize

	def changelist_view(self, request, extra_context=None):
		if extra_context is None:
			extra_context = dict()
		extra_context['pdf_title'] = 'Crony | Curso por Funcionário'
		return super().changelist_view(request, extra_context=extra_context)


@admin.register(ProgressoEtapa)
class ProgressoEtapaAdmin(admin.ModelAdmin):
	form = FuncionarioForm
	list_display = ('etapa', 'funcionario', 'data_conclusao') # colunas da tabela
	search_fields = ('etapa__titulo', 'funcionario__nome_completo') # campos de pesquisa aberta
	ordering = ('-data_conclusao',) # ordenção da tabela
