from django.contrib import admin
from .models import Ticket, TicketMessage

class TicketMessageInline(admin.TabularInline):
    model = TicketMessage
    extra = 1

@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = ('id', 'titulo', 'requisitante', 'status', 'prioridade', 'criado_em')
    list_filter = ('status', 'prioridade', 'categoria')
    search_fields = ('titulo', 'descricao', 'requisitante__email')
    inlines = [TicketMessageInline]
    readonly_fields = ('criado_em', 'atualizado_em')

@admin.register(TicketMessage)
class TicketMessageAdmin(admin.ModelAdmin):
    list_display = ('id', 'ticket', 'autor', 'criado_em')
    list_filter = ('criado_em',)
