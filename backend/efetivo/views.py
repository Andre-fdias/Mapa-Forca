from django.shortcuts import render
from rest_framework import viewsets, filters
from django_filters.rest_framework import DjangoFilterBackend
from .models import Funcionario, Efetivo
from .serializers import FuncionarioSerializer
from django.db.models import Q
from django.core.management import call_command
from django.http import HttpResponse

class FuncionarioViewSet(viewsets.ModelViewSet):
    queryset = Funcionario.objects.all()
    serializer_class = FuncionarioSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['posto_graduacao']
    search_fields = ['nome_completo', 'nome_guerra', 're']
    ordering_fields = ['posto_graduacao', 'nome_completo', 're']
    ordering = ['posto_graduacao', 'nome_completo']

def sync_efetivo_action(request):
    """Action HTMX para disparar o comando de sincronização do efetivo."""
    try:
        call_command('sync_efetivo_sheets')
        return HttpResponse('<div class="px-6 py-3 bg-emerald-500/20 text-emerald-400 rounded-2xl text-[10px] font-black uppercase tracking-widest animate-pulse border border-emerald-500/30">Sucesso! Recarregando...<script>setTimeout(() => location.reload(), 1500)</script></div>')
    except Exception as e:
        return HttpResponse(f'<div class="px-6 py-3 bg-red-500/20 text-red-400 rounded-2xl text-[10px] font-bold border border-red-500/30">Erro: {str(e)}</div>')

def lista_efetivo_importado(request):
    query = request.GET.get('q', '')
    unidade_filter = request.GET.get('unidade', '')
    sgb_filter = request.GET.get('sgb', '')
    secao_filter = request.GET.get('secao', '')
    
    efetivo = Efetivo.objects.all().order_by('nome')
    
    # Normalização em memória para exibição/fallback se necessário
    # mas o ideal é filtrar no banco.
    
    if query:
        efetivo = efetivo.filter(Q(nome__icontains=query) | Q(re__icontains=query) | Q(nome_do_pm__icontains=query))
    if unidade_filter:
        efetivo = efetivo.filter(unidade=unidade_filter)
    if sgb_filter:
        efetivo = efetivo.filter(sgb=sgb_filter)
    if secao_filter:
        efetivo = efetivo.filter(posto_secao=secao_filter)

    # --- LÓGICA DE FILTROS ---
    # Lista todas as Unidades disponíveis (removendo None e vazios)
    lista_unidades = Efetivo.objects.exclude(unidade__isnull=True).exclude(unidade='').values_list('unidade', flat=True).distinct().order_by('unidade')
    
    # Lista todos os SGBs baseados na unidade selecionada
    base_sgbs = Efetivo.objects.all()
    if unidade_filter:
        base_sgbs = base_sgbs.filter(unidade=unidade_filter)
    lista_sgb = base_sgbs.exclude(sgb__isnull=True).exclude(sgb='').values_list('sgb', flat=True).distinct().order_by('sgb')
    
    # Lista as Seções baseadas na unidade e no SGB selecionado
    base_secoes = Efetivo.objects.all()
    if unidade_filter:
        base_secoes = base_secoes.filter(unidade=unidade_filter)
    if sgb_filter:
        base_secoes = base_secoes.filter(sgb=sgb_filter)
        
    lista_secoes = base_secoes.exclude(posto_secao__isnull=True).exclude(posto_secao='').values_list('posto_secao', flat=True).distinct().order_by('posto_secao')
        
    return render(request, 'efetivo/lista_importada.html', {
        'efetivo': efetivo,
        'query': query,
        'unidade_filter': unidade_filter,
        'sgb_filter': sgb_filter,
        'secao_filter': secao_filter,
        'lista_unidades': lista_unidades,
        'lista_sgb': lista_sgb,
        'lista_secoes': lista_secoes
    })
