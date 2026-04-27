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

def format_militar_display(funcionario, efetivo_info, include_re=True):
    """Garante o formato EXATO: PATENTE + ' ' + RE + ' ' + NOME (Ex: 1º TEN PM 123456-7 NOME)."""
    ranks = [
        'CEL PM', 'TEN CEL PM', 'MAJ PM', 'CAP PM', '1º TEN PM', '2º TEN PM', 'ASP PM', 
        'SUBTEN PM', '1º SGT PM', '2º SGT PM', '3º SGT PM', 'CB PM', 'SD PM'
    ]
    
    # 1. Patente (Posto/Graduação)
    p_final = ""
    if efetivo_info and efetivo_info.posto_secao:
        p_txt = str(efetivo_info.posto_secao).upper()
        for r in ranks:
            if r in p_txt or r.replace('º', '') in p_txt:
                p_final = r
                break
    if not p_final and funcionario and funcionario.posto_graduacao:
        p_final = funcionario.posto_graduacao.nome.upper()

    # 2. RE e DIG
    re_str = ""
    raw_re = ""
    if funcionario and funcionario.re:
        raw_re = funcionario.re
    elif efetivo_info and efetivo_info.re:
        raw_re = efetivo_info.re
        
    if raw_re:
        parts = str(raw_re).split('-')
        re_val = parts[0].strip()
        dig_val = parts[1].strip() if len(parts) > 1 else ""
        if not dig_val and efetivo_info and efetivo_info.dig:
            dig_val = str(efetivo_info.dig).strip()
        
        re_str = f"{re_val}-{dig_val}" if dig_val else re_val

    # 3. Nome de Guerra
    n_final = ""
    if efetivo_info and efetivo_info.nome_guerra:
        n_final = str(efetivo_info.nome_guerra).upper().strip()
    elif efetivo_info and efetivo_info.nome:
        # Tenta extrair apenas o nome do campo 'nome' do efetivo
        n_txt = str(efetivo_info.nome).upper()
        n_txt = re.sub(r'\d{6}-\d{1}', '', n_txt)
        n_txt = re.sub(r'\(.*?\)', '', n_txt)
        for r in ranks:
            n_txt = n_txt.replace(r, '').replace(r.replace('º', ''), '')
        n_final = n_txt.strip()
    
    if not n_final and funcionario:
        n_final = (funcionario.nome_guerra or "").upper().strip()

    # 4. Montagem Final (Ordem: PATENTE RE NOME)
    parts = []
    if p_final: parts.append(p_final)
    if include_re and re_str: parts.append(re_str)
    if n_final: parts.append(n_final)
        
    return " ".join(parts) or "S/ NOME"

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
    user = request.user
    
    # --- LÓGICA DE PERMISSÕES DE ACESSO AO GRUPAMENTO (BATALHÃO) ---
    # ADMIN e COBOM são usuários globais (veem todos os Batalhões)
    is_global_user = user.is_superuser or user.role in ['ADMIN', 'COBOM']
    
    # Seletor de Unidades (Aparece apenas para usuários Globais)
    batalhoes = []
    if is_global_user:
        batalhoes = Unidade.objects.filter(tipo_unidade__codigo='BATALHAO').order_by('nome')
    
    batalhao_id = request.GET.get('batalhao_id')
    batalhao_selecionado = None
    
    # Prioridade 1: Seleção na URL (Apenas para usuários Globais)
    if batalhao_id and is_global_user:
        batalhao_selecionado = Unidade.objects.filter(id=batalhao_id).first()
    
    # Prioridade 2: Unidade de vínculo (Detecta Batalhão raiz para POSTO/SGB/BATALHAO)
    if not batalhao_selecionado and user.unidade:
        curr = user.unidade
        while curr:
            if curr.tipo_unidade and curr.tipo_unidade.codigo == 'BATALHAO':
                batalhao_selecionado = curr
                break
            # Fallback: Se o nome contiver "GB" mas não "SGB", provavelmente é um Batalhão
            u_nome = curr.nome.upper()
            if 'GB' in u_nome and 'SGB' not in u_nome:
                batalhao_selecionado = curr
                break
            # Se não tiver pai e ainda não achamos, usa o root_unit
            if not curr.parent:
                if curr.tipo_unidade and curr.tipo_unidade.codigo == 'BATALHAO':
                    batalhao_selecionado = curr
                else:
                    batalhao_selecionado = curr.root_unit
                break
            curr = curr.parent
            
    # Prioridade 3: Padrão 15º GB (Apenas para usuários Globais sem vínculo)
    if not batalhao_selecionado and is_global_user:
        # Busca mais flexível para o 15º GB
        batalhao_selecionado = Unidade.objects.filter(
            Q(nome__icontains='15') & Q(tipo_unidade__codigo='BATALHAO')
        ).first() or Unidade.objects.filter(nome__icontains='15º GB').first()

    # Prioridade 4: Primeiro que encontrar (Apenas para usuários Globais)
    if not batalhao_selecionado and is_global_user:
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
            postos_unidades = sgb.subunidades.all().order_by('nome')
            
            for unidade in postos_unidades:
                posto_obj_real = Posto.objects.filter(Q(cod_secao=unidade.codigo_secao) | Q(nome=unidade.nome)).first()
                
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
                
                # --- VERIFICAÇÃO DE PERMISSÃO DE EDIÇÃO ---
                # A regra é: ver todos do Batalhão, mas editar só o que compete ao nível
                pode_editar = is_global_user
                if not pode_editar:
                    if user.role == 'BATALHAO':
                        pode_editar = (batalhao_selecionado == user.unidade or user.unidade.root_unit == batalhao_selecionado)
                    elif user.role == 'SGB':
                        pode_editar = (user.unidade == sgb)
                    elif user.role == 'POSTO':
                        pode_editar = (user.unidade == unidade)

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
                    
                    alocs_pms = AlocacaoFuncionario.objects.filter(mapa=mapa).select_related('funcionario', 'funcao')
                    stats['efetivo_total'] = alocs_pms.count()
                    global_stats['militares_escalados'] += stats['efetivo_total']
                    
                    for m in alocs_pms:
                        if m.dejem: 
                            stats['dejem'] += 1
                            global_stats['dejem'] += 1
                        if m.funcao and m.funcao.codigo == 'MOTORISTA':
                            global_stats['motoristas'] += 1
                        
                        ef_info = Efetivo.objects.filter(Q(re=m.funcionario.re) | Q(nome__icontains=m.funcionario.nome_guerra)).first()
                        if ef_info:
                            if 'SIM' in str(ef_info.mergulho).upper(): 
                                stats['mergulhadores'] += 1
                                global_stats['mergulhadores'] += 1
                            if 'LEVE' in str(ef_info.ovb).upper(): stats['ovb_leve'] += 1
                            if 'PESADO' in str(ef_info.ovb).upper(): stats['ovb_pesado'] += 1

                    prefixos_tel = ['TELEGRAFISTA', 'TELEGRAFIA']
                    alocacoes_vtr_lista = AlocacaoViatura.objects.filter(
                        mapa=mapa, 
                        status_no_dia__codigo__in=['OPERANDO', 'RESERVA']
                    ).select_related('viatura', 'status_no_dia').exclude(viatura__prefixo__in=prefixos_tel)
                    
                    stats['vtrs_total'] = alocacoes_vtr_lista.count()
                    
                    aloc_tel = AlocacaoViatura.objects.filter(mapa=mapa, viatura__prefixo__in=prefixos_tel).first()
                    if aloc_tel:
                        tel_func = alocs_pms.filter(alocacao_viatura=aloc_tel).first()
                        if tel_func:
                            ef_tel = Efetivo.objects.filter(Q(re=tel_func.funcionario.re) | Q(nome__icontains=tel_func.funcionario.nome_guerra)).first()
                            telegrafista_info['nome_padrao'] = ef_tel.nome if ef_tel else format_militar_display(tel_func.funcionario, ef_tel)
                            telegrafista_info['nome'] = telegrafista_info['nome_padrao']
                            telegrafista_info['is_dejem'] = tel_func.dejem
                            if tel_func.dejem and tel_func.inicio_dejem:
                                telegrafista_info['horario'] = f"{tel_func.inicio_dejem.strftime('%H:%M')} > {tel_func.termino_dejem.strftime('%H:%M')}"

                    for aloc in alocacoes_vtr_lista:
                        if aloc.status_no_dia.codigo == 'OPERANDO':
                            stats['vtrs_operando'] += 1
                            global_stats['vtrs_operando'] += 1
                        elif aloc.status_no_dia.codigo == 'RESERVA':
                            vtrs_reserva_global.append({
                                'prefixo': aloc.viatura.prefixo,
                                'unidade': unidade.nome,
                                'sgb': sgb.nome
                            })

                        equipe_vtr = alocs_pms.filter(alocacao_viatura=aloc)
                        cmt = equipe_vtr.filter(funcao__codigo='COMANDANTE').first() or equipe_vtr.first()
                        
                        membros = []
                        for m in equipe_vtr:
                            efetivo_info = Efetivo.objects.filter(Q(re=m.funcionario.re) | Q(nome__icontains=m.funcionario.nome_guerra)).first()
                            tel_raw = efetivo_info.telefone if efetivo_info else None
                            tel_link = normalize_phone_for_whatsapp(tel_raw)
                            
                            # Garantir que o horário do DEJEM seja capturado corretamente
                            horario_formatado = ""
                            if m.dejem:
                                h_inicio = m.inicio_dejem or m.inicio_servico
                                h_fim = m.termino_dejem or m.termino_servico
                                if h_inicio and h_fim:
                                    horario_formatado = f"{h_inicio.strftime('%H:%M')} > {h_fim.strftime('%H:%M')}"
                                else:
                                    horario_formatado = "Horário N/D"
                            
                            membros.append({
                                'nome': m.funcionario.nome_curto,
                                'nome_padrao': efetivo_info.nome if efetivo_info else m.funcionario.nome_curto.upper(),
                                'funcao': m.funcao.nome if m.funcao else 'AUX',
                                'mergulho': efetivo_info.mergulho if efetivo_info else 'NÃO',
                                'is_mergulhador': 'SIM' in str(efetivo_info.mergulho).upper() if efetivo_info else False,
                                'ovb': efetivo_info.ovb if efetivo_info else 'NÃO',
                                'dejem': m.dejem,
                                'horario': horario_formatado,
                                'telefone': tel_raw,
                                'whatsapp_link': f'https://wa.me/{tel_link}' if tel_link else None,
                            })

                        enc_nome = 'S/ CMT'
                        if cmt:
                            ef_cmt = Efetivo.objects.filter(Q(re=cmt.funcionario.re) | Q(nome__icontains=cmt.funcionario.nome_guerra)).first()
                            enc_nome = ef_cmt.nome if ef_cmt else format_militar_display(cmt.funcionario, ef_cmt)
                        
                        viaturas_data.append({
                            'prefixo': aloc.viatura.prefixo, 
                            'status': aloc.status_no_dia.nome,
                            'status_codigo': aloc.status_no_dia.codigo,
                            'num_pm': equipe_vtr.count(),
                            'encarregado': {'nome_padrao': enc_nome},
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
                    'stats': stats,
                    'pode_editar': pode_editar
                })
            
            if postos_result:
                sgbs_data.append({
                    'nome': sgb.nome,
                    'postos': postos_result
                })
    
    mapa_completo = (total_completos == total_unidades) if total_unidades > 0 else False
    
    # --- COLETA DE OFICIAIS DE SERVIÇO (REAL-TIME) ---
    oficiais_servico = []
    oficial_area_1 = None
    oficial_area_2 = None
    supervisor_bt = None # Novo campo para o card fixo
    
    # Identificar Unidade (GB) Alvo (Selecionado ou do Usuário)
    target_gb_nome = ""
    if batalhao_selecionado:
        target_gb_nome = batalhao_selecionado.nome.upper()
    elif user.unidade:
        curr = user.unidade
        while curr:
            if curr.tipo_unidade and curr.tipo_unidade.codigo == 'BATALHAO':
                target_gb_nome = curr.nome.upper()
                break
            if 'GB' in curr.nome.upper() and 'SGB' not in curr.nome.upper():
                target_gb_nome = curr.nome.upper()
                break
            curr = curr.parent
    
    if batalhao_selecionado:
        unidades_bt_ids = [batalhao_selecionado.id]
        for s_sgb in batalhao_selecionado.subunidades.all():
            unidades_bt_ids.append(s_sgb.id)
            for s_posto in s_sgb.subunidades.all():
                unidades_bt_ids.append(s_posto.id)
        
        # 1. Supervisor do Batalhão (Busca Global no dia - pode estar no mapa do GB ou no CBI-1)
        if target_gb_nome:
            # Simplifica o nome para busca (ex: "15º GB" -> "15")
            gb_number_match = re.search(r'(\d+)', target_gb_nome)
            gb_num = gb_number_match.group(1) if gb_number_match else ""
            
            # Busca o supervisor em QUALQUER mapa de hoje
            # Filtra por funções que contenham "Supervisor" AND o número do GB
            aloc_sup_obj = AlocacaoFuncionario.objects.filter(
                mapa__data=hoje
            ).filter(
                Q(funcao__nome__icontains='Supervisor') & 
                (Q(funcao__nome__icontains=target_gb_nome) | Q(funcao__nome__icontains=gb_num))
            ).select_related('funcionario__posto_graduacao', 'mapa__unidade').first()

            if aloc_sup_obj:
                ef_sup = Efetivo.objects.filter(Q(re=aloc_sup_obj.funcionario.re) | Q(nome__icontains=aloc_sup_obj.funcionario.nome_guerra)).first()
                tel_link = normalize_phone_for_whatsapp(ef_sup.telefone) if ef_sup else None
                
                # Preparar objeto para o template
                rank = (aloc_sup_obj.funcionario.posto_graduacao.nome if aloc_sup_obj.funcionario.posto_graduacao else "").upper()
                stars = 0
                if 'CEL' in rank: stars = 3
                elif 'MAJ' in rank: stars = 2
                elif 'CAP' in rank: stars = 1
                
                aloc_sup_obj.rank_display = rank
                aloc_sup_obj.stars_list = range(stars)
                aloc_sup_obj.whatsapp_link = f'https://wa.me/{tel_link}' if tel_link else None
                supervisor_bt = aloc_sup_obj

        # 2. Oficiais de Área
        alocs_area = AlocacaoFuncionario.objects.filter(
            mapa__data=hoje, 
            mapa__unidade_id__in=unidades_bt_ids,
            is_oficial_area=True
        ).select_related('funcionario', 'mapa__unidade', 'alocacao_viatura__viatura').order_by('id')[:2]
        
        for i, aloc_area in enumerate(alocs_area):
            # Identificar o militar no Efetivo para pegar dados táticos
            ef_area = Efetivo.objects.filter(Q(re=aloc_area.funcionario.re) | Q(nome__icontains=aloc_area.funcionario.nome_guerra)).first()
            
            # Garantir que o telefone apareça no card se estiver no Efetivo mas não no Funcionario
            tel_link = None
            if ef_area and ef_area.telefone:
                if not aloc_area.funcionario.telefone:
                    aloc_area.funcionario.telefone = ef_area.telefone
                tel_link = normalize_phone_for_whatsapp(ef_area.telefone)
            
            aloc_area.whatsapp_link = f'https://wa.me/{tel_link}' if tel_link else None

            # Lógica de Estrelas e Destaque de Patente
            rank = (aloc_area.funcionario.posto_graduacao.nome if aloc_area.funcionario.posto_graduacao else "").upper()
            stars = 0
            if 'CAP' in rank: stars = 3
            elif '1º TEN' in rank or '1O TEN' in rank: stars = 2
            elif '2º TEN' in rank or '2O TEN' in rank: stars = 1
            
            # Anexar ao objeto para o template
            aloc_area.rank_display = rank
            aloc_area.stars_list = range(stars)
            
            if i == 0: oficial_area_1 = aloc_area
            if i == 1: oficial_area_2 = aloc_area

            oficiais_servico.append({
                'cargo': f'Oficial de Área {i+1}' if alocs_area.count() > 1 else 'Oficial de Área',
                'nome': format_militar_display(aloc_area.funcionario, ef_area),
                'tipo': 'DIA' if not aloc_area.dejem else 'DEJEM',
                'telefone': ef_area.telefone if ef_area else None,
                'whatsapp_link': aloc_area.whatsapp_link,
                'unidade': aloc_area.mapa.unidade.nome
            })

        # 2. Supervisor do Grupamento (Baseado na unidade do usuário logado ou selecionada)
        aloc_sup = None
        if target_gb_nome:
            # Tenta encontrar no mapa de hoje quem é o supervisor dessa unidade específica
            aloc_sup = AlocacaoFuncionario.objects.filter(
                mapa__data=hoje,
                mapa__unidade_id__in=unidades_bt_ids
            ).filter(
                Q(funcao__nome__icontains='Supervisor') & Q(funcao__nome__icontains=target_gb_nome.replace('º', ''))
            ).select_related('funcionario', 'mapa__unidade', 'funcao').first()

            if aloc_sup:
                ef_sup = Efetivo.objects.filter(Q(re=aloc_sup.funcionario.re) | Q(nome__icontains=aloc_sup.funcionario.nome_guerra)).first()
                tel_link = normalize_phone_for_whatsapp(ef_sup.telefone) if ef_sup else None
                oficiais_servico.append({
                    'cargo': f'Supervisor {target_gb_nome}',
                    'nome': format_militar_display(aloc_sup.funcionario, ef_sup),
                    'tipo': 'DIA' if not aloc_sup.dejem else 'DEJEM',
                    'telefone': ef_sup.telefone if ef_sup else None,
                    'whatsapp_link': f'https://wa.me/{tel_link}' if tel_link else None,
                    'unidade': aloc_sup.mapa.unidade.nome
                })

        # 3. Complemento: Outros supervisores se houver espaço (opcional, para preencher a barra)
        exclude_ids = [a.id for a in alocs_area]
        if aloc_sup:
            exclude_ids.append(aloc_sup.id)
            
        alocs_outros = AlocacaoFuncionario.objects.filter(
            mapa__data=hoje,
            mapa__unidade_id__in=unidades_bt_ids
        ).filter(
            Q(sub_funcao='supervisor') | Q(funcao__codigo='SUPERVISOR')
        ).exclude(id__in=exclude_ids)[:2]

        for s in alocs_outros:
            ef_s = Efetivo.objects.filter(Q(re=s.funcionario.re) | Q(nome__icontains=s.funcionario.nome_guerra)).first()
            tel_link = normalize_phone_for_whatsapp(ef_s.telefone) if ef_s else None
            oficiais_servico.append({
                'cargo': f'Sup. {s.mapa.unidade.nome}',
                'nome': format_militar_display(s.funcionario, ef_s),
                'tipo': 'DIA' if not s.dejem else 'DEJEM',
                'whatsapp_link': f'https://wa.me/{tel_link}' if tel_link else None
            })

    if not oficiais_servico:
        oficiais_servico = [
            {'cargo': 'Supervisor de Serviço', 'nome': 'NÃO IDENTIFICADO', 'tipo': 'N/D'},
            {'cargo': 'Oficial de Área', 'nome': 'NÃO IDENTIFICADO', 'tipo': 'N/D'}
        ]

    return render(request, 'dashboard/cobom.html', {
        'sgbs': sgbs_data, 
        'hoje': hoje, 
        'mapa_completo': mapa_completo,
        'global_stats': global_stats,
        'vtrs_reserva_global': vtrs_reserva_global,
        'batalhoes': batalhoes,
        'batalhao_selecionado': batalhao_selecionado,
        'is_global_user': is_global_user,
        'botoes_atalho': ['Aeroportos', 'Alarmes / Cód OPM', 'VTR Reserva', 'Normas do CB', 'Links / Intranet', 'Bairros', 'Pesquisa'],
        'oficiais': oficiais_servico,
        'oficial_area_1': oficial_area_1,
        'oficial_area_2': oficial_area_2,
        'supervisor_bt': supervisor_bt
    })

@login_required
def cadastro_viaturas_view(request):
    user = request.user
    query = request.GET.get('q', '')
    status_filter = request.GET.get('status', '')
    sgb_filter = request.GET.get('sgb', '')
    garagem_filter = request.GET.get('garagem', '')
    unidade_filter = request.GET.get('unidade', '') # Filtro de OPMCB

    viaturas = Viatura.objects.select_related('status_base', 'unidade_base').all()

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
                # Extrai o número do GB (ex: "07") para match parcial seguro
                match = re.search(r'(\d+)', gb_unidade.nome)
                if match:
                    unidade_num = match.group(1).lstrip('0')
                    viaturas = viaturas.filter(
                        Q(opmcb__icontains=f"{unidade_num}º GB") | 
                        Q(opmcb__icontains=f"0{unidade_num}º GB") |
                        Q(opmcb__icontains=f"{unidade_num} GB")
                    )
                else:
                    viaturas = viaturas.filter(opmcb__icontains=gb_unidade.nome)
        else:
            viaturas = viaturas.none()

    # --- FILTROS DE BUSCA ---
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

    # --- LÓGICA DE OPÇÕES DOS FILTROS ---
    perm_based_qs = Viatura.objects.all()
    if not is_global_user and gb_unidade:
        match = re.search(r'(\d+)', gb_unidade.nome)
        if match:
            unidade_num = match.group(1).lstrip('0')
            perm_based_qs = perm_based_qs.filter(
                Q(opmcb__icontains=f"{unidade_num}º GB") | 
                Q(opmcb__icontains=f"0{unidade_num}º GB") |
                Q(opmcb__icontains=f"{unidade_num} GB")
            )
        else:
            perm_based_qs = perm_based_qs.filter(opmcb__icontains=gb_unidade.nome)
    elif not is_global_user:
        perm_based_qs = perm_based_qs.none()

    lista_unidades = perm_based_qs.exclude(opmcb__isnull=True).values_list('opmcb', flat=True).distinct().order_by('opmcb')
    base_filtros = perm_based_qs
    if unidade_filter:
        base_filtros = base_filtros.filter(opmcb__icontains=unidade_filter)

    lista_sgb = base_filtros.exclude(sgb__isnull=True).values_list('sgb', flat=True).distinct().order_by('sgb')
    lista_garagem = base_filtros.exclude(garagem__isnull=True).values_list('garagem', flat=True).distinct().order_by('garagem')
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
    user = request.user
    query = request.GET.get('q', '')
    unidade_filter = request.GET.get('unidade', '')
    sgb_filter = request.GET.get('sgb', '')

    postos = Posto.objects.prefetch_related('municipios').all().order_by('unidade', 'sgb', 'nome')

    # --- LÓGICA DE PERMISSÕES ---
    is_global_user = user.is_superuser or user.role in ['ADMIN', 'COBOM']

    gb_unidade = None
    if not is_global_user:
        if user.unidade:
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
                match = re.search(r'(\d+)', gb_unidade.nome)
                if match:
                    unidade_num = match.group(1).lstrip('0')
                    postos = postos.filter(
                        Q(unidade__icontains=f"{unidade_num}º GB") | 
                        Q(unidade__icontains=f"0{unidade_num}º GB") |
                        Q(unidade__icontains=f"{unidade_num} GB")
                    )
                else:
                    postos = postos.filter(unidade__icontains=gb_unidade.nome)
        else:
            postos = postos.none()

    # --- FILTROS DE BUSCA ---
    if query:
        postos = postos.filter(Q(nome__icontains=query) | Q(sgb__icontains=query) | Q(cidade_posto__icontains=query))
    if unidade_filter:
        postos = postos.filter(unidade=unidade_filter)
    if sgb_filter:
        postos = postos.filter(sgb=sgb_filter)

    # --- LÓGICA DE OPÇÕES DOS FILTROS ---
    perm_based_qs = Posto.objects.all()
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

@login_required
def visao_cobom_efetivo_view(request):
    """Nova Visão Tática COBOM focada em Efetivo (Design Dark Mode)"""
    agora = timezone.localtime(timezone.now())
    hoje = get_data_operacional()
    user = request.user
    
    # Identificar Unidade (GB) do Usuário Logado
    user_gb_nome = ""
    if user.unidade:
        curr = user.unidade
        while curr:
            if curr.tipo_unidade and curr.tipo_unidade.codigo == 'BATALHAO':
                user_gb_nome = curr.nome.upper()
                break
            # Fallback similar ao dashboard_cobom
            if 'GB' in curr.nome.upper() and 'SGB' not in curr.nome.upper():
                user_gb_nome = curr.nome.upper()
                break
            curr = curr.parent

    # Try to find today's COBOM map
    mapa = MapaDiario.objects.filter(data=hoje, unidade__nome='CBI-1').first()
    if not mapa:
        mapa = MapaDiario.objects.filter(data=hoje, alocacoes_funcionarios__funcao__nome__in=['Oficial de Operações DEJEM', 'Supervisor Despacho', 'Chefe de Equipe']).first()
    
    pessoas = []
    oficial_area_data = None
    supervisor_servico_data = None
    
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
        alocs_all = mapa.alocacoes_funcionarios.select_related('funcionario__posto_graduacao', 'funcao').all()
        
        # 1. Identificar Oficial de Área (Militar com flag is_oficial_area=True no mapa CBI-1)
        aloc_oa = alocs_all.filter(is_oficial_area=True).first()
        if aloc_oa:
            ef_oa = Efetivo.objects.filter(Q(re=aloc_oa.funcionario.re) | Q(nome__icontains=aloc_oa.funcionario.nome_guerra)).first()
            tel_link = normalize_phone_for_whatsapp(ef_oa.telefone) if ef_oa else None
            oficial_area_data = {
                'nome': format_militar_display(aloc_oa.funcionario, ef_oa),
                'telefone': ef_oa.telefone if ef_oa else '-',
                'whatsapp_link': f'https://wa.me/{tel_link}' if tel_link else None,
            }

        # 2. Identificar Supervisor do Usuário (Baseado na Unidade logada)
        if user_gb_nome:
            # Busca por função que contenha "Supervisor" e o nome da Unidade (ex: "Supervisor 15º GB")
            aloc_sup = alocs_all.filter(
                Q(funcao__nome__icontains='Supervisor') & Q(funcao__nome__icontains=user_gb_nome.replace('º', ''))
            ).first()
            if aloc_sup:
                ef_sup = Efetivo.objects.filter(Q(re=aloc_sup.funcionario.re) | Q(nome__icontains=aloc_sup.funcionario.nome_guerra)).first()
                tel_link = normalize_phone_for_whatsapp(ef_sup.telefone) if ef_sup else None
                supervisor_servico_data = {
                    'nome': format_militar_display(aloc_sup.funcionario, ef_sup),
                    'telefone': ef_sup.telefone if ef_sup else '-',
                    'whatsapp_link': f'https://wa.me/{tel_link}' if tel_link else None,
                    'unidade': user_gb_nome
                }

        # Agrupar alocações por nome da função em MAIÚSCULO
        from collections import defaultdict
        aloc_grupos = defaultdict(list)
        for a in alocs_all:
            if a.funcao:
                aloc_grupos[a.funcao.nome.upper()].append(a)

        for setor_original, cor_original, fn_nome in FUNCOES_FIXAS:
            alocs_da_funcao = aloc_grupos.get(fn_nome.upper(), [])
            setor = setor_original
            if '193' in fn_nome: setor = '193'
            
            esconder_detalhes = False
            fn_upper = fn_nome.upper()
            if any(gb in fn_upper for gb in ['7º GB', '15º GB', '16º GB', '19º GB']) and 'SUPERVISOR' in fn_upper:
                esconder_detalhes = True

            if alocs_da_funcao:
                if esconder_detalhes:
                    alocs_da_funcao = sorted(alocs_da_funcao, key=lambda x: 0 if x.sub_funcao == 'supervisor' else 1)

                for index, aloc in enumerate(alocs_da_funcao):
                    ef_info = Efetivo.objects.filter(Q(re=aloc.funcionario.re) | Q(nome__icontains=aloc.funcionario.nome_guerra)).first()
                    nome_display = format_militar_display(aloc.funcionario, ef_info)
                    
                    obs = []
                    if ef_info and 'SIM' in str(ef_info.mergulho).upper(): obs.append('MERGULHADOR')
                    if aloc.dejem: obs.append('DEJEM')
                    
                    horario_str = ""
                    h_ini = aloc.inicio_dejem or aloc.inicio_servico
                    h_fim = aloc.termino_dejem or aloc.termino_servico
                    if h_ini and h_fim:
                        horario_str = f"{h_ini.strftime('%H:%M')} - {h_fim.strftime('%H:%M')}"
                    
                    tel_raw = ef_info.telefone if ef_info else '-'
                    tel_link = normalize_phone_for_whatsapp(tel_raw)
                    
                    fn_display = fn_nome.upper()
                    if esconder_detalhes and index > 0 and aloc.sub_funcao == 'motorista':
                        gb_match = re.search(r'(\d+)', fn_nome)
                        gb_num = gb_match.group(1) if gb_match else ""
                        fn_display = f"MOTORISTA SUP {gb_num}º GB"

                    pessoas.append({
                        'setor': setor,
                        'funcao': fn_display,
                        're': aloc.funcionario.re or '-',
                        'nome': nome_display,
                        'obs': ' '.join(obs) if obs else '-',
                        'dejem_horario': horario_str,
                        'tel': tel_raw,
                        'tel_link': f'https://wa.me/{tel_link}' if tel_link else None,
                        'cor_setor': cor_original,
                        'is_supervisor_gb': esconder_detalhes,
                        'is_main_supervisor': esconder_detalhes and index == 0 and aloc.sub_funcao == 'supervisor',
                        'is_subordinate': esconder_detalhes and index > 0,
                        'has_subordinates': esconder_detalhes and len(alocs_da_funcao) > 1 and index == 0,
                        'row_id': f"sup_{fn_nome.replace(' ', '_')}" if esconder_detalhes else None
                    })
            else:
                pessoas.append({
                    'setor': setor,
                    'funcao': fn_nome.upper(),
                    're': '-',
                    'nome': '-',
                    'obs': '-',
                    'dejem_horario': '',
                    'tel': '-',
                    'tel_link': None,
                    'cor_setor': cor_original,
                })
            
        prontidao = mapa.prontidao or 'INDEFINIDA'
        equipe = mapa.equipe or '-'
        periodo = mapa.periodo or 'dia'
        ultimo_atualizacao = mapa.atualizado_em
    else:
        prontidao = 'NÃO INICIADO'
        equipe = '-'
        periodo = 'dia'
        ultimo_atualizacao = agora
        
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
        'oficial_area': oficial_area_data,
        'supervisor_servico': supervisor_servico_data,
        'prontidao': prontidao,
        'equipe': equipe,
        'periodo': periodo,
        'bg_class': bg_class,
        'border_class': border_class,
        'text_class': text_class,
        'icon_class': icon_class,
        'ultimo_atualizacao': ultimo_atualizacao,
        'mapa': mapa,
        'atualizacao_limite_padrao': '20:30',
        'atualizacao_equipe_diurna': 'ATÉ 18h30',
        'atualizacao_equipe_noturna': 'ATÉ 20h30',
        'cobom_address': 'Avenida João Jorge, 499 - Campinas - SP',
        'cobom_address_maps': 'https://www.google.com/maps/search/?api=1&query=Avenida+Jo%C3%A3o+Jorge%2C+499%2C+Campinas%2C+SP',
        'suporte_telefone': '(11) 3396-2243',
        'suporte_whatsapp': normalize_phone_for_whatsapp('(11) 3396-2243'),
        'suporte_email': 'cbmqualidadeop@policiamilitar.sp.gov.br',
        'editor_email_1': 'cb1icobom@policiamilitar.sp.gov.br',
        'editor_email_2': 'cb1icobom.suporte@policiamilitar.sp.gov.br',
        'base_template': 'base.html',
    }
    
    return render(request, 'dashboard/visao_cobom_efetivo.html', context)
