from django.contrib import admin

from agenda.admin import FuncionarioForm
from pesquisa.models import Pesquisa, Pergunta, TextoPerguntas, Resposta


@admin.register(Pesquisa)
class PesquisaAdmin(admin.ModelAdmin):
	form = FuncionarioForm
	list_display = ('titulo', 'descricao', 'data_cadastro', 'anonimo') # colunas da tabela
	search_fields = ('funcionarios__nome_completo', 'titulo') # campos de pesquisa aberta
	ordering = ('-data_cadastro',) # ordenção da tabela


@admin.register(Pergunta)
class PerguntaAdmin(admin.ModelAdmin):
	list_display = ('titulo', 'pesquisa', 'tipo', 'obrigatorio', 'data_cadastro') # colunas da tabela
	search_fields = ('titulo', 'tipo') # campos de pesquisa aberta
	ordering = ('-data_cadastro',) # ordenção da tabela


@admin.register(TextoPerguntas)
class TextoPerguntasAdmin(admin.ModelAdmin):
	list_display = ('pergunta', 'texto') # colunas da tabela
	search_fields = ('texto', 'pergunta__titulo') # campos de pesquisa aberta
	ordering = ('pergunta__titulo',) # ordenção da tabela


@admin.register(Resposta)
class RespostaAdmin(admin.ModelAdmin):
	form = FuncionarioForm
	list_display = ('texto', 'pergunta', 'funcionario') # colunas da tabela
	search_fields = ('texto', 'funcionario__nome_completo') # campos de pesquisa aberta
	ordering = ('-data_cadastro',) # ordenção da tabela
