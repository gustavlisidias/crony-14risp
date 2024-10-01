from django.urls import path

from cursos.ajax import ConcluirEtapaView
from cursos.views import CursoView, ProgressoCursoView, AtribuirCursoView


urlpatterns = [
	path('cursos', CursoView, name='cursos'),
	path('cursos/progresso/curso/<int:course>/funcionario/<int:func>', ProgressoCursoView, name='progresso-curso'),
	path('cursos/atribuir/curso/<int:course>', AtribuirCursoView, name='atribuir-curso'),
	path('cursos/concluir/etapa/<int:etapa>', ConcluirEtapaView, name='concluir-etapa'),
]
