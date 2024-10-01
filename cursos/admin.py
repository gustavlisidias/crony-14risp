from django.contrib import admin

from cursos.models import Curso, Etapa, CursoFuncionario


admin.site.register(Curso)
admin.site.register(Etapa)
admin.site.register(CursoFuncionario)
