import codecs
import pandas as pd
import os
import re

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, JsonResponse
from django.utils import timezone

from datetime import datetime
from pathlib import Path

from agenda.models import DocumentosFerias
from configuracoes.models import Variavel
from funcionarios.models import Documento, Funcionario, TipoDocumento
from funcionarios.utils import converter_documento
from ponto.models import SolicitacaoAbono
from web.utils import not_none_not_empty


@login_required(login_url='entrar')
def AdicionarDocumentoView(request):
	if not request.method == 'POST':
		messages.warning(request, 'Método não permitido!')
		return JsonResponse({'message': 'forbidden'}, status=404)
	
	try:
		if not_none_not_empty(request.POST.get('tipo')):
			tipo = TipoDocumento.objects.get(pk=request.POST.get('tipo'))
			nome, documento = converter_documento(request.FILES.get('file'))
			funcionario, data_documento = None, timezone.localdate()

			if not documento:
				return JsonResponse({'message': 'Verifique o tipo de documento. Permitido apenas os tipos JPG, JPEG, PNG e PDF.'}, status=400)

			pasta = Path(Variavel.objects.get(chave='PATH_DOCS').valor, f'{tipo.codigo} - {tipo.tipo}')
			nome_lista = re.sub(r'[^a-zA-Z0-9]', '_', nome).split('_')
		
			if not_none_not_empty(request.POST.get('funcionario')):
				funcionario = Funcionario.objects.get(pk=request.POST.get('funcionario'))
				pasta = Path(Variavel.objects.get(chave='PATH_DOCS_EMP').valor, f'{funcionario.matricula} - {funcionario.nome_completo}')
				nome_lista.insert(0, tipo.codigo)

			if not_none_not_empty(request.POST.get('data')):
				data_documento = datetime.strptime(request.POST.get('data'), '%Y-%m-%d').date()
				nome_lista.insert(0, request.POST.get('data'))

			if request.POST.get('enviar') == 'on':
				os.makedirs(pasta, exist_ok=True)
				caminho = os.path.join(pasta, f'{"_".join(nome_lista)}.pdf')

				with open(caminho, 'wb') as f:
					f.write(documento)

			Documento(
				funcionario=funcionario,
				tipo=tipo,
				documento=documento, 
				caminho=f'{nome}.pdf',
				data_documento=data_documento
			).save()

		else:
			return JsonResponse({'message': 'O campo Tipo Documento é obrigatório.'}, status=400)
		
		return JsonResponse({'message': f'Documento {request.FILES.get("file")} salvo'}, status=200)
				
	except Exception as e:
		return JsonResponse({'message': e}, status=500)


@login_required(login_url='entrar')
def RealoadDocumentosView(request):
	if not request.method == 'GET':
		messages.warning(request, 'Método não permitido!')
		return JsonResponse({'message': 'forbidden'}, status=404)
	
	filtro_data_inicial = request.GET.get('data_inicial') if not_none_not_empty(request.GET.get('data_inicial')) else '2018-01-01'  # (timezone.localdate() - timedelta(days=10)).strftime('%Y-%m-%d')
	filtro_data_final = request.GET.get('data_final') if not_none_not_empty(request.GET.get('data_final')) else timezone.localdate().strftime('%Y-%m-%d')
	filtro_nome = request.GET.get('nome')
	filtro_tipo = request.GET.get('tipo')

	tipos = TipoDocumento.objects.all()

	documentos = Documento.objects.filter(funcionario=None, data_documento__range=[filtro_data_inicial, filtro_data_final], tipo__in=tipos).order_by('-data_documento')

	if not_none_not_empty(filtro_nome):
		documentos = documentos.filter(caminho__contains=filtro_nome)
	
	if not_none_not_empty(filtro_tipo):
		documentos = documentos.filter(tipo__in=[int(i) for i in filtro_tipo])

	tabela = list(documentos.values('id', 'caminho', 'tipo__tipo', 'tipo__codigo', 'data_documento'))
	return JsonResponse(tabela, safe=False, status=200)


@login_required(login_url='entrar')
def ExcluirDocumentoView(request, document):
	if not request.method == 'POST':
		messages.warning(request, 'Método não permitido!')
		return JsonResponse({'message': 'forbidden'}, status=404)
	
	if request.user.get_access == 'common':
		messages.error(request, 'Você não tem permissão para excluir o arquivo!')
		return JsonResponse({'message': 'not allowed'}, status=400)
	
	Documento.objects.get(pk=document).delete()
	messages.success(request, 'Documento excluido do banco de dados com sucesso! O arquivo físico ainda existe no servidor.')
	return JsonResponse({'message': 'success'}, status=200)


@login_required(login_url='entrar')
def ExportarFuncionariosView(request):
	if not request.method == 'GET':
		messages.warning(request, 'Método não permitido!')
		return JsonResponse({'message': 'forbidden'}, status=404)
	
	dataset = list(Funcionario.objects.all().values_list(
		'matricula', 'nome_completo', 'nome_social', 'nome_mae', 'nome_pai', 'email', 'cpf', 'rg', 'data_expedicao', 'sexo', 'contato', 'data_nascimento', 'estado__name', 'cidade__name', 'rua', 'numero', 'complemento', 'cep', 'setor__setor', 
		'cargo__cargo', 'gerente__nome_completo', 'salario', 'data_contratacao', 'data_demissao', 'data_cadastro'
	))
	
	colunas = [
		'Matrícula', 'Nome Completo', 'Nome Social', 'Nome Mãe', 'Nome Pai', 'Email', 'CPF', 'RG', 'Data Emissão', 'Sexo', 'Contato', 'Data de Nascimento', 'Estado', 'Cidade', 'Endereço', 'Número', 'Complemento', 'CEP', 'Setor', 'Cargo',
		'Gerente', 'Salário', 'Data de Contratação', 'Data de Demissão', 'Data de Cadastro'
	]
	
	response = HttpResponse (content_type='text/csv')
	response['Content-Disposition'] = 'attachment; filename=funcionarios.csv'                                
	response.write(codecs.BOM_UTF8)

	with codecs.getwriter('utf-8')(response) as csv_file:
		df = pd.DataFrame(dataset, columns=colunas)
		df.to_csv(csv_file, sep=';', index=False)
	
	return response


# Stream
@login_required(login_url='entrar')
def StreamDocumentoView(request, document, model, norm):
	if model == 'doc':
		documento = Documento.objects.get(pk=document)
	elif model == 'abono':
		documento = SolicitacaoAbono.objects.get(pk=document)
	else:
		documento = DocumentosFerias.objects.get(pk=document)

	if norm == 'download':
		response = HttpResponse(documento.documento, content_type='application/octet-stream')
		response['Content-Disposition'] = f'attachment; filename="{documento.caminho}"'
		response['Content-Length'] = len(documento.documento)
	
	if norm == 'visualizar':
		response = HttpResponse(documento.documento, content_type='application/pdf')
	
	return response