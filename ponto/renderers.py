import os
import tempfile

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from PIL import Image

from django.http import HttpResponse
from django.template.loader import get_template, render_to_string

from settings.settings import STATIC_ROOT


class RenderToPDF:
	def __init__(self, request, pageHTML, context={}, filename='arquivo.pdf'):
		self.request = request
		self.pageHTML = pageHTML
		self.context = context
		self.filename = filename

	def _render_template(self):
		template = get_template(self.pageHTML)
		return template.render(self.context)

	def xhtml2pdf(self):
		from io import BytesIO
		from xhtml2pdf import pisa

		html = self._render_template()
		result = BytesIO()
		pdf = pisa.pisaDocument(BytesIO(html.encode('utf-8')), result, encoding='utf-8')
		
		if pdf.err:
			return HttpResponse('Erro ao gerar PDF', status=400, content_type='text/plain')
		
		# return HttpResponse(result.getvalue(), content_type='application/pdf')
		
		response = HttpResponse(result.getvalue(), content_type='application/pdf')
		response['Content-Disposition'] = f'attachment; filename={self.filename}'
		return response

	def weasyprint(self):
		from weasyprint import HTML

		html = self._render_template()
		css = [os.path.join(STATIC_ROOT, 'bootstrap/css/bootstrap.min.css')]
		
		pdf = HTML(string=html, base_url=self.request.build_absolute_uri()).write_pdf(
			stylesheets=css,
			presentational_hints=True,
			optimize_size=('fonts', 'images')
		)
		
		# return HttpResponse(pdf, content_type='application/pdf')

		response = HttpResponse(pdf, content_type='application/pdf')
		response['Content-Disposition'] = f'attachment; filename={self.filename}'
		return response

	def pdfkit(self):
		import pdfkit

		html = self._render_template()
		css = os.path.join(STATIC_ROOT, 'bootstrap\\css\\bootstrap.min.css')
		options = {'enable-local-file-access': None, 'encoding': 'UTF-8'}

		pdf = pdfkit.from_string(html, False, options=options, css=css)

		# return HttpResponse(pdf, content_type='application/pdf')

		response = HttpResponse(pdf, content_type='application/pdf')
		response['Content-Disposition'] = f'attachment; filename={self.filename}'
		return response


def gerar_certificado(context):
	# Renderizar HTML como string
	html_content = render_to_string('relatorios/certificado.html', context)

	# Criar arquivo HTML temporário
	with tempfile.NamedTemporaryFile(delete=False, suffix='.html') as temp_html:
		temp_html.write(html_content.encode('utf-8'))
		temp_html_path = temp_html.name

	# Configurar Selenium para rodar em modo headless
	chrome_options = Options()
	chrome_options.add_argument('--headless')
	chrome_options.add_argument('--disable-gpu')
	chrome_options.add_argument('--window-size=1024x768')

	driver = webdriver.Chrome(options=chrome_options)
	driver.get(f'file://{temp_html_path}')

	# Tira um screenshot
	temp_png_path = temp_html_path.replace('.html', '.png')
	driver.save_screenshot(temp_png_path)
	driver.quit()

	# Ajustar imagem para cortar espaços vazios (opcional)
	image = Image.open(temp_png_path)
	image = image.crop(image.getbbox())  # Remove espaços vazios
	image.save(temp_png_path)  # Salva a versão ajustada
	image_name = f'certificado-{context["uuid"]}.png'

	# Lê a imagem para enviar como resposta HTTP
	with open(temp_png_path, 'rb') as img_file:
		image_data = img_file.read()

	# Remover arquivos temporários
	os.remove(temp_html_path)
	os.remove(temp_png_path)

	# Retornar a imagem como um download
	response = HttpResponse(image_data, content_type='image/png')
	response['Content-Disposition'] = f'attachment; filename={image_name}'

	return response

