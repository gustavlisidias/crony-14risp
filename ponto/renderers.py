import os
import pdfkit

from io import BytesIO
from xhtml2pdf import pisa
from weasyprint import HTML

from django.http import HttpResponse
from django.template.loader import get_template

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
		html = self._render_template()
		result = BytesIO()
		pdf = pisa.pisaDocument(BytesIO(html.encode('UTF-8')), result)
		
		if pdf.err:
			return HttpResponse('Invalid PDF', status=400, content_type='text/plain')
		
		# return HttpResponse(result.getvalue(), content_type='application/pdf')
		
		response = HttpResponse(result.getvalue(), content_type='application/pdf')
		response['Content-Disposition'] = f'attachment; filename={self.filename}'
		return response

	def pdfkit(self):
		html = self._render_template()
		css = [os.path.join(STATIC_ROOT, 'bootstrap/css/bootstrap.min.css')]
		pdf = pdfkit.from_string(html, False, css=css)
		
		# return HttpResponse(pdf, content_type='application/pdf')
		
		response = HttpResponse(pdf, content_type='application/pdf')
		response['Content-Disposition'] = f'attachment; filename={self.filename}'
		return response

	def weasyprint(self):
		html = self._render_template()
		css = [os.path.join(STATIC_ROOT, 'bootstrap/css/bootstrap.min.css')]
		pdf = HTML(string=html, base_url=self.request.build_absolute_uri()).write_pdf(stylesheets=css)
		
		# return HttpResponse(pdf, content_type='application/pdf')

		response = HttpResponse(pdf, content_type='application/pdf')
		response['Content-Disposition'] = f'attachment; filename={self.filename}'
		return response
