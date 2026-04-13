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
import re

def get_data_operacional():
    """
    Retorna a data operacional baseada no horário de reset (07:40).
    Se for antes das 07:40, ainda é a data do dia anterior.
    """
    agora = timezone.localtime(timezone.now())
    horario_reset = agora.replace(hour=7, minute=40, second=0, microsecond=0)
    
    if agora < horario_reset:
        return (agora - datetime.timedelta(days=1)).date()
    return agora.date()

def format_militar_display(funcionario, efetivo_info):
    """Garante o formato GRADUAÇÃO + NOME DE GUERRA limpo, sem duplicidade ou quebras de linha."""
    ranks = [
        'CEL PM', 'TEN CEL PM', 'MAJ PM', 'CAP PM', '1º TEN PM', '2º TEN PM', 'ASP PM', 
        'SUBTEN PM', '1º SGT PM', '2º SGT PM', '3º SGT PM', 'CB PM', 'SD PM',
        '1 SGT PM', '2 SGT PM', '3 SGT PM', '1 TEN PM', '2 TEN PM'
    ]
    
    # 1. Determina a Graduação
    p_limpo = ""
    if efetivo_info and efetivo_info.posto_secao:
        p_txt = str(efetivo_info.posto_secao).upper()
        for r in ranks:
            if r in p_txt:
                p_limpo = r
                break
    
    if not p_limpo and funcionario and funcionario.posto_graduacao:
        p_limpo = funcionario.posto_graduacao.nome.upper()
    
    # Normalização de graduação (ex: 1 SGT PM -> 1º SGT PM)
    if p_limpo:
        p_limpo = p_limpo.replace('1 SGT', '1º SGT').replace('2 SGT', '2º SGT').replace('3 SGT', '3º SGT')
        p_limpo = p_limpo.replace('1 TEN', '1º TEN').replace('2 TEN', '2º TEN')

    # 2. Determina o Nome de Guerra
    n_limpo = ""
    if efetivo_info and efetivo_info.nome:
        n_txt = str(efetivo_info.nome).upper()
        
        # Limpeza de códigos, REs e parênteses
        n_txt = re.sub(r'\d{6}-\d{1}', '', n_txt)
        n_txt = re.sub(r'\(.*?\)', '', n_txt)
        n_txt = re.sub(r'\d{4,}', '', n_txt)
        
        # REMOVE GRADUAÇÕES DO NOME para evitar duplicação (1º SGT PM 1º SGT PM)
        for r in ranks:
            n_txt = n_txt.replace(r, '').replace(r.replace('º', ''), '')
            
        n_txt = re.sub(r'[.\-\/_]', ' ', n_txt)
        n_limpo = n_txt.strip()
    
    if not n_limpo and funcionario:
        n_limpo = (funcionario.nome_guerra or "").upper().strip()

    # 3. Resultado Final (Garante linha única e espaços simples)
    final = f"{p_limpo} {n_limpo}".strip().upper()
    final = " ".join(final.split()) # Remove newlines e espaços duplos
    
    if not final and funcionario:
        return funcionario.nome_curto.upper()
    
    return final or "S/ NOME"

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
    """Dashboard principal. Redireciona para o COBOM (Geral) por padrão para ver tudo."""
    if request.GET.get('view') == 'batalhao':
        unidade_usuario = request.user.unidade
        hoje = get_data_operacional()
        
        if unidade_usuario and unidade_usuario.tipo_unidade and unidade_usuario.tipo_unidade.codigo == 'BATALHAO':
            unidades = Unidade.objects.filter(parent=unidade_usuario, tipo_unidade__codigo='POSTO').order_by('nome')
        else:
            unidades = Unidade.objects.filter(tipo_unidade__codigo='POSTO').order_by('nome')
            
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
                    equipe = AlocacaoFuncionario.objects.filter(alocacao_viatura=aloc).select_related('funcionario__posto_graduacao')
                    cmt = equipe.filter(funcao__codigo='COMANDANTE').first()
                    if not cmt: cmt = equipe.first()
                    
                    nome_enc = "S/ CMT"
                    if cmt:
                        ef_info = Efetivo.objects.filter(Q(re=cmt.funcionario.re) | Q(nome__icontains=cmt.funcionario.nome_guerra)).first()
                        nome_enc = format_militar_display(cmt.funcionario, ef_info)

                    alocacoes_vtr.append({
                        'prefixo': aloc.viatura.prefixo, 
                        'status': aloc.status_no_dia.nome if aloc.status_no_dia else 'N/D', 
                        'status_codigo': aloc.status_no_dia.codigo if aloc.status_no_dia else 'BAIXADO', 
                        'encarregado': nome_enc
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
    
    return dashboard_cobom(request)

@login_required
def dashboard_cobom(request):
    """Dashboard Geral (COBOM/Grande Comando) com mapeamento fixo e dados REAIS."""
    hoje = get_data_operacional()
    total_unidades = 0
    total_completos = 0
    
    global_stats = {
        'vtrs_operando': 0,
        'militares_escalados': 0,
        'mergulhadores': 0,
        'dejem': 0,
        'motoristas': 0
    }
    
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
    vtrs_reserva_global = []
    
    for sgb_nome, postos_nomes in OPCOES_POR_SGB.items():
        postos_result = []
        for p_nome in postos_nomes:
            unidade = None
            posto_obj_real = None
            if " - " in p_nome:
                partes = p_nome.split(" - ")
                codigo = partes[0].strip()
                nome_limpo = partes[1].strip()
                unidade = Unidade.objects.filter(Q(codigo_secao=codigo) | Q(nome=nome_limpo)).first()
                posto_obj_real = Posto.objects.filter(Q(cod_secao=codigo) | Q(nome__icontains=nome_limpo)).first()
            else:
                unidade = Unidade.objects.filter(nome=p_nome).first()
                posto_obj_real = Posto.objects.filter(nome__icontains=p_nome).first()

            is_operacional = False
            if posto_obj_real and posto_obj_real.operacional_adm:
                if "OPERACIONAL" in str(posto_obj_real.operacional_adm).upper():
                    is_operacional = True
            
            if not is_operacional:
                continue

            total_unidades += 1
            viaturas_data = []
            esta_pronto = False
            mapa_existe = False
            
            telegrafista_info = {
                'nome': "AGUARDANDO...",
                'is_dejem': False,
                'horario': ""
            }
            
            stats = {
                'mergulhadores': 0,
                'dejem': 0,
                'ovb_leve': 0,
                'ovb_pesado': 0,
                'efetivo_total': 0,
                'vtrs_total': 0,
                'vtrs_operando': 0
            }
            
            if unidade:
                mapa = MapaDiario.objects.filter(data=hoje, unidade=unidade).first()
                if mapa:
                    mapa_existe = True
                    esta_pronto = True
                    total_completos += 1
                    
                    prefixos_tel = ['TELEGRAFISTA', 'TELEGRAFIA']

                    alocacoes_vtr = AlocacaoViatura.objects.filter(
                        mapa=mapa, 
                        status_no_dia__codigo__in=['OPERANDO', 'RESERVA']
                    ).select_related('viatura', 'status_no_dia').exclude(viatura__prefixo__in=prefixos_tel)
                    
                    stats['vtrs_total'] = alocacoes_vtr.count()
                    
                    aloc_tel = AlocacaoViatura.objects.filter(mapa=mapa, viatura__prefixo__in=prefixos_tel).first()
                    if aloc_tel:
                        tel_func = AlocacaoFuncionario.objects.filter(alocacao_viatura=aloc_tel).select_related('funcionario__posto_graduacao').first()
                        if tel_func:
                            ef_tel = Efetivo.objects.filter(Q(re=tel_func.funcionario.re) | Q(nome__icontains=tel_func.funcionario.nome_guerra)).first()
                            telegrafista_info['nome'] = format_militar_display(tel_func.funcionario, ef_tel)
                            telegrafista_info['is_dejem'] = tel_func.dejem
                            if tel_func.dejem and tel_func.inicio_dejem:
                                telegrafista_info['horario'] = f"{tel_func.inicio_dejem.strftime('%H:%M')} > {tel_func.termino_dejem.strftime('%H:%M')}"
                            
                            global_stats['militares_escalados'] += 1
                            if tel_func.dejem:
                                global_stats['dejem'] += 1

                    for aloc in alocacoes_vtr:
                        if aloc.status_no_dia.codigo == 'OPERANDO':
                            stats['vtrs_operando'] += 1
                            global_stats['vtrs_operando'] += 1
                        elif aloc.status_no_dia.codigo == 'RESERVA':
                            vtrs_reserva_global.append({
                                'prefixo': aloc.viatura.prefixo,
                                'unidade': unidade.nome,
                                'sgb': sgb_nome
                            })

                        equipe = AlocacaoFuncionario.objects.filter(alocacao_viatura=aloc).select_related('funcionario__posto_graduacao', 'funcao')
                        cmt = equipe.filter(funcao__codigo='COMANDANTE').first()
                        if not cmt:
                            cmt = equipe.first()
                        
                        membros = []
                        for m in equipe:
                            if m.dejem: 
                                stats['dejem'] += 1
                                global_stats['dejem'] += 1
                            
                            if m.funcao and m.funcao.codigo == 'MOTORISTA':
                                global_stats['motoristas'] += 1

                            efetivo_info = Efetivo.objects.filter(Q(re=m.funcionario.re) | Q(nome__icontains=m.funcionario.nome_guerra)).first()
                            
                            membros.append({
                                'nome': format_militar_display(m.funcionario, efetivo_info),
                                'funcao': m.funcao.nome if m.funcao else 'AUX',
                                'mergulhador': 'SIM' in str(efetivo_info.mergulho).upper() if efetivo_info else False,
                                'ovb': efetivo_info.ovb if efetivo_info else None,
                                'dejem': m.dejem,
                                'horario': f"{m.inicio_dejem.strftime('%H:%M')} > {m.termino_dejem.strftime('%H:%M')}" if m.dejem and m.inicio_dejem else ""
                            })
                            
                            if efetivo_info:
                                if 'SIM' in str(efetivo_info.mergulho).upper(): 
                                    stats['mergulhadores'] += 1
                                    global_stats['mergulhadores'] += 1
                                if 'LEVE' in str(efetivo_info.ovb).upper(): stats['ovb_leve'] += 1
                                if 'PESADO' in str(efetivo_info.ovb).upper(): stats['ovb_pesado'] += 1
                            
                            stats['efetivo_total'] += 1
                            global_stats['militares_escalados'] += 1

                        encarregado_vtr = 'S/ CMT'
                        if cmt:
                            ef_cmt = Efetivo.objects.filter(Q(re=cmt.funcionario.re) | Q(nome__icontains=cmt.funcionario.nome_guerra)).first()
                            encarregado_vtr = format_militar_display(cmt.funcionario, ef_cmt)

                        viaturas_data.append({
                            'prefixo': aloc.viatura.prefixo, 
                            'status': aloc.status_no_dia.nome,
                            'status_codigo': aloc.status_no_dia.codigo,
                            'num_pm': equipe.count(),
                            'encarregado': encarregado_vtr,
                            'equipe_completa': membros
                        })
            
            postos_result.append({
                'unidade': unidade if unidade else {'nome': p_nome, 'id': None}, 
                'viaturas': viaturas_data, 
                'mapa_existe': mapa_existe,
                'esta_pronto': esta_pronto,
                'telegrafista': telegrafista_info,
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
        'global_stats': global_stats,
        'vtrs_reserva_global': vtrs_reserva_global,
        'botoes_atalho': ['Aeroportos', 'Alarmes / Cód OPM', 'VTR Reserva', 'Normas do CB', 'Links / Intranet', 'Bairros', 'Pesquisa'],
        'oficiais': [
            {'cargo': 'Supervisor de Serviço', 'nome': 'CAP PM RODRIGUES', 'tipo': 'DIA'}, 
            {'cargo': 'Comando de Área', 'nome': '1º TEN PM COSTA', 'tipo': 'DIA'}, 
            {'cargo': 'Despachador', 'nome': 'SGT PM SILVA', 'tipo': 'NOITE'}
        ]
    })

@login_required
def cadastro_viaturas_view(request):
    query = request.GET.get('q', '')
    status_filter = request.GET.get('status', '')
    sgb_filter = request.GET.get('sgb', '')
    garagem_filter = request.GET.get('garagem', '')
    viaturas = Viatura.objects.select_related('status_base', 'unidade_base').all()
    if query:
        viaturas = viaturas.filter(Q(prefixo__icontains=query) | Q(placa__icontains=query))
    if status_filter:
        viaturas = viaturas.filter(status_base__codigo=status_filter)
    if sgb_filter:
        viaturas = viaturas.filter(sgb=sgb_filter)
    if garagem_filter:
        viaturas = viaturas.filter(garagem=garagem_filter)
    lista_sgb = Viatura.objects.exclude(sgb__isnull=True).values_list('sgb', flat=True).distinct().order_by('sgb')
    lista_garagem = Viatura.objects.exclude(garagem__isnull=True).values_list('garagem', flat=True).distinct().order_by('garagem')
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
    try:
        call_command('sync_viaturas_sheets')
        return HttpResponse('<div class="p-4 bg-emerald-500/20 text-emerald-400 rounded-2xl text-xs font-black uppercase tracking-widest animate-pulse">Sincronização realizada com sucesso! Recarregando...<script>setTimeout(() => location.reload(), 2000)</script></div>')
    except Exception as e:
        return HttpResponse(f'<div class="p-4 bg-red-500/20 text-red-400 rounded-2xl text-xs font-bold">Erro: {str(e)}</div>')

@login_required
def lista_postos_view(request):
    query = request.GET.get('q', '')
    postos = Posto.objects.prefetch_related('municipios').all()
    if query:
        postos = postos.filter(Q(nome__icontains=query) | Q(sgb__icontains=query) | Q(cidade_posto__icontains=query))
    return render(request, 'unidades/lista_postos.html', {'postos': postos, 'query': query})

@login_required
def sync_postos_sheets_action(request):
    try:
        call_command('sync_postos_sheets')
        return HttpResponse('<div class="p-4 bg-emerald-500/20 text-emerald-400 rounded-2xl text-xs font-black uppercase tracking-widest animate-pulse">Postos sincronizados! Recarregando...<script>setTimeout(() => location.reload(), 2000)</script></div>')
    except Exception as e:
        return HttpResponse(f'<div class="p-4 bg-red-500/20 text-red-400 rounded-2xl text-xs font-bold">Erro: {str(e)}</div>')
