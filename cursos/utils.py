from django.utils.timezone import make_aware

from datetime import datetime
from collections import defaultdict

from cursos.models import CursoFuncionario
from web.decorators import record_time  # noqa: F401


# 2025-05-19 12:36:34.938 [runserver | INFO] progressao_cursos_funcionarios run time: 3.203 seconds
# @record_time
def progressao_cursos_funcionarios(etapas, start, end):
	start = make_aware(datetime.strptime(start, '%Y-%m-%d'))
	end = make_aware(datetime.strptime(end, '%Y-%m-%d'))

	cf_dict = defaultdict(list)

	for cf in CursoFuncionario.objects.filter(data_cadastro__date__range=[start, end], funcionario__in=[e.funcionario for e in etapas]):
		cf_dict[cf.funcionario].append(cf)

	cursos_por_funcionario = dict()

	for progresso in etapas:
		funcionario = progresso.funcionario

		if funcionario not in cursos_por_funcionario:
			cursos_por_funcionario[funcionario] = dict()

		cursos = progresso.etapa.curso.filter(id__in=[i.curso.id for i in cf_dict.get(funcionario, list())])

		for curso in cursos:
			if curso not in cursos_por_funcionario[funcionario]:
				cf_match = next((i for i in cf_dict[funcionario] if cf.curso == curso), None)
				data_cadastro_curso_funcionario = cf_match.data_cadastro if cf_match else None
				cursos_por_funcionario[funcionario][curso] = {'data_cadastro': data_cadastro_curso_funcionario, 'etapas': list(), 'progresso': 0, 'concluidas': 0}

			etapa_info = cursos_por_funcionario[funcionario][curso]['etapas']

			if not any(e['etapa'] == progresso.etapa for e in etapa_info):
				status = progresso.data_conclusao is not None
				etapa_info.append({'etapa': progresso.etapa, 'status': status})

				if status:
					cursos_por_funcionario[funcionario][curso]['concluidas'] += 1

	for cursos in cursos_por_funcionario.values():
		for info in cursos.values():
			total_etapas = len(info['etapas'])
			concluidas = info['concluidas']
			info['progresso'] = (concluidas / total_etapas) * 100 if total_etapas > 0 else 0

	return cursos_por_funcionario
