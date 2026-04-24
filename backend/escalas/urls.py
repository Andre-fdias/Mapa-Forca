from django.urls import path
from . import views

urlpatterns = [
    path('compor/', views.compor_mapa_view, name='compor_mapa'),
    path('buscar-funcionario/', views.buscar_funcionario_re, name='buscar_funcionario_re'),
    path('adicionar-viatura/<int:mapa_id>/', views.adicionar_viatura_mapa, name='adicionar_viatura_mapa'),
    path('alocar-funcionario/<int:alocacao_viatura_id>/', views.alocar_funcionario_viatura, name='alocar_funcionario_viatura'),
    path('mapa/<int:mapa_id>/update-cobom/', views.update_mapa_cobom, name='update_mapa_cobom'),
    path('remover-viatura/<int:alocacao_id>/', views.remover_viatura_mapa, name='remover_viatura_mapa'),
    path('remover-funcionario/<int:aloc_func_id>/', views.remover_funcionario_viatura, name='remover_funcionario_viatura'),
    path('atualizar-horario-alocacao/<int:aloc_func_id>/', views.atualizar_horario_alocacao, name='atualizar_horario_alocacao'),
    path('validar-mapa/<int:mapa_id>/', views.validar_mapa_final, name='validar_mapa_final'),
    path('get-viaturas/', views.get_viaturas_por_unidade, name='get_viaturas_por_unidade'),
    path('historico/', views.historico_view, name='historico_mapa'),
]
