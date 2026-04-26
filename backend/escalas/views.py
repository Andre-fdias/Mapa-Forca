from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, JsonResponse
from django.utils import timezone
from django.utils.html import escape
from django.db.models import Q
from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend

from .models import MapaDiario, AlocacaoViatura, AlocacaoFuncionario, HistoricoAlteracao
from unidades.models import Unidade, Viatura, Posto
from efetivo.models import Funcionario, Efetivo
from dictionaries.models import Dictionary
from .serializers import (
    MapaDiarioSerializer, AlocacaoFuncionarioSerializer, 
    AlocacaoViaturaSerializer, CloneMapaSerializer
)
import re
import csv
import datetime

def normalize_opm_name(name):
    """Remove símbolos e espaços para comparação flexível."""
    if not name: return ""
    match = re.search(r'(\d+)', name)
    if match: return match.group(1)
    return re.sub(r'[^0-9]', '', name)

def get_data_operacional():
    """Retorna a data operacional baseada no horário de reset (07:40)."""
    agora = timezone.localtime(timezone.now())
    horario_reset = agora.replace(hour=7, minute=40, second=0, microsecond=0)
    if agora < horario_reset: return (agora - datetime.timedelta(days=1)).date()
    return agora.date()

def limpar_escalas_vencidas():
    """Limpa alocações do COBOM que já expiraram conforme as regras de horário."""
    agora = timezone.localtime(timezone.now())
    hoje = agora.date()
    ontem = hoje - datetime.timedelta(days=1)
    hora_atual = agora.time()
    if hora_atual >= datetime.time(18, 55):
        AlocacaoFuncionario.objects.filter(mapa__unidade__nome='CBI-1', mapa__data=hoje, inicio_servico=datetime.time(6, 45), termino_servico=datetime.time(19, 0)).delete()
    if hora_atual >= datetime.time(6, 55):
        AlocacaoFuncionario.objects.filter(mapa__unidade__nome='CBI-1', mapa__data=ontem, inicio_servico=datetime.time(18, 45), termino_servico=datetime.time(7, 0)).delete()
    if hora_atual >= datetime.time(7, 25):
        AlocacaoFuncionario.objects.filter(mapa__data=ontem, mapa__unidade__nome='CBI-1', inicio_servico=datetime.time(7, 30), termino_servico=datetime.time(7, 30)).delete()

@login_required
def atualizar_horario_alocacao(request, aloc_func_id):
    af = get_object_or_404(AlocacaoFuncionario, id=aloc_func_id)
    af.inicio_servico = request.POST.get('inicio_servico', af.inicio_servico)
    af.termino_servico = request.POST.get('termino_servico', af.termino_servico)
    af.sub_funcao = request.POST.get('sub_funcao', af.sub_funcao)
    af.save()
    HistoricoAlteracao.objects.create(mapa=af.mapa, usuario=request.user, tipo_acao='UPDATE', descricao=f"Atualizou {af.funcionario.nome_guerra}.")
    return render(request, 'mapa_forca/partials/linha_funcionario_viatura.html', {'aloc_func': af, 'is_cobom': af.alocacao_viatura is None})

@login_required
def compor_mapa_view(request):
    limpar_escalas_vencidas()
    hoje = get_data_operacional()
    u_id = request.GET.get('unidade_id')
    categoria = request.GET.get('categoria')
    sgb_param = request.GET.get('sgb')
    mapa = None
    
    user = request.user
    is_global_user = user.is_superuser or user.role in ['ADMIN', 'COBOM']

    # --- IDENTIFICAÇÃO DO BATALHÃO VINCULADO ---
    user_gb_name = None
    batalhao_vinculado = None
    if user.unidade:
        curr = user.unidade
        while curr:
            if curr.tipo_unidade and curr.tipo_unidade.codigo == 'BATALHAO':
                batalhao_vinculado = curr
                user_gb_name = curr.nome
                break
            if 'GB' in curr.nome.upper() and 'SGB' not in curr.nome.upper():
                batalhao_vinculado = curr
                user_gb_name = curr.nome
                break
            curr = curr.parent
        
        if not batalhao_vinculado:
            batalhao_vinculado = user.unidade.root_unit
            user_gb_name = batalhao_vinculado.nome

    # --- ROTEAMENTO COBOM (POSTOS DE TRABALHO DA PLANILHA) ---
    if user.role == 'COBOM' or categoria == 'CBI-1':
        unidade_cobom = Unidade.objects.filter(nome='CBI-1').first()
        if not unidade_cobom:
            unidade_cobom = Unidade.objects.create(nome='CBI-1', ativo=True)
            
        mapa, created = MapaDiario.objects.get_or_create(data=hoje, unidade=unidade_cobom, defaults={'criado_por': user})
        
        # Busca os POSTOS reais cadastrados com unidade='CBI-1' (conforme aba postos da planilha)
        postos_cobom = Posto.objects.filter(unidade__icontains='CBI-1').order_by('id')
        
        funcs_com_alocacoes = []
        if mapa:
            all_alocs = AlocacaoFuncionario.objects.filter(mapa=mapa, alocacao_viatura__isnull=True).select_related('funcionario', 'funcao')
            for posto in postos_cobom:
                # Localiza ou cria a função correspondente ao nome do posto para salvar na alocação
                funcao_obj, _ = Dictionary.objects.get_or_create(
                    tipo='FUNCAO_OPERACIONAL_COBOM',
                    nome=posto.nome.upper(),
                    defaults={'codigo': posto.nome.upper().replace(' ', '_')[:100], 'ativo': True}
                )

                funcs_com_alocacoes.append({
                    'funcao': funcao_obj,
                    'posto_nome': posto.nome,
                    'alocacoes': all_alocs.filter(funcao=funcao_obj)
                })

        context = {
            'mapa': mapa, 'hoje': hoje, 'user_gb': 'COBOM',
            'funcs_com_alocacoes': funcs_com_alocacoes,
            'base_template': 'base.html'
        }
        return render(request, 'mapa_forca/compor_mapa_cobom.html', context)

    # --- ROTEAMENTO GB (MANTIDO ORIGINAL) ---
    unidade_obj = get_object_or_404(Unidade, id=u_id) if u_id else user.unidade
    if unidade_obj:
        mapa, created = MapaDiario.objects.get_or_create(data=hoje, unidade=unidade_obj, defaults={'criado_por': user})

    lista_opm = list(Posto.objects.exclude(unidade__isnull=True).exclude(unidade='').values_list('unidade', flat=True).distinct().order_by('unidade'))
    if not is_global_user and user_gb_name: categoria = user_gb_name
    elif not categoria and lista_opm: categoria = lista_opm[0]

    lista_sgbs = []
    qs_unidades = Unidade.objects.none()
    if categoria:
        match_gb = re.search(r'(\d+)', categoria)
        gb_num = match_gb.group(1) if match_gb else ""
        q_planilha = Q(unidade__icontains=categoria)
        if gb_num: q_planilha |= Q(unidade__icontains=f"{gb_num}")
        lista_sgbs = list(Posto.objects.filter(q_planilha).exclude(sgb__isnull=True).exclude(sgb='').values_list('sgb', flat=True).distinct().order_by('sgb'))
        
        filtro_postos_final = q_planilha
        if sgb_param: filtro_postos_final &= Q(sgb=sgb_param)
        dados_postos = Posto.objects.filter(filtro_postos_final).values('cod_secao', 'nome')
        codigos = [d['cod_secao'] for d in dados_postos if d['cod_secao']]
        nomes = [d['nome'] for d in dados_postos]
        qs_unidades = Unidade.objects.filter(Q(codigo_secao__in=codigos) | Q(nome__in=nomes)).distinct()
    
    viaturas_disponiveis = []
    if categoria:
        match_gb_vtr = re.search(r'(\d+)', categoria)
        gb_num_vtr = match_gb_vtr.group(1) if match_gb_vtr else ""
        q_vtr = Q(opmcb__icontains=categoria)
        if gb_num_vtr: q_vtr |= Q(opmcb__icontains=f"{gb_num_vtr}º GB") | Q(opmcb__icontains=f"{gb_num_vtr} GB")
        viats_qs = Viatura.objects.filter(q_vtr).exclude(prefixo='TELEGRAFIA')
        viaturas_disponiveis = list(viats_qs.order_by('prefixo'))
    
    funcoes_qs = Dictionary.objects.filter(Q(tipo='FUNCAO_OPERACIONAL') | Q(tipo='FUNCAO_OPERACIONAL_GB'), ativo=True).order_by('ordem', 'nome')

    context = {
        'mapa': mapa, 'todas_unidades': qs_unidades.order_by('nome'), 'viaturas_disponiveis': viaturas_disponiveis,
        'categorias_opm': lista_opm, 'categoria_selecionada': categoria, 'lista_sgbs': lista_sgbs,
        'sgb_selecionado': sgb_param, 'user_gb': user_gb_name, 'hoje': hoje,
        'funcoes': funcoes_qs, 'base_template': 'base.html'
    }
    return render(request, 'escalas/compor_mapa.html', context)

@login_required
def buscar_funcionario_re(request):
    q = request.GET.get('funcionario_re', '').strip()
    if len(q) < 2: return HttpResponse('')
    ef_queryset = Efetivo.objects.filter(Q(nome__icontains=q) | Q(nome_do_pm__icontains=q) | Q(re__icontains=re.sub(r'\D', '', q)))
    cat = request.GET.get('categoria')
    if cat and cat != 'CBI-1': ef_queryset = ef_queryset.filter(unidade__icontains=cat.replace('º','').replace('°','').strip())
    efetivo = list(ef_queryset.order_by('nome')[:15])
    for e in efetivo: e.indisponivel = AlocacaoFuncionario.objects.filter(mapa__data=get_data_operacional(), funcionario__nome_completo__iexact=e.nome_do_pm or e.nome).first()
    return render(request, 'mapa_forca/partials/lista_busca_funcionarios.html', {'efetivo_extra': efetivo, 'query': q})

@login_required
def adicionar_viatura_mapa(request, mapa_id):
    pref = request.POST.get('prefixo')
    mapa = get_object_or_404(MapaDiario, id=mapa_id)
    if pref == 'TELEGRAFIA':
        v, _ = Viatura.objects.get_or_create(prefixo='TELEGRAFIA', defaults={'placa': 'INTERNO'})
    else:
        v = get_object_or_404(Viatura, prefixo=pref)
        ja = AlocacaoViatura.objects.filter(mapa__data=mapa.data, viatura=v).exclude(mapa=mapa).first()
        if ja: return HttpResponse(f'<script>showToast("Viatura {v.prefixo} já está em {ja.mapa.unidade.nome}", "error");</script>')
    
    # Define status OPERANDO como padrão para novas alocações
    status_op = Dictionary.objects.filter(tipo='STATUS_VIATURA', codigo='OPERANDO').first()
    aloc, created = AlocacaoViatura.objects.get_or_create(mapa=mapa, viatura=v, defaults={'status_no_dia': status_op})
    
    return render(request, 'mapa_forca/partials/card_viatura_alocada.html', {'alocacao': aloc, 'funcoes': Dictionary.objects.filter(tipo='FUNCAO_OPERACIONAL')})

@login_required
def alocar_funcionario_viatura(request, alocacao_viatura_id):
    re_in = request.POST.get('funcionario_re', '').strip()
    efetivo_id = request.POST.get('efetivo_id')
    f_id = request.POST.get('funcao_id')
    mapa_id = request.POST.get('mapa_id')
    
    aloc_v = get_object_or_404(AlocacaoViatura, id=alocacao_viatura_id) if alocacao_viatura_id and int(alocacao_viatura_id) != 0 else None
    mapa = aloc_v.mapa if aloc_v else get_object_or_404(MapaDiario, id=mapa_id)
    
    funcao = get_object_or_404(Dictionary, id=f_id)
    militar = Funcionario.objects.filter(re=re_in).first()
    
    if not militar:
        ef = Efetivo.objects.filter(Q(re=re_in) | Q(nome__icontains=re_in)).first()
        if ef:
            militar = Funcionario.objects.filter(re=ef.re).first()
            if not militar:
                p_grad = Dictionary.objects.filter(tipo='POSTO_GRADUACAO', nome__icontains=str(ef.posto_secao)[:3]).first()
                nguerra = ef.nome.split()[-1] if ef.nome else "MILITAR"
                militar = Funcionario.objects.create(re=ef.re or re_in, nome_completo=ef.nome, nome_guerra=nguerra, posto_graduacao=p_grad, mergulho=ef.mergulho, ovb=ef.ovb)
    
    if militar:
        if AlocacaoFuncionario.objects.filter(mapa__data=mapa.data, funcionario=militar).exists():
            return HttpResponse(f'<script>showToast("Militar {militar.nome_guerra} já escalado hoje!", "error");</script>')
        
        # --- REGRA DE SUPERVISÃO GB COBOM ---
        sub_f = ""
        f_nome_upper = funcao.nome.upper()
        if "SUPERVISOR" in f_nome_upper and "GB" in f_nome_upper:
            posto_nome = militar.posto_graduacao.nome.upper() if militar.posto_graduacao else ""
            if any(rank in posto_nome for rank in ["CAP", "TEN"]):
                sub_f = "supervisor"
            elif any(rank in posto_nome for rank in ["SGT", "CB", "SD"]):
                sub_f = "motorista"

        af = AlocacaoFuncionario.objects.create(
            mapa=mapa, 
            alocacao_viatura=aloc_v, 
            funcionario=militar, 
            funcao=funcao, 
            sub_funcao=sub_f,
            dejem=request.POST.get('dejem') == 'true', 
            inicio_servico="07:30:00", 
            termino_servico="07:30:00"
        )
        
        HistoricoAlteracao.objects.create(mapa=mapa, usuario=request.user, tipo_acao='UPDATE', descricao=f"Alocou {militar.nome_guerra} em {funcao.nome}.")
        return render(request, 'mapa_forca/partials/linha_funcionario_viatura.html', {'aloc_func': af, 'is_cobom': aloc_v is None})
    
    return HttpResponse('<script>showToast("Erro: Militar não localizado!", "error");</script>')

@login_required
def remover_viatura_mapa(request, alocacao_id):
    AlocacaoViatura.objects.filter(id=alocacao_id).delete(); return HttpResponse("")
@login_required
def remover_funcionario_viatura(request, aloc_func_id):
    AlocacaoFuncionario.objects.filter(id=aloc_func_id).delete(); return HttpResponse("")
@login_required
def validar_mapa_final(request, mapa_id):
    mapa = get_object_or_404(MapaDiario, id=mapa_id); mapa.finalizado = True; mapa.save()
    return HttpResponse('<script>showToast("MAPA FINALIZADO!", "success"); setTimeout(() => { window.location.href = "/unidades/dashboard/"; }, 2000);</script>')
@login_required
def get_viaturas_por_unidade(request):
    gb = request.GET.get('categoria', '')
    viats = Viatura.objects.filter(opmcb__icontains=gb.replace('º','').replace('°','')).exclude(prefixo='TELEGRAFIA')
    data = [{'VIATURAS': v.prefixo, 'SGB': v.sgb, 'STATUS': v.status_base.nome if v.status_base else 'RESERVA'} for v in viats]
    return JsonResponse(data, safe=False)
@login_required
def update_mapa_cobom(request, mapa_id):
    mapa = get_object_or_404(MapaDiario, id=mapa_id)
    for field in ['prontidao', 'equipe', 'periodo']:
        if field in request.POST: setattr(mapa, field, request.POST.get(field))
    mapa.save(); return HttpResponse("")
@login_required
def historico_view(request):
    data_str = request.GET.get('data')
    data_selecionada = timezone.datetime.strptime(data_str, '%Y-%m-%d').date() if data_str else timezone.now().date()
    mapas = MapaDiario.objects.filter(data=data_selecionada).select_related('unidade')
    return render(request, 'escalas/historico.html', {'mapas': mapas, 'data_selecionada': data_selecionada})
class MapaDiarioViewSet(viewsets.ModelViewSet): queryset = MapaDiario.objects.all(); serializer_class = MapaDiarioSerializer
class AlocacaoFuncionarioViewSet(viewsets.ModelViewSet): queryset = AlocacaoFuncionario.objects.all(); serializer_class = AlocacaoFuncionarioSerializer
class AlocacaoViaturaViewSet(viewsets.ModelViewSet): queryset = AlocacaoViatura.objects.all(); serializer_class = AlocacaoViaturaSerializer
