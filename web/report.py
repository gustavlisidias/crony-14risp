import codecs
import pandas

from django.http import HttpResponse


def gerar_relatorio_csv(colunas, dataset, filename):
	response = HttpResponse(content_type='text/csv')
	response['Content-Disposition'] = f'attachment; filename={filename}.csv'                                
	response.write(codecs.BOM_UTF8)

	with codecs.getwriter('utf-8')(response) as csv_file:
		df = pandas.DataFrame(dataset, columns=colunas)
		df.to_csv(csv_file, sep=';', index=False)

	return response
