from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.core.management import call_command
from django.http import HttpResponse
from rest_framework import viewsets, filters
from django_filters.rest_framework import DjangoFilterBackend
from .models import Unidade, Viatura, Posto, Municipio
from efetivo.models import Efetivo  # Usaremos Efetivo que tem os campos táticos
from dictionaries.models import Dictionary
from .serializers import UnidadeSerializer, ViaturaSerializer
from escalas.models import MapaDiario, AlocacaoViatura, AlocacaoFuncionario
from django.db.models import Q, Count, Sum
import datetime

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
    """Dashboard consolidado para Batalhão ou Posto específico."""
    if request.user.role in ['GRANDE_COMANDO', 'ADMIN', 'CENTRAL']:
        return dashboard_cobom(request)
        
    unidade_usuario = request.user.unidade
    hoje = timezone.now().date()
    
    # Busca as unidades (Postos) que devem aparecer no dashboard
    if request.user.role == 'BATALHAO':
        unidades = Unidade.objects.filter(parent=unidade_usuario, tipo_unidade__codigo='POSTO').order_by('nome')
    else:
        unidades = Unidade.objects.filter(id=unidade_usuario.id) if unidade_usuario else []
        
    data_postos = []
    total_completos = 0
    
    for unidade in unidades:
        mapa = MapaDiario.objects.filter(data=hoje, unidade=unidade).first()
        alocacoes_vtr = []
        esta_pronto = False
        
        if mapa:
            esta_pronto = True
            total_completos += 1
            alocacoes = AlocacaoViatura.objects.filter(mapa=mapa).select_related('viatura', 'status_no_dia')
            for aloc in alocacoes:
                cmt = AlocacaoFuncionario.objects.filter(alocacao_viatura=aloc, funcao__codigo='COMANDANTE').select_related('funcionario').first()
                alocacoes_vtr.append({
                    'prefixo': aloc.viatura.prefixo, 
                    'status': aloc.status_no_dia.nome if aloc.status_no_dia else 'N/D', 
                    'status_codigo': aloc.status_no_dia.codigo if aloc.status_no_dia else 'BAIXADO', 
                    'encarregado': cmt.funcionario.nome_guerra if cmt else 'S/ CMT'
                })
        
        data_postos.append({
            'unidade': unidade, 
            'viaturas': alocacoes_vtr, 
            'mapa_existe': bool(mapa),
            'esta_pronto': esta_pronto
        })
    
    mapa_completo = (total_completos == len(unidades)) if unidades else False
    
    return render(request, 'dashboard/batalhao.html', {
        'data_postos': data_postos, 
        'hoje': hoje,
        'mapa_completo': mapa_completo
    })

@login_required
def dashboard_cobom(request):
    """Dashboard Geral (COBOM/Grande Comando) com mapeamento fixo e dados REAIS."""
    hoje = timezone.now().date()
    total_unidades = 0
    total_completos = 0
    
    OPCOES_POR_SGB = {
      "2 - 1ºSGB": [
        "703151000 - CMT 1ºSGB", "703151100 - ADM PB CERRADO",
        "703151101 - EB CERRADO", "703151102 - EB ZONA NORTE",
        "703151200 - ADM PB SANTA ROSÁLIA", "703151201 - EB SANTA ROSÁLIA",
        "703151201-1 - TELEGRAFIA -EB SANTA ROSÁLIA", "703151202 - EB ÉDEN",
        "703151300 - ADM PB VOTORANTIM", "703151301 - EB VOTORANTIM",
        "703151302 - EB PIEDADE", "703151800 - ADM 1ºSGB"
      ],
      "3 - 2ºSGB": [
        "703152000 - CMT 2ºSGB", "703152100 - ADM PB ITU",
        "703152101 - EB ITU", "703152102 - EB PORTO FELIZ",
        "703152200 - ADM PB SALTO", "703152201 - EB SALTO",
        "703152300 - ADM PB SÃO ROQUE", "703152301 - EB SÃO ROQUE",
        "703152302 - EB IBIÚNA", "703152800 - ADM 2ºSGB",
        "703152900 - NUCL ATIV TEC 2ºSGB"
      ],
      "4 - 3ºSGB": [
        "703153000 - CMT 3ºSGB", "703153100 - ADM PB ITAPEVA",
        "703153101 - EB ITAPEVA", "703153102 - EB APIAÍ",
        "703153103 - EB ITARARÉ", "703153104 - EB CAPÃO BONITO",
        "703153800 - ADM 3ºSGB", "703153900 - NUCL ATIV TEC 3ºSGB"
      ],
      "5 - 4ºSGB": [
        "703154000 - CMT 4ºSGB", "703154100 - ADM PB ITAPETININGA",
        "703154101 - EB ITAPETININGA", "703154102 - EB BOITUVA",
        "703154103 - EB ANGATUBA", "703154200 - ADM PB TATUÍ",
        "703154201 - EB TATUÍ", "703154202 - EB TIETÊ",
        "703154203 - EB LARANJAL PAULISTA", "703154800 - ADM 4ºSGB",
        "703154900 - NUCL ATIV TEC 4ºSGB"
      ],
      "6 - 5ºSGB": [
        "703155000 - CMT 5ºSGB", "703155100 - ADM PB BOTUCATU",
        "703155101 - EB BOTUCATU", "703155102 - EB ITATINGA",
        "703155200 - ADM PB AVARÉ", "703155201 - EB AVARÉ",
        "703155202 - EB PIRAJU", "703155203 - EB ITAÍ",
        "703155800 - ADM 5ºSGB", "703155900 - NUCL ATIV TEC 5ºSGB"
      ],
    }
    
    sgbs_data = []
    
    for sgb_nome, postos_nomes in OPCOES_POR_SGB.items():
        postos_result = []
        for p_nome in postos_nomes:
            total_unidades += 1
            unidade = Unidade.objects.filter(nome=p_nome).first()
            
            viaturas_data = []
            esta_pronto = False
            mapa_existe = False
            
            stats = {
                'mergulhadores': 0,
                'dejem': 0,
                'ovb_leve': 0,
                'ovb_pesado': 0,
                'efetivo_total': 0
            }
            
            if unidade:
                mapa = MapaDiario.objects.filter(data=hoje, unidade=unidade).first()
                if mapa:
                    mapa_existe = True
                    esta_pronto = True
                    total_completos += 1
                    
                    # 1. Processar Viaturas (Operando e Reserva)
                    alocacoes_vtr = AlocacaoViatura.objects.filter(
                        mapa=mapa, 
                        status_no_dia__codigo__in=['OPERANDO', 'RESERVA']
                    ).select_related('viatura', 'status_no_dia')
                    
                    for aloc in alocacoes_vtr:
                        equipe = AlocacaoFuncionario.objects.filter(alocacao_viatura=aloc).select_related('funcionario', 'funcao')
                        cmt = equipe.filter(funcao__codigo='COMANDANTE').first()
                        
                        membros = []
                        for m in equipe:
                            # Busca dados táticos no modelo Efetivo sincronizado
                            efetivo_info = Efetivo.objects.filter(nome=m.funcionario.nome_guerra).first()
                            membros.append({
                                'nome': m.funcionario.nome_guerra,
                                'funcao': m.funcao.nome if m.funcao else 'AUX',
                                'mergulhador': 'SIM' in str(efetivo_info.mergulho).upper() if efetivo_info else False,
                                'ovb': efetivo_info.ovb if efetivo_info else None,
                                'dejem': False # Implementar flag de DEJEM no AlocacaoFuncionario se existir
                            })
                            
                            # Acumula stats globais do posto
                            if efetivo_info:
                                if 'SIM' in str(efetivo_info.mergulho).upper(): stats['mergulhadores'] += 1
                                if 'LEVE' in str(efetivo_info.ovb).upper(): stats['ovb_leve'] += 1
                                if 'PESADO' in str(efetivo_info.ovb).upper(): stats['ovb_pesado'] += 1
                            
                            stats['efetivo_total'] += 1

                        viaturas_data.append({
                            'prefixo': aloc.viatura.prefixo, 
                            'status': aloc.status_no_dia.nome,
                            'status_codigo': aloc.status_no_dia.codigo,
                            'num_pm': equipe.count(),
                            'encarregado': cmt.funcionario.nome_guerra if cmt else 'S/ CMT',
                            'equipe_completa': membros
                        })
            
            postos_result.append({
                'unidade': unidade if unidade else {'nome': p_nome, 'id': None}, 
                'viaturas': viaturas_data, 
                'mapa_existe': mapa_existe,
                'esta_pronto': esta_pronto,
                'stats': stats
            })
            
        sgbs_data.append({
            'nome': sgb_nome,
            'postos': postos_result
        })
    
    mapa_completo = (total_completos == total_unidades) if total_unidades > 0 else False
    
    return render(request, 'dashboard/cobom.html', {
        'sgbs': sgbs_data, 
        'hoje': hoje, 
        'mapa_completo': mapa_completo,
        'botoes_atalho': ['Aeroportos', 'Alarmes / Cód OPM', 'VTR Reserva', 'Normas do CB', 'Links / Intranet', 'Bairros', 'Pesquisa'],
        'oficiais': [
            {'cargo': 'Supervisor de Serviço', 'nome': 'CAP PM RODRIGUES', 'tipo': 'DIA'}, 
            {'cargo': 'Comando de Área', 'nome': '1º TEN PM COSTA', 'tipo': 'DIA'}, 
            {'cargo': 'Despachador', 'nome': 'SGT PM SILVA', 'tipo': 'NOITE'}
        ]
    })

# --- NOVA VIEW: CADASTRO DE VIATURAS ---

@login_required
def cadastro_viaturas_view(request):
    """Lista todas as viaturas com filtros e suporte a sincronização."""
    query = request.GET.get('q', '')
    status_filter = request.GET.get('status', '')
    sgb_filter = request.GET.get('sgb', '')
    garagem_filter = request.GET.get('garagem', '')
    
    viaturas = Viatura.objects.select_related('status_base', 'unidade_base').all()
    
    # Filtros de Texto (Busca)
    if query:
        viaturas = viaturas.filter(Q(prefixo__icontains=query) | Q(placa__icontains=query))
    
    # Filtros de Seleção (Exatos)
    if status_filter:
        viaturas = viaturas.filter(status_base__codigo=status_filter)
    if sgb_filter:
        viaturas = viaturas.filter(sgb=sgb_filter)
    if garagem_filter:
        viaturas = viaturas.filter(garagem=garagem_filter)
        
    # Listas Únicas para popular os Filtros Select
    # Usamos distinct() para evitar duplicatas e values_list para eficiência
    lista_sgb = Viatura.objects.exclude(sgb__isnull=True).values_list('sgb', flat=True).distinct().order_by('sgb')
    lista_garagem = Viatura.objects.exclude(garagem__isnull=True).values_list('garagem', flat=True).distinct().order_by('garagem')
    
    # Opções de Status baseadas no Dicionário
    status_options = Dictionary.objects.filter(tipo='STATUS_VIATURA').order_by('ordem')
        
    return render(request, 'unidades/cadastro_viaturas.html', {
        'viaturas': viaturas,
        'query': query,
        'status_filter': status_filter,
        'sgb_filter': sgb_filter,
        'garagem_filter': garagem_filter,
        'lista_sgb': lista_sgb,
        'lista_garagem': lista_garagem,
        'status_options': status_options
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

# --- NOVA VIEW: POSTOS DE ATENDIMENTO ---

@login_required
def lista_postos_view(request):
    """Lista todos os postos importados com busca."""
    query = request.GET.get('q', '')
    postos = Posto.objects.prefetch_related('municipios').all()
    
    if query:
        postos = postos.filter(Q(nome__icontains=query) | Q(sgb__icontains=query) | Q(cidade_posto__icontains=query))
        
    return render(request, 'unidades/lista_postos.html', {
        'postos': postos,
        'query': query
    })

@login_required
def sync_postos_sheets_action(request):
    """Action HTMX para sincronizar postos."""
    try:
        call_command('sync_postos_sheets')
        return HttpResponse('<div class="p-4 bg-emerald-500/20 text-emerald-400 rounded-2xl text-xs font-black uppercase tracking-widest animate-pulse">Postos sincronizados! Recarregando...<script>setTimeout(() => location.reload(), 2000)</script></div>')
    except Exception as e:
        return HttpResponse(f'<div class="p-4 bg-red-500/20 text-red-400 rounded-2xl text-xs font-bold">Erro: {str(e)}</div>')
