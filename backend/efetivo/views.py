from django.shortcuts import render
from rest_framework import viewsets, filters
from django_filters.rest_framework import DjangoFilterBackend
from .models import Funcionario, Efetivo
from .serializers import FuncionarioSerializer

class FuncionarioViewSet(viewsets.ModelViewSet):
    queryset = Funcionario.objects.all()
    serializer_class = FuncionarioSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['posto_graduacao']
    search_fields = ['nome_completo', 'nome_guerra', 're']
    ordering_fields = ['posto_graduacao', 'nome_completo', 're']
    ordering = ['posto_graduacao', 'nome_completo']

from django.core.management import call_command
from django.http import HttpResponse

def sync_efetivo_action(request):
    """Action HTMX para disparar o comando de sincronização do efetivo."""
    try:
        call_command('sync_efetivo_sheets')
        return HttpResponse('<div class="px-6 py-3 bg-emerald-500/20 text-emerald-400 rounded-2xl text-[10px] font-black uppercase tracking-widest animate-pulse border border-emerald-500/30">Sucesso! Recarregando...<script>setTimeout(() => location.reload(), 1500)</script></div>')
    except Exception as e:
        return HttpResponse(f'<div class="px-6 py-3 bg-red-500/20 text-red-400 rounded-2xl text-[10px] font-bold border border-red-500/30">Erro: {str(e)}</div>')

def lista_efetivo_importado(request):
    query = request.GET.get('q', '')
    efetivo = Efetivo.objects.all().order_by('nome')
    
    if query:
        efetivo = efetivo.filter(nome__icontains=query)
        
    return render(request, 'efetivo/lista_importada.html', {
        'efetivo': efetivo,
        'query': query
    })
