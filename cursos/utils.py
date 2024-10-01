from django.utils.timezone import make_aware

from datetime import datetime

from cursos.models import CursoFuncionario


def progressao_cursos_funcionarios(etapas, start, end):
	start = make_aware(datetime.strptime(start, '%Y-%m-%d'))
	end = make_aware(datetime.strptime(end, '%Y-%m-%d'))
	cursos_por_funcionario = {}

	for progresso in etapas:
		funcionario = progresso.funcionario
		cursos_funcionario = CursoFuncionario.objects.filter(funcionario=funcionario, data_cadastro__date__range=[start, end]).values_list('curso', flat=True)
		datas = CursoFuncionario.objects.filter(funcionario=funcionario)
		cursos = progresso.etapa.curso.filter(id__in=cursos_funcionario)

		if funcionario not in cursos_por_funcionario:
			cursos_por_funcionario[funcionario] = {}

		for curso in cursos:
			if curso not in cursos_por_funcionario[funcionario]:
				data = next((i.data_cadastro for i in datas if curso == i.curso), None)
				cursos_por_funcionario[funcionario][curso] = {'data': data, 'etapas': [], 'progresso': 0, 'concluidas': 0}

			if not any(etapa_info['etapa'] == progresso.etapa for etapa_info in cursos_por_funcionario[funcionario][curso]['etapas']):
				status = progresso.data_conclusao is not None
				cursos_por_funcionario[funcionario][curso]['etapas'].append({'etapa': progresso.etapa, 'status': status})

				if status:
					cursos_por_funcionario[funcionario][curso]['concluidas'] += 1

	for funcionario, cursos in cursos_por_funcionario.items():
		for curso, info in cursos.items():
			total_etapas = len(info['etapas'])
			concluidas = info['concluidas']
			info['progresso'] = (concluidas / total_etapas) * 100 if total_etapas > 0 else 0

	return cursos_por_funcionario
