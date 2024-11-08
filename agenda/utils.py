from datetime import datetime, timedelta, date
from dateutil.relativedelta import relativedelta

from agenda.models import Ferias
from web.utils import add_years, parse_employee, not_none_not_empty


def ferias_funcionarios(funcionarios):
	funcionarios = parse_employee(funcionarios)

	if not funcionarios:
		return None
	
	ferias_por_funcionario = {}

	for funcionario in funcionarios:

		if funcionario.nome_completo not in ferias_por_funcionario:
			ferias_por_funcionario[funcionario.nome_completo] = []

		if funcionario.get_contrato.slug.split('-')[0] == 'estagio':
			# Funcionario Estágio tem direito a 15 dias após 6 meses trabalhados
			# Empresa tem mais 6 meses para liberar as ferias, porém não pode ultrapassar o limite de 1 ano consecutivos de trabalho do funcionario

			# Exemplo: contratação em 01/03/2023, primeiro período de 01/09/2023 até 29/02/2023

			if not_none_not_empty(funcionario.data_inicio_ferias):
				inicio_periodo = funcionario.data_inicio_ferias + relativedelta(months=6)
			else:
				inicio_periodo = funcionario.data_contratacao + relativedelta(months=6)

			while inicio_periodo <= date.today():
				periodo = (inicio_periodo - relativedelta(months=6)).year
				final_periodo = inicio_periodo + timedelta(days=179)

				saldo = timedelta(days=15)
				status = False
				ferias = Ferias.objects.filter(funcionario=funcionario, ano_referencia=periodo)

				if ferias:
					for obj in ferias:
						saldo -= (obj.final_ferias - obj.inicio_ferias) + timedelta(days=obj.abono)

					if saldo.days <= 0:
						status = True
				
				ferias_por_funcionario[funcionario.nome_completo].append({
					'periodo': periodo,
					'status': status,
					'saldo': saldo,
					'inicio': inicio_periodo,
					'vencimento': final_periodo,
				})
				
				inicio_periodo += relativedelta(months=6)

		else:
			# Funcionario CLT tem direito a 30 dias após 1 ano trabalhado
			# Empresa tem mais 1 ano para liberar as ferias, porém não pode ultrapassar o limite de 2 anos consecutivos de trabalho do funcionario
			
			# Consulto se houve ferias no periodo calculado
			# Se houve, calculo o saldo
			# Se o saldo foi quitado o status é definido como True

			# Exemplo: contratação em 20/12/1994, primeiro período de 20/12/1995 até 19/11/1996

			if not_none_not_empty(funcionario.data_inicio_ferias):
				ano_inicio = funcionario.data_inicio_ferias.year
			else:
				ano_inicio = funcionario.data_contratacao.year

			for ano in range(ano_inicio, datetime.now().year + 1):
				inicio_periodo = add_years(funcionario.data_contratacao.replace(year=ano), 1)
				final_periodo = add_years(funcionario.data_contratacao.replace(year=ano), 2) - timedelta(days=31)

				saldo = timedelta(days=30)
				status = False
				ferias = Ferias.objects.filter(funcionario=funcionario, ano_referencia=ano)

				if ferias:
					for obj in ferias:
						saldo -= (obj.final_ferias - obj.inicio_ferias) + timedelta(days=obj.abono)

					if saldo.days <= 0:
						status = True

				ferias_por_funcionario[funcionario.nome_completo].append({
					'periodo': ano,
					'status': status,
					'saldo': saldo,
					'inicio': inicio_periodo,
					'vencimento': final_periodo,
				})

	return ferias_por_funcionario
