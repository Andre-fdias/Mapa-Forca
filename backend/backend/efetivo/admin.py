from django.contrib import admin
from .models import Funcionario, Efetivo

@admin.register(Funcionario)
class FuncionarioAdmin(admin.ModelAdmin):
    list_display = ('posto_graduacao', 're', 'nome_guerra', 'nome_completo')
    search_fields = ('re', 'nome_completo', 'nome_guerra')
    list_filter = ('posto_graduacao',)

@admin.register(Efetivo)
class EfetivoAdmin(admin.ModelAdmin):
    list_display = ('nome', 'fonte', 'data_importacao')
    search_fields = ('nome',)
    list_filter = ('fonte', 'data_importacao')
    readonly_fields = ('data_importacao',)
