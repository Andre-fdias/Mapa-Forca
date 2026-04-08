from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.core.management import call_command
from django.http import HttpResponse
from rest_framework import viewsets, filters
from django_filters.rest_framework import DjangoFilterBackend
from .models import Unidade, Viatura
from .serializers import UnidadeSerializer, ViaturaSerializer
from escalas.models import MapaDiario, AlocacaoViatura, AlocacaoFuncionario
from django.db.models import Q

class UnidadeViewSet(viewsets.ModelViewSet):
    queryset = Unidade.objects.filter(ativo=True)
    serializer_class = UnidadeSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ['nome']

class ViaturaViewSet(viewsets.ModelViewSet):
    queryset = Viatura.objects.all()
    serializer_class = ViaturaSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status_base', 'unidade_base']
    search_fields = ['prefixo', 'placa']
    ordering = ['prefixo']

@login_required
def dashboard_batalhao(request):
    """Dashboard consolidado."""
    if request.user.role in ['GRANDE_COMANDO', 'ADMIN', 'CENTRAL']:
        return dashboard_cobom(request)
    unidade_usuario = request.user.unidade
    hoje = timezone.now().date()
    if request.user.role == 'BATALHAO':
        unidades = Unidade.objects.filter(parent=unidade_usuario)
    else:
        unidades = Unidade.objects.filter(id=unidade_usuario.id) if unidade_usuario else []
    data_postos = []
    for unidade in unidades:
        mapa = MapaDiario.objects.filter(data=hoje, unidade=unidade).first()
        alocacoes_vtr = []
        if mapa:
            alocacoes = AlocacaoViatura.objects.filter(mapa=mapa).select_related('viatura', 'status_no_dia')
            for aloc in alocacoes:
                cmt = AlocacaoFuncionario.objects.filter(alocacao_viatura=aloc, funcao__codigo='COMANDANTE').select_related('funcionario').first()
                alocacoes_vtr.append({'prefixo': aloc.viatura.prefixo, 'status': aloc.status_no_dia.nome if aloc.status_no_dia else 'N/D', 'status_codigo': aloc.status_no_dia.codigo if aloc.status_no_dia else 'BAIXADO', 'encarregado': cmt.funcionario.nome_guerra if cmt else 'S/ CMT'})
        data_postos.append({'unidade': unidade, 'viaturas': alocacoes_vtr, 'mapa_existe': bool(mapa)})
    return render(request, 'dashboard/batalhao.html', {'data_postos': data_postos, 'hoje': hoje})

@login_required
def dashboard_cobom(request):
    hoje = timezone.now().date()
    sgbs = []
    for i in range(1, 6):
        nome_sgb = f"{i}º SGB"
        unidade_sgb = Unidade.objects.filter(nome__icontains=nome_sgb, tipo_unidade__codigo='BATALHAO').first()
        postos_data = []
        if unidade_sgb:
            postos = Unidade.objects.filter(parent=unidade_sgb).order_by('nome')
            for posto in postos:
                mapa = MapaDiario.objects.filter(data=hoje, unidade=posto).first()
                viaturas = []
                if mapa:
                    alocacoes = AlocacaoViatura.objects.filter(mapa=mapa).select_related('viatura', 'status_no_dia')
                    for aloc in alocacoes:
                        cmt = AlocacaoFuncionario.objects.filter(alocacao_viatura=aloc, funcao__codigo='COMANDANTE').select_related('funcionario').first()
                        viaturas.append({'prefixo': aloc.viatura.prefixo, 'status_codigo': aloc.status_no_dia.codigo if aloc.status_no_dia else 'BAIXADO', 'encarregado': cmt.funcionario.nome_guerra if cmt else 'S/ CMT'})
                postos_data.append({'unidade': posto, 'viaturas': viaturas, 'mapa_existe': bool(mapa)})
        sgbs.append({'nome': nome_sgb, 'postos': postos_data})
    return render(request, 'dashboard/cobom.html', {'sgbs': sgbs, 'hoje': hoje, 'botoes_atalho': ['Aeroportos', 'Alarmes / Cód OPM', 'VTR Reserva', 'Normas do CB', 'Links / Intranet', 'Bairros', 'Pesquisa'], 'oficiais': [{'cargo': 'Supervisor de Serviço', 'nome': 'CAP PM RODRIGUES', 'tipo': 'DIA'}, {'cargo': 'Comando de Área', 'nome': '1º TEN PM COSTA', 'tipo': 'DIA'}, {'cargo': 'Despachador', 'nome': 'SGT PM SILVA', 'tipo': 'NOITE'}]})

# --- NOVA VIEW: CADASTRO DE VIATURAS ---

@login_required
def cadastro_viaturas_view(request):
    """Lista todas as viaturas com filtros e suporte a sincronização."""
    query = request.GET.get('q', '')
    status_filter = request.GET.get('status', '')
    
    viaturas = Viatura.objects.select_related('status_base', 'unidade_base').all()
    
    if query:
        viaturas = viaturas.filter(Q(prefixo__icontains=query) | Q(placa__icontains=query))
    if status_filter:
        viaturas = viaturas.filter(status_base__codigo=status_filter)
        
    return render(request, 'unidades/cadastro_viaturas.html', {
        'viaturas': viaturas,
        'query': query,
        'status_filter': status_filter
    })

@login_required
def sync_sheets_action(request):
    """Action HTMX para disparar o comando de sincronização."""
    try:
        # Chama o comando de gerenciamento internamente
        call_command('sync_viaturas_sheets')
        return HttpResponse('<div class="p-4 bg-emerald-500/20 text-emerald-400 rounded-2xl text-xs font-black uppercase tracking-widest animate-pulse">Sincronização realizada com sucesso! Recarregando...<script>setTimeout(() => location.reload(), 2000)</script></div>')
    except Exception as e:
        return HttpResponse(f'<div class="p-4 bg-red-500/20 text-red-400 rounded-2xl text-xs font-bold">Erro: {str(e)}</div>')
