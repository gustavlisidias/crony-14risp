from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path, re_path
from django.views.static import serve 

from configuracoes.views import LoginView, LogoutView, RegistrationView
from configuracoes.registration import PasswordResetView, PasswordResetDoneView, PasswordResetConfirmView
from settings import settings


handler404 = 'configuracoes.error.custom_page_not_found_view'
handler500 = 'configuracoes.error.custom_error_view'
handler403 = 'configuracoes.error.custom_permission_denied_view'
handler400 = 'configuracoes.error.custom_bad_request_view'

urlpatterns = [
	re_path(r'^media/(?P<path>.*)$', serve,{'document_root': settings.MEDIA_ROOT}), 
	re_path(r'^static/(?P<path>.*)$', serve,{'document_root': settings.STATIC_ROOT}),

	path('ckeditor5/', include('django_ckeditor_5.urls')),
	path('admin/', admin.site.urls),

	path('registrar', RegistrationView, name='registrar'),
	path('entrar', LoginView, name='entrar'),
	path('sair', LogoutView, name='sair'),

	path('recuperar/senha', PasswordResetView.as_view(), name='recuperar-senha'),
	path('recuperar/senha/enviado', PasswordResetDoneView.as_view(), name='recuperar-senha-enviado'),
	path('recuperar/senha/<uidb64>/<token>/', PasswordResetConfirmView.as_view(), name='recuperar-senha-alterar'),

	path('', include('agenda.urls')),
	path('', include('avaliacoes.urls')),
	path('', include('chat.urls')),
	path('', include('configuracoes.urls')),
	path('', include('cursos.urls')),
	path('', include('funcionarios.urls')),
	path('', include('notificacoes.urls')),
	path('', include('pesquisa.urls')),
	path('', include('ponto.urls')),
	path('', include('web.urls')),
]

if settings.DEBUG:
	urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
	urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

urlpatterns += [path('/i18n/', include('django.conf.urls.i18n'))]
