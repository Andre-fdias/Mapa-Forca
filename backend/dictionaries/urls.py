from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import DictionaryViewSet, abrir_modal_funcao, salvar_nova_funcao

router = DefaultRouter()
router.register(r'dictionaries', DictionaryViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('adicionar-funcao-modal/', abrir_modal_funcao, name='abrir_modal_funcao'),
    path('salvar-funcao/', salvar_nova_funcao, name='salvar_nova_funcao'),
]
