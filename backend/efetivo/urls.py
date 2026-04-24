from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import FuncionarioViewSet, lista_efetivo_importado, sync_efetivo_action

router = DefaultRouter()
router.register(r'funcionarios', FuncionarioViewSet)

urlpatterns = [
    path('importado/', lista_efetivo_importado, name='lista_efetivo_importado'),
    path('sync-sheets/', sync_efetivo_action, name='sync_efetivo_sheets'),
    path('', include(router.urls)),
]
