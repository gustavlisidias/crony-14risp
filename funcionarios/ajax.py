import os

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponse, JsonResponse
from django.utils import timezone
from django.utils.text import slugify

from datetime import datetime
from pathlib import Path

from agenda.models import DocumentosFerias
from configuracoes.models import Variavel
from funcionarios.models import Documento, Funcionario, TipoDocumento, JornadaFuncionario, Estabilidade
from funcionarios.utils import allowed_extensions, allowed_content_types
from ponto.models import SolicitacaoAbono
from web.report import gerar_relatorio_csv
from web.utils import not_none_not_empty


@login_required(login_url='entrar')
def AdicionarDocumentoView(request):
	if not request.method == 'POST':
		messages.warning(request, 'Método não permitido!')
		return JsonResponse({'message': 'forbidden'}, status=404)
	
	tipo = TipoDocumento.objects.get(pk=request.POST.get('tipo')) if request.POST.get('tipo') else None
	data_documento = datetime.strptime(request.POST.get('data'), '%Y-%m-%d').date() if request.POST.get('data') else timezone.localdate()
	funcionario = Funcionario.objects.get(pk=request.POST.get('funcionario')) if request.POST.get('funcionario') else None

	file = request.FILES.get('file')
	filename, extension = file.name.split('.')
	filename = f'{slugify(filename)}.{extension}'

	if extension not in allowed_extensions:
		return JsonResponse({'message': f'O arquivo não é em um dos formatos: {allowed_extensions}.'}, status=400)

	if tipo:
		if funcionario:
			servidor = Path(Variavel.objects.get(chave='PATH_DOCS_EMP').valor)
			pasta = Path(servidor, f'{funcionario.matricula} - {funcionario.nome_completo}')
			caminho = Path(pasta, f'{data_documento}_{tipo.codigo}_{filename}')
		else:
			servidor = Path(Variavel.objects.get(chave='PATH_DOCS').valor)
			pasta = Path(servidor, f'{tipo.codigo} - {tipo.tipo}')
			caminho = Path(pasta, f'{data_documento}_{filename}')
		
		os.makedirs(pasta, exist_ok=True)
		with open(caminho, 'wb+') as destination:
			for chunk in file.chunks():
				destination.write(chunk)

		Documento(
			funcionario=funcionario,
			tipo=tipo,
			caminho=caminho,
			data_documento=data_documento
		).save()

		return JsonResponse({'message': f'Documento {request.FILES.get("file")} salvo'}, status=200)
	else:
		return JsonResponse({'message': 'O campo Tipo Documento é obrigatório.'}, status=400)


@login_required(login_url='entrar')
def RealoadDocumentosView(request):
	if not request.method == 'GET':
		messages.warning(request, 'Método não permitido!')
		return JsonResponse({'message': 'forbidden'}, status=404)
	
	funcionario = Funcionario.objects.get(usuario=request.user)
	filtro_data_inicial = request.GET.get('data_inicial', '2018-01-01')
	filtro_data_final = request.GET.get('data_final', timezone.localdate().strftime('%Y-%m-%d'))
	filtro_nome = request.GET.get('nome')
	filtro_tipo = request.GET.get('tipo')

	if funcionario.is_financeiro:
		tipos = TipoDocumento.objects.filter(Q(visibilidade=TipoDocumento.Visoes.GERAL) | Q(visibilidade=TipoDocumento.Visoes.FINA))
	elif request.user.get_access == 'admin':
		tipos = TipoDocumento.objects.filter(Q(visibilidade=TipoDocumento.Visoes.GERAL) | Q(visibilidade=TipoDocumento.Visoes.ADMIN))
	else:
		tipos = TipoDocumento.objects.filter(visibilidade=TipoDocumento.Visoes.GERAL)
	
	documentos = Documento.objects.filter(funcionario=None, data_documento__range=[filtro_data_inicial, filtro_data_final], tipo__in=tipos).order_by('-data_documento')

	if not_none_not_empty(filtro_nome):
		documentos = documentos.filter(caminho__contains=filtro_nome)
	
	if not_none_not_empty(filtro_tipo):
		documentos = documentos.filter(tipo__in=[int(i) for i in filtro_tipo])

	tabela = list()
	for documento in documentos:
		tabela.append({
			'id': documento.id,
			'documento': documento.get_short_name,
			'data_documento': documento.data_documento,
			'tipo': documento.tipo.tipo,
			'codigo': documento.tipo.codigo
		})
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
def ExcluirHistoricoJornadaView(request, func, agrupador):
	if not request.method == 'POST':
		messages.warning(request, 'Método não permitido!')
		return JsonResponse({'message': 'forbidden'}, status=404)
	
	if request.user.get_access == 'common':
		messages.error(request, 'Você não tem permissão para excluir o arquivo!')
		return JsonResponse({'message': 'not allowed'}, status=400)
	
	try:
		with transaction.atomic():
			jornadas = JornadaFuncionario.objects.filter(funcionario__pk=func).order_by('agrupador', 'dia', 'ordem')

			if jornadas.values('agrupador').distinct().count() < 2:
				messages.error(request, 'Funcionário precisa de ao menos 1 jornada ativa!')
				return JsonResponse({'message': 'error'}, status=400)
			
			jorndas_para_excluir = jornadas.filter(agrupador=agrupador)
			jornada_ativa = jorndas_para_excluir.first().final_vigencia is None
			jorndas_para_excluir.delete()

			if jornada_ativa:
				jornadas.filter(agrupador=agrupador-1).update(final_vigencia=None)

			for jornada in jornadas:					
				if jornada.agrupador > agrupador:
					jornada.agrupador -= 1
				jornada.save()

		messages.success(request, 'Histórico removido com sucesso!')
	
	except Exception as e:
		messages.error(request, f'Erro ao tentar remover histórico de jornada: {e}')

	return JsonResponse({'message': 'success'}, status=200)


@login_required(login_url='entrar')
def ExportarFuncionariosView(request):
	if not request.method == 'GET':
		messages.warning(request, 'Método não permitido!')
		return JsonResponse({'message': 'forbidden'}, status=404)
	
	filename = 'funcionarios'
	dataset = list(Funcionario.objects.all().values_list(
		'matricula', 'nome_completo', 'nome_social', 'nome_mae', 'nome_pai', 'email', 'cpf', 'rg', 'data_expedicao', 'sexo', 'contato', 'data_nascimento', 'estado__name', 'cidade__name', 'rua', 'numero', 'complemento', 'cep', 'setor__setor', 
		'cargo__cargo', 'gerente__nome_completo', 'salario', 'data_contratacao', 'data_demissao', 'data_cadastro'
	))
	
	colunas = [
		'Matrícula', 'Nome Completo', 'Nome Social', 'Nome Mãe', 'Nome Pai', 'Email', 'CPF', 'RG', 'Data Emissão', 'Sexo', 'Contato', 'Data de Nascimento', 'Estado', 'Cidade', 'Endereço', 'Número', 'Complemento', 'CEP', 'Setor', 'Cargo',
		'Gerente', 'Salário', 'Data de Contratação', 'Data de Demissão', 'Data de Cadastro'
	]
	
	return gerar_relatorio_csv(colunas, dataset, filename)


# Stream
@login_required(login_url='entrar')
def StreamDocumentoView(request, document, model, norm):
	try:
		if model == 'doc':
			caminho = Documento.objects.get(pk=document).caminho

			with open(caminho, 'rb') as documento:
				_, extensao = os.path.splitext(caminho)
				extensao = extensao.lstrip('.')

				if extensao in allowed_extensions:
					content_type = allowed_content_types.get(extensao, 'application/octet-stream')
					response = HttpResponse(documento, content_type=content_type)
				
					if norm == 'visualizar':				
						response['Content-Disposition'] = f'inline; filename="{os.path.basename(caminho)}"'
						return response
					
					elif norm == 'download':
						response['Content-Disposition'] = f'attachment; filename="{os.path.basename(caminho)}"'
						return response

		elif model in ['abono', 'ferias']:
			query = SolicitacaoAbono.objects.get(pk=document) if model == 'abono' else DocumentosFerias.objects.get(pk=document)
			documento = query.documento
			nome_documento, extensao = query.caminho.split('.')

			if extensao in allowed_extensions:
				content_type = allowed_content_types.get(extensao, 'application/octet-stream')
				response = HttpResponse(documento, content_type=content_type)

				if norm == 'visualizar':				
					response['Content-Disposition'] = f'inline; filename="{nome_documento}"'
					return response

				elif norm == 'download':
					response['Content-Disposition'] = f'attachment; filename="{nome_documento}"'
					return response
		
		else:
			return HttpResponse(status=204)

	except Exception:
		return HttpResponse(status=204)


@login_required(login_url='entrar')
def ExcluirEstabilidadeView(request, stab):
	if not request.method == 'POST':
		messages.warning(request, 'Método não permitido!')
		return JsonResponse({'message': 'forbidden'}, status=404)
	
	if request.user.get_access == 'common':
		messages.error(request, 'Você não tem permissão para excluir a estabilidade!')
		return JsonResponse({'message': 'not allowed'}, status=400)
	
	Estabilidade.objects.get(pk=stab).delete()
	messages.success(request, 'Estabilidade removida com sucesso')
	return JsonResponse({'message': 'success'}, status=200)


@login_required(login_url='entrar')
def ConsultarFuncionarioView(request, code):
	if request.method != 'GET':
		messages.warning(request, 'Método não permitido!')
		return JsonResponse({'message': 'forbidden'}, status=404)
	
	code2 = re.sub('\W+','', code)
	query = Funcionario.objects.filter(Q(cpf=code) | Q(cpf=code2))
	if query:
		response = {'status': True, 'nome': query.last().nome_completo}
	else:
		response = {'status': False, 'nome': None}

	return JsonResponse(response, status=200)
