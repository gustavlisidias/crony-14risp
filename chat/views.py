import uuid

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from datetime import datetime, timedelta

from chat.models import Sala, Mensagem, Arquivo
from funcionarios.models import Funcionario
from web.utils import not_none_not_empty


@login_required(login_url='entrar')
def ChatUsersView(request):
	if not request.method == 'GET':
		return JsonResponse({'message': 'forbidden'}, status=404)
	
	try:
		funcionario = Funcionario.objects.get(usuario=request.user)
		usuarios = list()
		for i in Funcionario.objects.filter(data_demissao=None).exclude(pk=funcionario.pk).order_by('nome_completo'):
			usuarios.append({
				'id': i.id,
				'nome_completo': i.nome_completo,
				'is_auth': i.usuario.is_authenticated,
				'setor': i.setor.setor
			})

		usuarios_recentes = set()
		max_date = datetime.today().date() - timedelta(days=1)
		salas = Sala.objects.filter(tipo=Sala.Tipos.CONVERSA, funcionarios=funcionario)
		for i in Mensagem.objects.filter(sala__in=salas, data_cadastro__date__gte=max_date):
			for j in i.sala.funcionarios.all():
				if j != funcionario:
					usuarios_recentes.add(j)

		grupos = list()
		for i in Sala.objects.filter(tipo=Sala.Tipos.GRUPO, funcionarios=funcionario):
			grupos.append({'id': i.id, 'nome': i.nome})
		
		context = {
			'usuarios': usuarios,
			'usuarios_recentes': [{
				'id': i.id,
				'nome_completo': i.nome_completo,
				'is_auth': i.usuario.is_authenticated
			} for i in usuarios_recentes],
			'grupos': grupos
		}

		return JsonResponse(context, safe=False, status=200)
	except Exception as e:
		return JsonResponse({'message': f'Erro ao consultar funcionários: {e}'}, status=400)


@login_required(login_url='entrar')
def ChatView(request, index, tipo):	
	try:
		remetente = Funcionario.objects.get(usuario=request.user)
		destinatarios = list()

		if tipo == 'group':
			sala = Sala.objects.get(pk=index)
		else:
			destinatario = get_object_or_404(Funcionario, pk=index)

			# Procura por uma sala existente com os 2 usuários
			sala = Sala.objects.exclude(tipo=Sala.Tipos.GRUPO).filter(funcionarios=remetente).filter(funcionarios=destinatario).first()
			
			# Se não houver uma sala existente, cria uma nova
			if not sala:
				sala = Sala.objects.create(uuid=uuid.uuid4().hex)
				sala.funcionarios.add(remetente, destinatario)

		for mensagem in Mensagem.objects.filter(sala=sala).exclude(remetente=remetente):
			mensagem.lido = True
			mensagem.save()
		
		for arquivo in Arquivo.objects.filter(sala=sala).exclude(remetente=remetente):
			arquivo.lido = True
			arquivo.save()

		# Crio o socket com o uuid da sala
		socket = f'{request.get_host()}/ws/chat/room/{sala.uuid}'

		# Recupero as mensagens e arquivos associadas à sala
		mensagens = []
		for mensagem in Arquivo.objects.filter(sala=sala).order_by('data_cadastro'):
			mensagens.append({
				'remetente': mensagem.remetente.nome_completo,
				'data_cadastro': mensagem.data_cadastro,
				'mensagem': mensagem.arquivo.url,
				'tipo': 'arq'
			})

		for mensagem in Mensagem.objects.filter(sala=sala).order_by('data_cadastro'):
			mensagens.append({
				'remetente': mensagem.remetente.nome_completo,
				'data_cadastro': mensagem.data_cadastro,
				'mensagem': mensagem.mensagem,
				'tipo': 'msg'
			})

		mensagens = sorted(mensagens, key=lambda x: x['data_cadastro'])

		destinatarios.append([{
			'id': i.id,
			'nome': i.nome_completo,
			'img': i.get_perfil.foto.url if i.get_perfil.foto else None,
			'tipo': 'usuario'
		} for i in sala.funcionarios.all()])

		if tipo == 'group':
			destinatarios[0].append({'id': sala.id, 'nome': sala.nome, 'img': None, 'tipo': 'grupo'})

		context = {
			'mensagens': mensagens,
			'remetente': {
				'id': remetente.id,
				'nome': remetente.nome_completo,
				'img': remetente.get_perfil.foto.url if remetente.get_perfil.foto else None
			}, 
			'destinatarios': destinatarios[0],
			'socket': socket
		}

		return JsonResponse(context, safe=False, status=200)
	
	except Exception as e:
		return JsonResponse({'message': f'Erro ao consultar mensagens: {e}'}, status=400)


@login_required(login_url='entrar')
def MesagemMassaView(request):
	if not request.method == 'POST':
		messages.warning(request, 'Método não permitido!')
		return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))
	
	texto = request.POST.get('mensagem-texto')
	remetente = Funcionario.objects.get(usuario=request.user)
	destinatarios = Funcionario.objects.filter(pk__in=request.POST.getlist('mensagem-funcionarios'))

	if not_none_not_empty(texto, destinatarios):
		for destinatario in destinatarios:
			salas = Sala.objects.exclude(tipo=Sala.Tipos.GRUPO).filter(funcionarios=remetente).filter(funcionarios=destinatario)
			if salas:
				sala = salas.first()
			else:
				sala = Sala.objects.create(uuid=uuid.uuid4().hex)
				sala.funcionarios.add(remetente, destinatario)

			Mensagem.objects.create(sala=sala, mensagem=texto, remetente=remetente)

			channel_layer = get_channel_layer()
			async_to_sync(channel_layer.group_send)(
				'global_chat_notifications', {
					'type': 'chat.notify',
					'remetente': remetente.nome_completo,
					'remetente_id': remetente.id,
					'destinatario': destinatario.nome_completo,
					'destinatario_id': destinatario.id,
					'notificar': True
				}
			)
		
		messages.success(request, 'Mensagem enviada com sucesso!')
	
	else:
		messages.error(request, 'Preencha todos os campos obrigatórios!')

	return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))
