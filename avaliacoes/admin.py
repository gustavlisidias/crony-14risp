from django.contrib import admin

from agenda.admin import FuncionarioForm
from avaliacoes.models import Avaliacao, Nivel, Pergunta, Resposta, PerguntaAvaliacao


@admin.register(Avaliacao)
class AvaliacaoAdmin(admin.ModelAdmin):
	form = FuncionarioForm
	list_display = ('titulo', 'inicio', 'final', 'avaliado', 'status', 'data_encerramento', 'data_cadastro') # colunas da tabela
	search_fields = ('titulo', 'avaliado__nome_completo', 'descricao') # campos de pesquisa aberta
	ordering = ('-data_cadastro',) # ordenção da tabela


@admin.register(Nivel)
class NivelAdmin(admin.ModelAdmin):
	list_display = ('tipo', 'avaliacao', 'peso') # colunas da tabela
	search_fields = ('avaliacao__titulo', 'tipo') # campos de pesquisa aberta
	ordering = ('tipo',) # ordenção da tabela


@admin.register(Pergunta)
class PerguntaAdmin(admin.ModelAdmin):
	list_display = ('titulo', 'texto', 'peso') # colunas da tabela
	search_fields = ('titulo', 'texto') # campos de pesquisa aberta
	ordering = ('titulo',) # ordenção da tabela


@admin.register(PerguntaAvaliacao)
class PerguntaAvaliacaoAdmin(admin.ModelAdmin):
	form = FuncionarioForm
	list_display = ('pergunta', 'avaliacao', 'data_cadastro') # colunas da tabela
	search_fields = ('pergunta__titulo', 'avaliacao__titulo') # campos de pesquisa aberta
	ordering = ('-data_cadastro',) # ordenção da tabela


@admin.register(Resposta)
class RespostaAdmin(admin.ModelAdmin):
	form = FuncionarioForm
	list_display = ('referencia', 'funcionario', 'nota') # colunas da tabela
	search_fields = ('referencia__pergunta__titulo', 'referencia__avaliacao__titulo', 'funcionario__nome_completo') # campos de pesquisa aberta
	ordering = ('referencia__avaliacao__id', 'funcionario__nome_completo') # ordenção da tabela
