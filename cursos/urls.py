from django.urls import path

from cursos.ajax import ConcluirEtapaView, ConsultarCursoView
from cursos.views import CursoView, ProgressoCursoView, AtribuirCursoView, EditarCursoView


urlpatterns = [
	path('cursos', CursoView, name='cursos'),
	path('cursos/progresso/curso/<int:course>/funcionario/<int:func>', ProgressoCursoView, name='progresso-curso'),
	path('cursos/atribuir/curso/<int:course>', AtribuirCursoView, name='atribuir-curso'),
	path('cursos/concluir/curso/<int:course>/etapa/<int:etapa>', ConcluirEtapaView, name='concluir-etapa'),
	path('cursos/consultar/<int:course>', ConsultarCursoView, name='consultar-curso'),
	path('cursos/editar/<int:course>', EditarCursoView, name='editar-curso'),
]
