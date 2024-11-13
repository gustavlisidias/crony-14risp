import zipfile

from io import BytesIO
from datetime import timedelta, date

from django.http import HttpResponse
from django.shortcuts import get_object_or_404

from configuracoes.models import Variavel
from funcionarios.models import Funcionario, JornadaFuncionario
from notifications.signals import notify
from ponto.models import Ponto
from ponto.renderers import RenderToPDF
from ponto.utils import pontos_por_dia
from web.utils import not_none_not_empty, parse_date, parse_employee


DADOS_EMPRESA = {'nome': Variavel.objects.get(chave='NOME_EMPRESA').valor, 'cnpj': Variavel.objects.get(chave='CNPJ').valor, 'inscricao': Variavel.objects.get(chave='INSC_ESTADUAL').valor}


def gerar_pdf_ponto(request, funcionarios, data_inicial, data_final):
	data_inicial = parse_date(data_inicial)
	data_final = parse_date(data_final)
	funcionarios = parse_employee(funcionarios)
	zip_buffer = BytesIO()

	def processar_funcionario(funcionario):
		try:
			pontos, _ = pontos_por_dia(data_inicial, data_final, funcionario)
			
			if not pontos:
				raise ValueError(f'Nenhum ponto encontrado para {funcionario.nome_completo}')
			
			jornada = {}
			for item in JornadaFuncionario.objects.filter(funcionario=funcionario, final_vigencia=None).order_by('funcionario__id', 'agrupador', 'dia', 'ordem'):
				if item.dia not in jornada:
					jornada[item.dia] = []
				jornada[item.dia].append({'tipo': item.get_tipo_display(), 'hora': item.hora, 'contrato': item.contrato})
			
			nro_colunas = 0
			saldos = {
				'total': timedelta(seconds=0),
				'saldo': timedelta(seconds=0),
				'credito': timedelta(seconds=0),
				'debito': timedelta(seconds=0)
			}

			for _, dados in pontos.items():
				for dado in dados:
					saldos['total'] += dado['total']
					saldos['saldo'] += dado['saldo']

					if dado['saldo'] < timedelta(0):
						saldos['debito'] += dado['saldo']
					else:
						saldos['credito'] += dado['saldo']

					if len(dado['pontos']) > nro_colunas:
						nro_colunas = len(dado['pontos'])

			filename = f'espelho_ponto_{funcionario.nome_completo.lower()}.pdf'
			context = {
				'pontos': pontos,
				'saldos': saldos,
				'funcionario': funcionario,
				'periodo': {'inicio': data_inicial, 'final': data_final},
				'nro_colunas': range(nro_colunas),
				'autor': get_object_or_404(Funcionario, usuario=request.user),
				'jornada': jornada,
				'dados_empresa': DADOS_EMPRESA
			}

			if not_none_not_empty(request.POST.get('fechamento')):
				for ponto in Ponto.objects.filter(funcionario=funcionario, data__range=[data_inicial, data_final]).order_by('data', 'hora'):
					ponto.encerrado = True
					ponto.data_fechamento = date.today()
					ponto.save()

			pdf = RenderToPDF(request, 'relatorios/espelho_ponto.html', context, filename).weasyprint()
			return filename, pdf
		
		except Exception as e:
			notify.send(
				sender=request.user,
				recipient=request.user,
				verb='Houve erros ao gerar espelho de ponto',
				description=e,
			)

			return None, None

	if funcionarios.count() > 1:
		with zipfile.ZipFile(zip_buffer, 'w') as zip_file:
			for funcionario in funcionarios:
				filename, pdf = processar_funcionario(funcionario)
				if filename and pdf:
					zip_file.writestr(filename, pdf.content)

		zip_buffer.seek(0)
		response = HttpResponse(zip_buffer, content_type='application/zip')
		response['Content-Disposition'] = 'attachment; filename=espelhos_ponto.zip'
		return response

	else:
		funcionario = funcionarios.first()
		filename, response = processar_funcionario(funcionario)
		
	return response
