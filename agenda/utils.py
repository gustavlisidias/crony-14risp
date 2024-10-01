from datetime import datetime, timedelta
from slugify import slugify

from agenda.models import Ferias
from web.utils import add_years


def ferias_funcionarios(funcionarios):
	ferias_por_funcionario = {}

	for funcionario in funcionarios:
		contrato_funcionario = funcionario.get_contrato.titulo.lower().split('_')[0]

		if funcionario.nome_completo not in ferias_por_funcionario:
			ferias_por_funcionario[funcionario.nome_completo] = []

		if slugify(contrato_funcionario) == 'estagio':
			delta = datetime.today().date() - funcionario.data_contratacao
			intervalos = delta.days // 180

			periodo = 6
			inicio = funcionario.data_contratacao + timedelta(days=180)
			while True:
				vencimento = inicio + timedelta(days=180 - 16)
				saldo = timedelta(days=15)
				status = False
				ferias = Ferias.objects.filter(funcionario=funcionario, inicio__gte=inicio, inicio__lte=vencimento)

				if ferias:
					for obj in ferias:
						saldo -= (obj.final - obj.inicio) + timedelta(days=obj.abono)

					if saldo.days <= 0:
						status = True

				ferias_por_funcionario[funcionario.nome_completo].append({
					'periodo': periodo,
					'status': status,
					'saldo': saldo,
					'inicio': inicio,
					'vencimento': vencimento,
				})

				intervalos -= 1
				periodo += 6
				inicio = vencimento + timedelta(days=16)

				if intervalos <= 0:
					break			

		else:
			for ano in range(funcionario.data_contratacao.year, datetime.now().year + 1):
				# funcionario tem direito a 30 dias após 1 ano trabalhado
				inicio = add_years(funcionario.data_contratacao.replace(year=ano), 1)
				# empresa tem mais 1 ano para liberar as ferias, porém não pode ultrapassar o limite de 2 anos consecutivos de trabalho do funcionario
				vencimento = add_years(funcionario.data_contratacao.replace(year=ano), 2) - timedelta(days=31)

				# Consulto se houve ferias no periodo calculado
				# Se houve, calculo o saldo
				# Se o saldo foi quitado o status é definido como True
				saldo = timedelta(days=30)
				status = False
				ferias = Ferias.objects.filter(funcionario=funcionario, inicio__gte=inicio, inicio__lte=vencimento)

				if ferias:
					for obj in ferias:
						saldo -= (obj.final - obj.inicio) + timedelta(days=obj.abono)

					if saldo.days <= 0:
						status = True

				ferias_por_funcionario[funcionario.nome_completo].append({
					'periodo': ano,
					'status': status,
					'saldo': saldo,
					'inicio': inicio,
					'vencimento': vencimento,
				})

	return ferias_por_funcionario
