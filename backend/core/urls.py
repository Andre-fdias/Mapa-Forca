from django.contrib import admin
from django.urls import path, include
from rest_framework import routers
from employees.views import FuncionarioViewSet
from resources.views import PostoViewSet, ViaturaViewSet
from maps.views import MapaDiarioViewSet, AlocacaoFuncionarioViewSet, AlocacaoViaturaViewSet
from dictionaries.views import DictionaryViewSet
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

router = routers.DefaultRouter()
router.register(r'funcionarios', FuncionarioViewSet)
router.register(r'postos', PostoViewSet)
router.register(r'viaturas', ViaturaViewSet)
router.register(r'mapas', MapaDiarioViewSet)
router.register(r'alocacoes-funcionarios', AlocacaoFuncionarioViewSet)
router.register(r'alocacoes-viaturas', AlocacaoViaturaViewSet)
router.register(r'dictionaries', DictionaryViewSet)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include(router.urls)),
    
    # Auth
    path('api/auth/', include('dj_rest_auth.urls')),
    path('api/auth/registration/', include('dj_rest_auth.registration.urls')),
    path('api/auth/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    
    # Social Auth (Google)
    path('api/auth/social/', include('accounts.urls')),
    path('accounts/', include('allauth.urls')),
]
