from django.contrib import admin

from funcionarios.models import (
    Cargo,
    Documento,
    Funcionario,
    JornadaFuncionario,
    Perfil,
    Score,
    Setor,
    TipoDocumento,
    Feedback,
    SolicitacaoFeedback,
	RespostaFeedback,
	HistoricoFuncionario
)


admin.site.register(Setor)
admin.site.register(Cargo)
admin.site.register(Funcionario)
admin.site.register(JornadaFuncionario)
admin.site.register(TipoDocumento)
admin.site.register(Documento)
admin.site.register(Perfil)
admin.site.register(Score)
admin.site.register(Feedback)
admin.site.register(SolicitacaoFeedback)
admin.site.register(RespostaFeedback)
admin.site.register(HistoricoFuncionario)
