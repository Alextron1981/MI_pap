from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin

class IndexView(LoginRequiredMixin, TemplateView):
    template_name = 'index.html'
    login_url = '/admin/login/'

urlpatterns = [
    path('', IndexView.as_view(), name='index'),  # Главная страница приложения
    path('admin/', admin.site.urls),
    path('api/fieldwork/', include('fieldwork_app.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
