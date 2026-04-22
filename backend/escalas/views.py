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
    is_restricted = not user.is_superuser and user.role not in ['ADMIN', 'COBOM']

    user_root_unit = None
    if user.unidade:
        curr = user.unidade
        while curr:
            if 'GB' in curr.nome.upper() and 'SGB' not in curr.nome.upper(): user_root_unit = curr.nome; break
            curr = curr.parent
        if not user_root_unit and user.unidade.root_unit: user_root_unit = user.unidade.root_unit.nome

    lista_opm = list(Posto.objects.exclude(unidade__isnull=True).exclude(unidade='').values_list('unidade', flat=True).distinct().order_by('unidade'))
    if is_restricted and user_root_unit: categoria = user_root_unit
    elif not categoria and lista_opm: categoria = lista_opm[0]

    unidade_obj = None
    if u_id:
        unidade_obj = get_object_or_404(Unidade, id=u_id)
        if is_restricted:
            curr_target = unidade_obj
            target_root = None
            while curr_target:
                if 'GB' in curr_target.nome.upper() and 'SGB' not in curr_target.nome.upper(): target_root = curr_target.nome; break
                curr_target = curr_target.parent
            if not target_root: target_root = unidade_obj.root_unit.nome if (unidade_obj.root_unit and unidade_obj.root_unit.nome) else unidade_obj.nome
            if normalize_opm_name(target_root) != normalize_opm_name(user_root_unit): unidade_obj = user.unidade
            else:
                if user.role == 'SGB':
                    p_target = Posto.objects.filter(Q(cod_secao=unidade_obj.codigo_secao) | Q(nome=unidade_obj.nome)).first()
                    p_user = Posto.objects.filter(Q(cod_secao=user.unidade.codigo_secao) | Q(nome=user.unidade.nome)).first()
                    if p_target and p_user and p_target.sgb != p_user.sgb: unidade_obj = user.unidade
                elif user.role == 'POSTO' and unidade_obj != user.unidade: unidade_obj = user.unidade
    else: unidade_obj = user.unidade

    if unidade_obj:
        mapa, created = MapaDiario.objects.get_or_create(data=hoje, unidade=unidade_obj, defaults={'criado_por': user})

    lista_sgbs = []
    qs_unidades = Unidade.objects.none()
    if categoria:
        match_gb = re.search(r'(\d+)', categoria)
        gb_num = match_gb.group(1) if match_gb else ""
        q_planilha = Q(unidade__icontains=categoria)
        if gb_num: q_planilha |= Q(unidade__icontains=f"{gb_num}")
        lista_sgbs = list(Posto.objects.filter(q_planilha).exclude(sgb__isnull=True).exclude(sgb='').values_list('sgb', flat=True).distinct().order_by('sgb'))
        if is_restricted and user.role == 'SGB':
            p_user = Posto.objects.filter(Q(cod_secao=user.unidade.codigo_secao) | Q(nome=user.unidade.nome)).first()
            if p_user: sgb_param = p_user.sgb
        filtro_postos_final = q_planilha
        if sgb_param: filtro_postos_final &= Q(sgb=sgb_param)
        dados_postos = Posto.objects.filter(filtro_postos_final).values('cod_secao', 'nome')
        codigos = [d['cod_secao'] for d in dados_postos if d['cod_secao']]
        nomes = [d['nome'] for d in dados_postos]
        qs_unidades = Unidade.objects.filter(Q(codigo_secao__in=codigos) | Q(nome__in=nomes)).distinct()
        if not qs_unidades.exists() and not sgb_param: qs_unidades = Unidade.objects.filter(Q(nome__icontains=gb_num) | Q(parent__nome__icontains=gb_num))
    if is_restricted and user.role == 'POSTO': qs_unidades = Unidade.objects.filter(id=user.unidade.id)
    todas_unidades = qs_unidades.order_by('nome')

    viaturas_disponiveis = []
    if categoria:
        match_gb_vtr = re.search(r'(\d+)', categoria)
        gb_num_vtr = match_gb_vtr.group(1) if match_gb_vtr else ""
        q_vtr = Q(opmcb__icontains=categoria)
        if gb_num_vtr:
            q_vtr |= Q(opmcb__icontains=f"{gb_num_vtr}º GB")
            q_vtr |= Q(opmcb__icontains=f"{gb_num_vtr} GB")
            q_vtr |= Q(opmcb__icontains=f"{gb_num_vtr}GB")
            q_vtr |= Q(prefixo__startswith=f"{gb_num_vtr}")
        viats_qs = Viatura.objects.filter(q_vtr).exclude(prefixo='TELEGRAFIA')
        viaturas_disponiveis = list(viats_qs.order_by('prefixo'))
        v_telegrafia = Viatura.objects.filter(prefixo='TELEGRAFIA').first()
        if v_telegrafia: viaturas_disponiveis.insert(0, v_telegrafia)
        else: viaturas_disponiveis.insert(0, Viatura(prefixo='TELEGRAFIA', placa='SALA'))

    context = {
        'mapa': mapa, 'todas_unidades': todas_unidades, 'viaturas_disponiveis': viaturas_disponiveis,
        'categorias_opm': lista_opm, 'categoria_selecionada': categoria, 'lista_sgbs': lista_sgbs,
        'sgb_selecionado': sgb_param, 'user_gb': user_root_unit, 'hoje': hoje,
        'funcoes': Dictionary.objects.filter(tipo='FUNCAO_OPERACIONAL'),
    }
    if request.headers.get('HX-Request') and not u_id: return render(request, 'escalas/partials/filtros_unidade_compor.html', context)
    
    # Roteamento baseado no nível de acesso (Role)
    if user.role == 'COBOM':
        funcs_com_alocacoes = []
        if mapa:
            # Para o COBOM, buscamos alocações que não estão vinculadas a viaturas
            all_alocs = AlocacaoFuncionario.objects.filter(
                mapa=mapa, 
                alocacao_viatura__isnull=True
            ).select_related('funcionario', 'funcao')
            
            for fn in context['funcoes']:
                funcs_com_alocacoes.append({
                    'funcao': fn,
                    'alocacoes': all_alocs.filter(funcao=fn)
                })
        
        context.update({
            'base_template': 'base.html',
            'funcs_com_alocacoes': funcs_com_alocacoes,
        })
        return render(request, 'mapa_forca/compor_mapa_cobom.html', context)

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
        af = AlocacaoFuncionario.objects.create(mapa=mapa, alocacao_viatura=aloc_v, funcionario=militar, funcao_id=f_id, dejem=request.POST.get('dejem') == 'true', inicio_servico="07:30:00", termino_servico="07:30:00")
        HistoricoAlteracao.objects.create(mapa=mapa, usuario=request.user, tipo_acao='UPDATE', descricao=f"Alocou {militar.nome_guerra}.")
        return render(request, 'mapa_forca/partials/linha_funcionario_viatura.html', {'aloc_func': af, 'is_cobom': aloc_v is None})
    return HttpResponse('<script>showToast("Erro: Militar não localizado na planilha!", "error");</script>')

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
