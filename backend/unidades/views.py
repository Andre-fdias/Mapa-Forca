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
                    
                    nome_enc = {'nome_padrao': 'S/ CMT'}
                    if cmt:
                        ef_info = Efetivo.objects.filter(Q(re=cmt.funcionario.re) | Q(nome__icontains=cmt.funcionario.nome_guerra)).first()
                        nome_enc = {
                            'nome_padrao': ef_info.nome if ef_info else format_militar_display(cmt.funcionario, ef_info)
                        }

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
    """Dashboard Geral (COBOM/Grande Comando) com mapeamento dinâmico e dados REAIS."""
    hoje = get_data_operacional()
    
    # Seletor de Unidades (Apenas Admin, Superuser ou COBOM)
    # Filtramos por BATALHAO para garantir que apenas os Grupamentos reais apareçam
    batalhoes = []
    if request.user.is_superuser or request.user.role in ['ADMIN', 'COBOM']:
        batalhoes = Unidade.objects.filter(tipo_unidade__codigo='BATALHAO').order_by('nome')
    
    batalhao_id = request.GET.get('batalhao_id')
    if batalhao_id:
        batalhao_selecionado = Unidade.objects.filter(id=batalhao_id).first()
    else:
        # Default: Unidade do usuário se for Batalhão, ou 15º GB
        if request.user.unidade and request.user.unidade.tipo_unidade and request.user.unidade.tipo_unidade.codigo == 'BATALHAO':
            batalhao_selecionado = request.user.unidade
        else:
            batalhao_selecionado = Unidade.objects.filter(nome__icontains='15', tipo_unidade__codigo='BATALHAO').first()

    if not batalhao_selecionado:
        batalhao_selecionado = Unidade.objects.filter(tipo_unidade__codigo='BATALHAO').first()

    total_unidades = 0
    total_completos = 0
    
    global_stats = {
        'vtrs_operando': 0,
        'militares_escalados': 0,
        'mergulhadores': 0,
        'dejem': 0,
        'motoristas': 0
    }
    
    sgbs_data = []
    vtrs_reserva_global = []
    
    if batalhao_selecionado:
        # SGBs são subunidades do Batalhão
        sgbs = batalhao_selecionado.subunidades.all().order_by('nome')
        
        for sgb in sgbs:
            postos_result = []
            # Postos são subunidades do SGB
            # Tentamos buscar tanto por subunidades quanto por Posto real da planilha
            postos_unidades = sgb.subunidades.all().order_by('nome')
            
            for unidade in postos_unidades:
                # Filtro Operacional (Vem da Planilha via modelo Posto)
                posto_obj_real = Posto.objects.filter(Q(cod_secao=unidade.codigo_secao) | Q(nome=unidade.nome)).first()
                
                # Se não houver informação no Posto ou se estiver como OPERACIONAL (ou vazio), mostramos.
                # Só ocultamos se estiver explicitamente como ADM e não contiver OPERACIONAL.
                is_operacional = True
                if posto_obj_real and posto_obj_real.operacional_adm:
                    status_op = str(posto_obj_real.operacional_adm).upper()
                    if "ADM" in status_op and "OPERACIONAL" not in status_op:
                        is_operacional = False
                
                if not is_operacional:
                    continue

                total_unidades += 1
                viaturas_data = []
                esta_pronto = False
                mapa_existe = False
                
                telegrafista_info = {
                    'nome': "AGUARDANDO...",
                    'nome_padrao': "AGUARDANDO...",
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
                            telegrafista_info['nome_padrao'] = ef_tel.nome if ef_tel else format_militar_display(tel_func.funcionario, ef_tel)
                            telegrafista_info['nome'] = telegrafista_info['nome_padrao']
                            telegrafista_info['is_dejem'] = tel_func.dejem
                            if tel_func.dejem and tel_func.inicio_dejem:
                                telegrafista_info['horario'] = f"{tel_func.inicio_dejem.strftime('%H:%M')} > {tel_func.termino_dejem.strftime('%H:%M')}"
                            
                            global_stats['militares_escalados'] += 1
                            stats['efetivo_total'] += 1
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
                                'sgb': sgb.nome
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
                                'nome': m.funcionario.nome_curto,
                                'nome_padrao': efetivo_info.nome if efetivo_info else m.funcionario.nome_curto.upper(),
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

                        enc_nome_sheets = 'S/ CMT'
                        if cmt:
                            ef_cmt = Efetivo.objects.filter(Q(re=cmt.funcionario.re) | Q(nome__icontains=cmt.funcionario.nome_guerra)).first()
                            enc_nome_sheets = ef_cmt.nome if ef_cmt else format_militar_display(cmt.funcionario, ef_cmt)
                        
                        encarregado_vtr = {'nome_padrao': enc_nome_sheets}

                        viaturas_data.append({
                            'prefixo': aloc.viatura.prefixo, 
                            'status': aloc.status_no_dia.nome,
                            'status_codigo': aloc.status_no_dia.codigo,
                            'num_pm': equipe.count(),
                            'encarregado': encarregado_vtr,
                            'equipe_completa': membros,
                            'vol_agua': aloc.viatura.vol_agua,
                            'combustivel': aloc.viatura.combustivel,
                            'placa': aloc.viatura.placa
                        })
                
                postos_result.append({
                    'unidade': unidade, 
                    'viaturas': viaturas_data, 
                    'mapa_existe': mapa_existe,
                    'esta_pronto': esta_pronto,
                    'telegrafista': telegrafista_info,
                    'stats': stats
                })
            
            if postos_result:
                sgbs_data.append({
                    'nome': sgb.nome,
                    'postos': postos_result
                })
    
    mapa_completo = (total_completos == total_unidades) if total_unidades > 0 else False
    
    return render(request, 'dashboard/cobom.html', {
        'sgbs': sgbs_data, 
        'hoje': hoje, 
        'mapa_completo': mapa_completo,
        'global_stats': global_stats,
        'vtrs_reserva_global': vtrs_reserva_global,
        'batalhoes': batalhoes,
        'batalhao_selecionado': batalhao_selecionado,
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
    unidade_filter = request.GET.get('unidade', '') # Filtro de OPMCB
    
    viaturas = Viatura.objects.select_related('status_base', 'unidade_base').all()
    
    if query:
        viaturas = viaturas.filter(Q(prefixo__icontains=query) | Q(placa__icontains=query))
    if status_filter:
        viaturas = viaturas.filter(status_base__codigo=status_filter)
    if sgb_filter:
        viaturas = viaturas.filter(sgb=sgb_filter)
    if garagem_filter:
        viaturas = viaturas.filter(garagem=garagem_filter)
    if unidade_filter:
        viaturas = viaturas.filter(opmcb__icontains=unidade_filter)

    # --- LÓGICA DE FILTROS DEPENDENTES ---
    # A lista de Unidades (GBs) é sempre a lista completa disponível no banco
    lista_unidades = Viatura.objects.exclude(opmcb__isnull=True).values_list('opmcb', flat=True).distinct().order_by('opmcb')
    
    # Base de consulta para SGB e Garagem depende da Unidade selecionada
    base_filtros = Viatura.objects.all()
    if unidade_filter:
        base_filtros = base_filtros.filter(opmcb__icontains=unidade_filter)
    
    # Se um SGB for selecionado, a lista de Garagens pode ser filtrada por ele também (Opcional, mas melhora a experiência)
    base_garagens = base_filtros
    if sgb_filter:
        base_garagens = base_garagens.filter(sgb=sgb_filter)

    lista_sgb = base_filtros.exclude(sgb__isnull=True).values_list('sgb', flat=True).distinct().order_by('sgb')
    lista_garagem = base_garagens.exclude(garagem__isnull=True).values_list('garagem', flat=True).distinct().order_by('garagem')
    
    status_options = Dictionary.objects.filter(tipo='STATUS_VIATURA').order_by('ordem')
    
    return render(request, 'unidades/cadastro_viaturas.html', {
        'viaturas': viaturas,
        'query': query,
        'status_filter': status_filter,
        'sgb_filter': sgb_filter,
        'garagem_filter': garagem_filter,
        'unidade_filter': unidade_filter,
        'lista_sgb': lista_sgb,
        'lista_garagem': lista_garagem,
        'lista_unidades': lista_unidades,
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
    unidade_filter = request.GET.get('unidade', '')
    sgb_filter = request.GET.get('sgb', '')

    postos = Posto.objects.prefetch_related('municipios').all().order_by('unidade', 'sgb', 'nome')
    
    if query:
        postos = postos.filter(Q(nome__icontains=query) | Q(sgb__icontains=query) | Q(cidade_posto__icontains=query))
    if unidade_filter:
        postos = postos.filter(unidade=unidade_filter)
    if sgb_filter:
        postos = postos.filter(sgb=sgb_filter)

    # --- LÓGICA DE FILTROS ---
    # Unidades únicas
    lista_unidades = Posto.objects.exclude(unidade__isnull=True).exclude(unidade='').values_list('unidade', flat=True).distinct().order_by('unidade')
    
    # SGBs únicos filtrados pela unidade
    base_sgbs = Posto.objects.all()
    if unidade_filter:
        base_sgbs = base_sgbs.filter(unidade=unidade_filter)
    lista_sgb = base_sgbs.exclude(sgb__isnull=True).exclude(sgb='').values_list('sgb', flat=True).distinct().order_by('sgb')

    return render(request, 'unidades/lista_postos.html', {
        'postos': postos, 
        'query': query,
        'unidade_filter': unidade_filter,
        'sgb_filter': sgb_filter,
        'lista_unidades': lista_unidades,
        'lista_sgb': lista_sgb
    })

@login_required
def sync_postos_sheets_action(request):
    try:
        call_command('sync_postos_sheets')
        return HttpResponse('<div class="p-4 bg-emerald-500/20 text-emerald-400 rounded-2xl text-xs font-black uppercase tracking-widest animate-pulse">Postos sincronizados! Recarregando...<script>setTimeout(() => location.reload(), 2000)</script></div>')
    except Exception as e:
        return HttpResponse(f'<div class="p-4 bg-red-500/20 text-red-400 rounded-2xl text-xs font-bold">Erro: {str(e)}</div>')

@login_required
def visao_cobom_efetivo_view(request):
    """Nova Visão Tática COBOM focada em Efetivo (Design Dark Mode)"""
    agora = timezone.localtime(timezone.now())
    hoje = get_data_operacional()
    
    # Try to find today's COBOM map
    mapa = MapaDiario.objects.filter(data=hoje, unidade__nome='CBI-1').first()
    if not mapa:
        # Fallback in case ADMIN created the map under a different unit by mistake
        mapa = MapaDiario.objects.filter(data=hoje, alocacoes_funcionarios__funcao__nome__in=['Oficial de Operações DEJEM', 'Supervisor Despacho', 'Chefe de Equipe']).first()
    
    pessoas = []
    
    FUNCOES_FIXAS = [
        ('COBOM CBI1', 'text-blue-500', 'Oficial de Operações DEJEM'),
        ('COBOM CBI1', 'text-blue-500', 'Chefe de Equipe'),
        ('COBOM CBI1', 'text-blue-500', 'Supervisor Despacho'),
        ('COBOM CBI1', 'text-blue-500', 'Supervisor 193'),
        ('COBOM CBI1', 'text-blue-500', 'Atendente 193'),
        ('7º GB', 'text-red-500', 'Supervisor 7º GB'),
        ('7º GB', 'text-red-500', 'Cabine 7º GB'),
        ('19º GB', 'text-red-500', 'Supervisor 19º GB'),
        ('19º GB', 'text-red-500', 'Cabine 19º GB'),
        ('15º GB', 'text-red-500', 'Supervisor 15º GB'),
        ('15º GB', 'text-red-500', 'Cabine 15º GB'),
        ('16º GB', 'text-red-500', 'Supervisor 16º GB'),
        ('16º GB', 'text-red-500', 'Cabine 16º GB'),
        ('APOIO', 'text-slate-400', 'Apoio Cabine 7º, 19º e 15º GB'),
        ('APOIO', 'text-slate-400', 'Apoio Cabine 16º GB'),
        ('TRIAGEM', 'text-emerald-500', 'Enfermeiro de Triagem'),
        ('SISTEMA', 'text-purple-500', 'Inclusor'),
        ('SISTEMA', 'text-purple-500', 'Supervisor COE Autoban'),
    ]
    
    if mapa:
        alocs = mapa.alocacoes_funcionarios.select_related('funcionario__posto_graduacao', 'funcao')
        aloc_dict = {a.funcao.nome.upper(): a for a in alocs if a.funcao}
        
        for setor, cor, fn_nome in FUNCOES_FIXAS:
            fn_upper = fn_nome.upper()
            if fn_upper in aloc_dict:
                aloc = aloc_dict[fn_upper]
                ef_info = Efetivo.objects.filter(Q(re=aloc.funcionario.re) | Q(nome__icontains=aloc.funcionario.nome_guerra)).first()
                nome_display = format_militar_display(aloc.funcionario, ef_info)
                
                obs = []
                if ef_info:
                    if 'SIM' in str(ef_info.mergulho).upper(): obs.append('MERG')
                    if ef_info.ovb: obs.append(ef_info.ovb)
                if aloc.dejem: obs.append('DEJEM')
                    
                pessoas.append({
                    'setor': setor,
                    'funcao': fn_nome.upper(),
                    're': aloc.funcionario.re or '-',
                    'nome': nome_display,
                    'obs': ' '.join(obs) if obs else '-',
                    'tel': ef_info.telefone if ef_info and hasattr(ef_info, 'telefone') else '-',
                    'cor_setor': cor,
                })
            else:
                pessoas.append({
                    'setor': setor,
                    'funcao': fn_nome.upper(),
                    're': '-',
                    'nome': '-',
                    'obs': '-',
                    'tel': '-',
                    'cor_setor': cor,
                })
            
        prontidao = mapa.prontidao or 'INDEFINIDA'
        equipe = mapa.equipe or '-'
    else:
        prontidao = 'NÃO INICIADO'
        equipe = '-'
        
    color_map = {
        'AZUL': ('bg-blue-600/10', 'border-blue-500', 'text-blue-500', 'bg-blue-500'),
        'VERDE': ('bg-emerald-600/10', 'border-emerald-500', 'text-emerald-500', 'bg-emerald-500'),
        'AMARELA': ('bg-amber-600/10', 'border-amber-500', 'text-amber-500', 'bg-amber-500')
    }
    bg_class, border_class, text_class, icon_class = color_map.get(prontidao.upper(), ('bg-slate-600/10', 'border-slate-500', 'text-slate-500', 'bg-slate-500'))
    
    context = {
        'hoje': agora,
        'aba_ativa': 'CBI-1',
        'is_editor': request.user.role in ['ADMIN', 'COBOM'] or request.user.is_superuser,
        'pessoas': pessoas,
        'prontidao': prontidao,
        'equipe': equipe,
        'bg_class': bg_class,
        'border_class': border_class,
        'text_class': text_class,
        'icon_class': icon_class,
    }
    
    return render(request, 'dashboard/visao_cobom_efetivo.html', context)
