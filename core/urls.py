from django.contrib import admin
from django.urls import path, include
from rest_framework import routers
from efetivo.views import FuncionarioViewSet
from unidades.views import UnidadeViewSet, ViaturaViewSet, dashboard_batalhao
from escalas.views import MapaDiarioViewSet, AlocacaoFuncionarioViewSet, AlocacaoViaturaViewSet
from dictionaries.views import DictionaryViewSet
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

router = routers.DefaultRouter()
router.register(r'funcionarios', FuncionarioViewSet)
router.register(r'unidades', UnidadeViewSet)
router.register(r'viaturas', ViaturaViewSet)
router.register(r'mapas', MapaDiarioViewSet)
router.register(r'alocacoes-funcionarios', AlocacaoFuncionarioViewSet)
router.register(r'alocacoes-viaturas', AlocacaoViaturaViewSet)
router.register(r'dictionaries', DictionaryViewSet)

from django.views.generic import TemplateView
from django.http import HttpResponse

def htmx_test(request):
    return HttpResponse("<span class='text-green-600 font-bold'>Sucesso! A requisição HTMX e o TailwindCSS estão funcionando perfeitamente!</span>")

urlpatterns = [
    path('', dashboard_batalhao, name='home'),
    path('api/htmx-test/', htmx_test, name='htmx_test'),
    path('admin/', admin.site.urls),
    path('api/', include(router.urls)),
    path('escalas/', include('escalas.urls')),
    path('unidades/', include('unidades.urls')),
    path('efetivo/', include('efetivo.urls')),
    path('tickets/', include('tickets.urls')),
    path('accounts/', include('accounts.urls')),
    
    # Auth
    path('api/auth/', include('dj_rest_auth.urls')),
    path('api/auth/registration/', include('dj_rest_auth.registration.urls')),
    path('api/auth/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    
    # Social Auth (Google)
    path('accounts/', include('allauth.urls')),
    
    # Tailwind browser reload
    path("__reload__/", include("django_browser_reload.urls")),
]
