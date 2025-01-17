import json
import base64
import os
import logging

from django.core.files.base import ContentFile

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer

from collections import defaultdict

from chat.models import Sala, Mensagem, Arquivo
from funcionarios.models import Funcionario
from settings.settings import BASE_DIR


@database_sync_to_async
def get_sala(uuid):
	try:
		return Sala.objects.get(uuid=uuid)
	except Exception:
		return Sala.objects.get(pk=uuid)


@database_sync_to_async
def get_sala_funcionarios(remetente, destinatario):
	return Sala.objects.filter(funcionarios=remetente, tipo=Sala.Tipos.CONVERSA).filter(funcionarios=destinatario).first()


@database_sync_to_async
def get_visualizado(sala, room):
	return len(sala.funcionarios.all()) == len(room)


@database_sync_to_async
def get_group_users(sala):
	return [i.id for i in sala.funcionarios.all() if i.nome_completo not in ChatConsumer.room_connections[f'chat_{sala.uuid}']]


@database_sync_to_async
def get_funcionario(**kwargs):
	try:
		if 'pk' in kwargs.keys():
			return Funcionario.objects.get(pk=kwargs.get('pk'))
		if 'user' in kwargs.keys():
			return Funcionario.objects.get(usuario=kwargs.get('user'))
	except Exception:
		return None


@database_sync_to_async
def get_foto(funcionario):
	if funcionario.get_perfil.foto:
		return funcionario.get_perfil.foto.url
	return None


@database_sync_to_async
def get_pendencias(remetente_id):
	pendencias = set()

	salas = Sala.objects.filter(funcionarios=remetente_id)

	for mensagem in Mensagem.objects.filter(sala__in=salas, lido=False).exclude(remetente__id=remetente_id):
		if mensagem.sala.tipo == Sala.Tipos.CONVERSA:
			pendencias.add(mensagem.remetente.id)

	for arquivo in Arquivo.objects.filter(sala__in=salas, lido=False).exclude(remetente__id=remetente_id):
		if arquivo.sala.tipo == Sala.Tipos.CONVERSA:
			pendencias.add(arquivo.remetente.id)
	
	return pendencias


@database_sync_to_async
def criar_mensagem(sala, remetente, mensagem, lido):
	Mensagem(sala=sala, remetente=remetente, mensagem=mensagem, lido=lido).save()


@database_sync_to_async
def criar_arquivo(sala, remetente, arquivo, lido):
	Arquivo(sala=sala, remetente=remetente, arquivo=arquivo, lido=lido).save()


@database_sync_to_async
def criar_log(mensagem):
	log_path = os.path.join(BASE_DIR, 'logs/log_chat.log')
	logging.basicConfig(filename=log_path, encoding='utf-8', level=logging.INFO, force=True)
	logging.info(mensagem)


class ChatConsumer(AsyncWebsocketConsumer):
	employee = None
	room_name = None
	room_connections = defaultdict(set)
	sala = None

	async def connect(self):
		await self.accept()

		parms = self.scope['url_route']['kwargs']

		self.sala = await get_sala(parms.get('room'))
		if not self.sala:
			await self.send(text_data=json.dumps({'reason': 'Sala não encontrada'}))
			await self.close(code=4000)
			return

		self.user = self.scope['user']
		if not self.user:
			await self.send(text_data=json.dumps({'reason': 'Usuário não encontrado'}))
			await self.close(code=4001)
			return
		
		funcionario = await get_funcionario(user=self.user)
		if not funcionario:
			await self.send(text_data=json.dumps({'reason': 'Funcionário não encontrado'}))
			await self.close(code=4002)
			return

		self.employee = funcionario.nome_completo
		if not self.user.is_authenticated or not self.employee:
			await self.send(text_data=json.dumps({'reason': 'Usuário não autenticado ou não encontrado NOME_COMPLETO do Funcionário'}))
			await self.close(code=4003)
			return

		try:
			self.room_name = f'chat_{self.sala.uuid}'
			self.room_connections[self.room_name].add(self.employee)

			await self.channel_layer.group_add(self.room_name, self.channel_name)

			await criar_log(f'Conexão estabelecida na sala {self.room_name}, total de {len(self.room_connections[self.room_name])} usuários')
			
		except Exception as e:
			await self.send(text_data=json.dumps({'reason': e}))
			await self.close(code=4004)
			return

	async def disconnect(self, close_code):
		if self.room_name and self.user.is_authenticated:
			self.room_connections[self.room_name].discard(self.employee)
			await self.channel_layer.group_discard(self.room_name, self.channel_name)

		await criar_log(f'Desconexão de {self.employee} em {self.room_name}')

	async def receive(self, text_data):
		remetente = await get_funcionario(pk=int(json.loads(text_data)['remetente']))

		if 'arquivo' in json.loads(text_data):
			arquivo = json.loads(text_data)['arquivo']
			nome = arquivo.get('name')
			dados_base64 = arquivo.get('data')
			formato, dados_base64 = dados_base64.split(';base64,')
			dados_binarios = base64.b64decode(dados_base64)
			arquivo_modelo = ContentFile(dados_binarios, name=nome)
			lido = await get_visualizado(self.sala, self.room_connections[self.room_name])

			await criar_arquivo(sala=self.sala, remetente=remetente, arquivo=arquivo_modelo, lido=lido)

			imagem = await get_foto(remetente)
			await self.channel_layer.group_send(
				self.room_name, {
					'type': 'chat.arquivo',
					'nome': nome,
					'arquivo': dados_base64,
					'formato': formato.replace('data:', ''),
					'remetente': remetente.nome_completo,
					'remetente_id': remetente.id,
					'imagem': imagem
			})

			await criar_log(f'O usuário {remetente.nome_completo} enviou o arquivo: {nome}')

		else:
			message = json.loads(text_data)['message']
			lido = await get_visualizado(self.sala, self.room_connections[self.room_name])

			await criar_mensagem(sala=self.sala, remetente=remetente, mensagem=message, lido=lido)

			imagem = await get_foto(remetente)
			await self.channel_layer.group_send(
				self.room_name, {
					'type': 'chat.message', 
					'message': message,
					'remetente': remetente.nome_completo,
					'remetente_id': remetente.id,
					'imagem': imagem
			})

			await criar_log(f'O usuário {remetente.nome_completo} enviou a mensagem: {message}')

	async def chat_message(self, event):
		await self.send(text_data=json.dumps({
			'message': event['message'],
			'remetente': event['remetente'],
			'remetente_id': event['remetente_id'],
			'imagem': event['imagem']
		}))

	async def chat_arquivo(self, event):
		await self.send(text_data=json.dumps({
			'nome': event['nome'],
			'arquivo': event['arquivo'],
			'formato': event['formato'],
			'remetente': event['remetente'],
			'remetente_id': event['remetente_id'],
			'imagem': event['imagem']
		}))


class ChatNotificationConsumer(AsyncWebsocketConsumer):
	employee = None
	room_name = 'global_chat_notifications'
	room_connections = defaultdict(set)

	async def connect(self):
		await self.accept()

		self.user = self.scope['user']
		if not self.user:
			await self.send(text_data=json.dumps({'reason': 'Usuário não encontrado'}))
			await self.close(code=4001)
			return

		funcionario = await get_funcionario(user=self.user)
		if not funcionario:
			await self.send(text_data=json.dumps({'reason': 'Funcionário não encontrado'}))
			await self.close(code=4002)
			return
		
		self.employee = funcionario.id
		if not self.user.is_authenticated or not self.employee:
			await self.send(text_data=json.dumps({'reason': 'Usuário não autenticado ou não encontrado ID do Funcionário'}))
			await self.close(code=4003)
			return
		
		try:
			await self.channel_layer.group_add(self.room_name, self.channel_name)

			self.room_connections[self.room_name].add(self.employee)
			await self.channel_layer.group_send(
				self.room_name, {
					'type': 'chat.connections',
					'users': list(self.room_connections[self.room_name])
			})

			pendencias = await get_pendencias(self.employee)
			if pendencias:
				await self.channel_layer.group_send(
					self.room_name, {
						'type': 'chat.pendings',
						'user': self.employee,
						'pendings': list(pendencias),
				})

			await criar_log(f'Conexão estabelecida na sala {self.room_name}, total de {len(self.room_connections[self.room_name])} usuários')

		except Exception as e:
			await self.send(text_data=json.dumps({'reason': e}))
			await self.close(code=4004)
			return

	async def disconnect(self, close_code):
		if self.user.is_authenticated:

			self.room_connections[self.room_name].discard(self.employee)
			await self.channel_layer.group_send(
				self.room_name, {
					'type': 'chat.connections',
					'users': list(self.room_connections[self.room_name])
			})

			await self.channel_layer.group_discard(self.room_name, self.channel_name)
			await self.close()

		await criar_log(f'Conexão encerrada na sala {self.room_name}, total de {len(self.room_connections[self.room_name])} usuários')

	async def receive(self, text_data):
		if json.loads(text_data)['tipo'] == 'user':
			remetente = await get_funcionario(pk=int(json.loads(text_data)['remetente']))
			destinatario = await get_funcionario(pk=int(json.loads(text_data)['index']))
			sala = await get_sala_funcionarios(remetente, destinatario)
			notificar = False if destinatario.nome_completo in ChatConsumer.room_connections[f'chat_{sala.uuid}'] else True

			await self.channel_layer.group_send(
				self.room_name, {
					'type': 'chat.notify',
					'remetente': remetente.nome_completo,
					'remetente_id': remetente.id,
					'destinatario': destinatario.nome_completo,
					'destinatario_id': destinatario.id,
					'notificar': notificar
			})

			await criar_log(f'O usuário {remetente.nome_completo} enviou uma nova mensagem para {destinatario.nome_completo}')

		else:
			remetente = await get_funcionario(pk=int(json.loads(text_data)['remetente']))
			sala = await get_sala(int(json.loads(text_data)['index'])) # grupo
			destinatarios = await get_group_users(sala)

			await self.channel_layer.group_send(
				self.room_name, {
					'type': 'chat.notify',
					'remetente': remetente.nome_completo,
					'remetente_id': remetente.id,
					'destinatario': destinatarios,
					'destinatario_id': sala.id,
					'notificar': True
			})

			await criar_log(f'O usuário {remetente.nome_completo} enviou uma nova mensagem no grupo {sala.nome}')

	async def chat_connections(self, event):
		await self.send(text_data=json.dumps({
			'users': event['users']
		}))

	async def chat_pendings(self, event):
		await self.send(text_data=json.dumps({
			'user': event['user'],
			'pendings': event['pendings']
		}))

	async def chat_notify(self, event):
		await self.send(text_data=json.dumps({
			'remetente': event['remetente'],
			'remetente_id': event['remetente_id'],
			'destinatario': event['destinatario'],
			'destinatario_id': event['destinatario_id'],
			'notificar': event['notificar']
		}))
		