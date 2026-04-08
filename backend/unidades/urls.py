from django.urls import path
from . import views

urlpatterns = [
    path('dashboard/', views.dashboard_batalhao, name='dashboard_batalhao'),
    path('cadastro-viaturas/', views.cadastro_viaturas_view, name='cadastro_viaturas'),
    path('sync-sheets/', views.sync_sheets_action, name='sync_viaturas_sheets'),
]
