from django.contrib import messages
from django.core.exceptions import RequestDataTooBig
from django.http import HttpResponseRedirect


class HandleRequestDataTooBigMiddleware:
	'''
	https://stackoverflow.com/questions/43496658/django-catch-requestdatatoobig-exception
	Em D:\Projetos\crony\.env\Lib\site-packages\django\http\request.py adicionar o codigo
	self._body = self.read(None)
	dentro do metodo body
	'''

	def __init__(self, get_response):
		self.get_response = get_response

	def __call__(self, request):
		try:
			request.body

		except RequestDataTooBig:
			messages.error(request, 'Importação excede o tamanho máximo. Por favor diminua a quantidade de arquivos.')
			return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))

		response = self.get_response(request)
		return response
