from django.shortcuts import render
from rest_framework import viewsets, filters
from django_filters.rest_framework import DjangoFilterBackend
from .models import Funcionario, Efetivo
from .serializers import FuncionarioSerializer
from django.db.models import Q
from django.core.management import call_command
from django.http import HttpResponse
import re

def normalize_phone_for_whatsapp(telefone):
    if not telefone:
        return None
    digits = re.sub(r'\D+', '', str(telefone))
    if not digits:
        return None
    if digits.startswith('00'):
        digits = digits[2:]
    if digits.startswith('55'):
        return digits
    if digits.startswith('0'):
        digits = digits.lstrip('0')
    return f'55{digits}'

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
    
    efetivo_qs = Efetivo.objects.all().order_by('nome')
    
    if query:
        efetivo_qs = efetivo_qs.filter(Q(nome__icontains=query) | Q(re__icontains=query) | Q(nome_do_pm__icontains=query))
    if unidade_filter:
        efetivo_qs = efetivo_qs.filter(unidade=unidade_filter)
    if sgb_filter:
        efetivo_qs = efetivo_qs.filter(sgb=sgb_filter)
    if secao_filter:
        efetivo_qs = efetivo_qs.filter(posto_secao=secao_filter)

    # Processamento adicional (Telefone Link)
    efetivo_list = list(efetivo_qs)
    for m in efetivo_list:
        if m.telefone:
            m.tel_link = normalize_phone_for_whatsapp(m.telefone)

    # --- LÓGICA DE FILTROS ---
    lista_unidades = Efetivo.objects.exclude(unidade__isnull=True).exclude(unidade='').values_list('unidade', flat=True).distinct().order_by('unidade')
    
    base_sgbs = Efetivo.objects.all()
    if unidade_filter:
        base_sgbs = base_sgbs.filter(unidade=unidade_filter)
    lista_sgb = base_sgbs.exclude(sgb__isnull=True).exclude(sgb='').values_list('sgb', flat=True).distinct().order_by('sgb')
    
    base_secoes = Efetivo.objects.all()
    if unidade_filter:
        base_secoes = base_secoes.filter(unidade=unidade_filter)
    if sgb_filter:
        base_secoes = base_secoes.filter(sgb=sgb_filter)
        
    lista_secoes = base_secoes.exclude(posto_secao__isnull=True).exclude(posto_secao='').values_list('posto_secao', flat=True).distinct().order_by('posto_secao')
        
    return render(request, 'efetivo/lista_importada.html', {
        'efetivo': efetivo_list,
        'query': query,
        'unidade_filter': unidade_filter,
        'sgb_filter': sgb_filter,
        'secao_filter': secao_filter,
        'lista_unidades': lista_unidades,
        'lista_sgb': lista_sgb,
        'lista_secoes': lista_secoes
    })
