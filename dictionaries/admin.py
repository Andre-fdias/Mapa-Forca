from django.contrib import admin
from .models import Dictionary

@admin.register(Dictionary)
class DictionaryAdmin(admin.ModelAdmin):
    list_display = ('tipo', 'codigo', 'nome', 'ativo', 'ordem')
    list_filter = ('tipo', 'ativo')
    search_fields = ('tipo', 'codigo', 'nome')
    ordering = ('tipo', 'ordem', 'nome')
