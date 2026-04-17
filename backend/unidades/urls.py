from django.urls import path
from . import views

urlpatterns = [
    path('dashboard/', views.dashboard_batalhao, name='dashboard_batalhao'),
    path('visao-cobom/', views.visao_cobom_efetivo_view, name='visao_cobom_efetivo'),
    path('cadastro-viaturas/', views.cadastro_viaturas_view, name='cadastro_viaturas'),
    path('sync-sheets/', views.sync_sheets_action, name='sync_viaturas_sheets'),
    path('postos/', views.lista_postos_view, name='lista_postos'),
    path('sync-postos/', views.sync_postos_sheets_action, name='sync_postos_sheets'),
]
