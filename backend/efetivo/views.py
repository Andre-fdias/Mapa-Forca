from django.shortcuts import render
from django.contrib.auth.decorators import login_required
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

from django.db.models import Count
from escalas.models import AlocacaoFuncionario
from django.utils import timezone

@login_required
def relatorio_efetivo_view(request):
    if not (request.user.is_superuser or request.user.role in ['ADMIN', 'COBOM']):
        return redirect('/')

    user = request.user
    hoje = timezone.localtime(timezone.now()).date()
    
    # Parâmetros de Filtro
    unidade_sel = request.GET.get('unidade', '')
    sgb_sel = request.GET.get('sgb', '')
    posto_sel = request.GET.get('posto', '')
    
    efetivo_qs = Efetivo.objects.all()
    aloc_qs = AlocacaoFuncionario.objects.filter(mapa__data=hoje)

    # Filtro Dinâmico
    if unidade_sel:
        efetivo_qs = efetivo_qs.filter(unidade=unidade_sel)
        aloc_qs = aloc_qs.filter(Q(mapa__unidade__nome=unidade_sel) | Q(mapa__unidade__parent__nome=unidade_sel))
    if sgb_sel:
        efetivo_qs = efetivo_qs.filter(sgb=sgb_sel)
        # Tenta filtrar alocação pelo SGB (que geralmente é o parent da unidade do mapa)
        aloc_qs = aloc_qs.filter(mapa__unidade__parent__nome=sgb_sel)
    if posto_sel:
        efetivo_qs = efetivo_qs.filter(posto_secao=posto_sel)
        aloc_qs = aloc_qs.filter(mapa__unidade__nome=posto_sel)

    # --- AGREGAÇÃO DE DADOS ---
    total_efetivo = efetivo_qs.count()
    total_escalados = aloc_qs.values('funcionario').distinct().count()
    
    # 1. Distribuição por Unidade (Top 10)
    dist_unidade = list(efetivo_qs.values('unidade').annotate(total=Count('id')).order_by('-total')[:10])
    
    # 2. Especialidades
    mergulhadores = efetivo_qs.filter(Q(mergulho__icontains='SIM') | Q(mergulho__icontains='S')).count()
    ovb = efetivo_qs.filter(Q(ovb__icontains='SIM') | Q(ovb__icontains='S')).count()
    
    # 3. Postos/Graduações
    func_qs = Funcionario.objects.filter(re__in=efetivo_qs.values_list('re', flat=True))
    dist_postos = list(func_qs.values('posto_graduacao__nome').annotate(total=Count('re')).order_by('posto_graduacao__ordem'))

    # 4. Dados de Água (Agregados)
    from django.db.models import Sum
    vtrs_base = aloc_qs.filter(alocacao_viatura__isnull=False)
    
    # Água por SGB
    dist_agua_sgb = list(vtrs_base.values('mapa__unidade__parent__nome')
                        .annotate(total_agua=Sum('alocacao_viatura__viatura__vol_agua'))
                        .filter(total_agua__gt=0).order_by('-total_agua')[:10])
    
    # Água por Posto
    dist_agua_posto = list(vtrs_base.values('mapa__unidade__nome')
                          .annotate(total_agua=Sum('alocacao_viatura__viatura__vol_agua'))
                          .filter(total_agua__gt=0).order_by('-total_agua')[:10])

    total_agua = vtrs_base.aggregate(Sum('alocacao_viatura__viatura__vol_agua'))['alocacao_viatura__viatura__vol_agua__sum'] or 0

    # Listas para os filtros (Opções Dinâmicas)
    lista_unidades = Efetivo.objects.exclude(unidade__isnull=True).exclude(unidade='').values_list('unidade', flat=True).distinct().order_by('unidade')
    lista_sgb = Efetivo.objects.filter(unidade=unidade_sel).exclude(sgb__isnull=True).exclude(sgb='').values_list('sgb', flat=True).distinct().order_by('sgb') if unidade_sel else []
    lista_postos = Efetivo.objects.filter(sgb=sgb_sel).exclude(posto_secao__isnull=True).exclude(posto_secao='').values_list('posto_secao', flat=True).distinct().order_by('posto_secao') if sgb_sel else []

    context = {
        'total_efetivo': total_efetivo,
        'total_escalados': total_escalados,
        'dist_unidade': dist_unidade,
        'mergulhadores': mergulhadores,
        'ovb': ovb,
        'dist_postos': dist_postos,
        'dist_agua_sgb': dist_agua_sgb,
        'dist_agua_posto': dist_agua_posto,
        'total_agua': total_agua,
        'hoje': hoje,
        'unidades': lista_unidades,
        'sgbs': lista_sgb,
        'postos_list': lista_postos,
        'unidade_sel': unidade_sel,
        'sgb_sel': sgb_sel,
        'posto_sel': posto_sel
    }
    
    return render(request, 'efetivo/relatorios.html', context)



def lista_efetivo_importado(request):
    user = request.user
    query = request.GET.get('q', '')
    unidade_filter = request.GET.get('unidade', '')
    sgb_filter = request.GET.get('sgb', '')
    secao_filter = request.GET.get('secao', '')
    
    efetivo_qs = Efetivo.objects.all().order_by('nome')

    # --- LÓGICA DE PERMISSÕES ---
    is_global_user = user.is_superuser or user.role in ['ADMIN', 'COBOM']
    
    gb_unidade = None
    if not is_global_user:
        if user.unidade:
            # Sobe na hierarquia para encontrar o GB (Batalhão)
            curr = user.unidade
            while curr:
                if curr.tipo_unidade and curr.tipo_unidade.codigo == 'BATALHAO':
                    gb_unidade = curr
                    break
                if 'GB' in curr.nome.upper() and 'SGB' not in curr.nome.upper():
                    gb_unidade = curr
                    break
                curr = curr.parent
            
            if not gb_unidade:
                gb_unidade = user.unidade.root_unit

            if gb_unidade:
                # Extrai o número do GB (ex: "07" ou "7")
                match = re.search(r'(\d+)', gb_unidade.nome)
                if match:
                    unidade_num = match.group(1).lstrip('0')
                    efetivo_qs = efetivo_qs.filter(
                        Q(unidade__icontains=f"{unidade_num}º GB") | 
                        Q(unidade__icontains=f"0{unidade_num}º GB") |
                        Q(unidade__icontains=f"{unidade_num} GB")
                    )
                else:
                    efetivo_qs = efetivo_qs.filter(unidade__icontains=gb_unidade.nome)
        else:
            efetivo_qs = efetivo_qs.none()
    
    # --- FILTROS DE BUSCA ---
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

    # --- LÓGICA DE OPÇÕES DOS FILTROS ---
    perm_based_qs = Efetivo.objects.all()
    if not is_global_user and gb_unidade:
        match = re.search(r'(\d+)', gb_unidade.nome)
        if match:
            unidade_num = match.group(1).lstrip('0')
            perm_based_qs = perm_based_qs.filter(
                Q(unidade__icontains=f"{unidade_num}º GB") | 
                Q(unidade__icontains=f"0{unidade_num}º GB") |
                Q(unidade__icontains=f"{unidade_num} GB")
            )
        else:
            perm_based_qs = perm_based_qs.filter(unidade__icontains=gb_unidade.nome)
    elif not is_global_user:
        perm_based_qs = perm_based_qs.none()

    lista_unidades = perm_based_qs.exclude(unidade__isnull=True).exclude(unidade='').values_list('unidade', flat=True).distinct().order_by('unidade')
    
    base_sgbs = perm_based_qs
    if unidade_filter:
        base_sgbs = base_sgbs.filter(unidade=unidade_filter)
    lista_sgb = base_sgbs.exclude(sgb__isnull=True).exclude(sgb='').values_list('sgb', flat=True).distinct().order_by('sgb')
    
    base_secoes = perm_based_qs
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
