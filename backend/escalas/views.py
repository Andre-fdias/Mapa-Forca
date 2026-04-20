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

def get_data_operacional():
    """Retorna a data operacional baseada no horário de reset (07:40)."""
    agora = timezone.localtime(timezone.now())
    horario_reset = agora.replace(hour=7, minute=40, second=0, microsecond=0)
    if agora < horario_reset:
        return (agora - datetime.timedelta(days=1)).date()
    return agora.date()

def limpar_escalas_vencidas():
    """Limpa alocações do COBOM que já expiraram conforme as regras de horário."""
    agora = timezone.localtime(timezone.now())
    hoje = agora.date()
    ontem = hoje - datetime.timedelta(days=1)
    hora_atual = agora.time()
    
    # 1. 12hs (06:45 - 19:00): Limpa às 18:55 do próprio dia
    if hora_atual >= datetime.time(18, 55):
        AlocacaoFuncionario.objects.filter(
            mapa__unidade__nome='CBI-1',
            mapa__data=hoje,
            inicio_servico=datetime.time(6, 45),
            termino_servico=datetime.time(19, 0)
        ).delete()

    # 2. 12hs (18:45 - 07:00): Limpa às 06:55 do dia seguinte (referente a ontem)
    if hora_atual >= datetime.time(6, 55):
        AlocacaoFuncionario.objects.filter(
            mapa__unidade__nome='CBI-1',
            mapa__data=ontem,
            inicio_servico=datetime.time(18, 45),
            termino_servico=datetime.time(7, 0)
        ).delete()

    # 3. 24hs (07:30 - 07:30): Limpa às 07:25 do dia do término (referente a ontem)
    if hora_atual >= datetime.time(7, 25):
        AlocacaoFuncionario.objects.filter(
            mapa__data=ontem,
            mapa__unidade__nome='CBI-1',
            inicio_servico=datetime.time(7, 30),
            termino_servico=datetime.time(7, 30)
        ).delete()

@login_required
def atualizar_horario_alocacao(request, aloc_func_id):
    af = get_object_or_404(AlocacaoFuncionario, id=aloc_func_id)
    inicio = request.POST.get('inicio_servico')
    termino = request.POST.get('termino_servico')
    sub_funcao = request.POST.get('sub_funcao')
    
    if inicio and termino:
        af.inicio_servico = inicio
        af.termino_servico = termino
    
    if sub_funcao is not None:
        af.sub_funcao = sub_funcao
        
    af.save()
        
    HistoricoAlteracao.objects.create(
        mapa=af.mapa,
        usuario=request.user,
        tipo_acao='UPDATE',
        descricao=f"Atualizou dados de {af.funcionario.nome_guerra}."
    )
    
    return render(request, 'mapa_forca/partials/linha_funcionario_viatura.html', {'aloc_func': af, 'is_cobom': af.alocacao_viatura is None})

@login_required
def compor_mapa_view(request):
    limpar_escalas_vencidas()
    hoje = get_data_operacional()
    u_id = request.GET.get('unidade_id')
    categoria = request.GET.get('categoria')
    mapa = None
    

    # 1. IDENTIFICAÇÃO DE ACESSO E CATEGORIA (OPM)
    user_root_unit = None
    if request.user.unidade:
        user_root_unit = request.user.unidade.root_unit.nome

    # Lógica de Categorias (Grupamentos)
    qs_opm = Posto.objects.exclude(unidade__isnull=True).exclude(unidade='')
    if request.user.role not in ['ADMIN', 'COBOM'] and user_root_unit:
        # Usuários regionais ficam presos ao seu Grupamento
        qs_opm = qs_opm.filter(unidade=user_root_unit)
        categoria = user_root_unit
    
    lista_opm = list(qs_opm.values_list('unidade', flat=True).distinct().order_by('unidade'))
    
    if not categoria:
        categoria = user_root_unit if user_root_unit else (lista_opm[0] if lista_opm else '15º GB')

    # 2. DEFINIÇÃO DA UNIDADE SELECIONADA E SEGURANÇA
    unidade_obj = None
    if u_id:
        unidade_obj = get_object_or_404(Unidade, id=u_id)
        # Bloqueio de segurança: impede que usuários regionais acessem unidades fora do seu escopo
        if request.user.role not in ['ADMIN', 'COBOM']:
            if request.user.role == 'BATALHAO' and unidade_obj.root_unit.nome != user_root_unit:
                unidade_obj = request.user.unidade
            elif request.user.role == 'SGB' and (unidade_obj != request.user.unidade and unidade_obj.parent != request.user.unidade):
                unidade_obj = request.user.unidade
            elif request.user.role == 'POSTO' and unidade_obj != request.user.unidade:
                unidade_obj = request.user.unidade
    else:
        # Se não houver ID na URL, tenta usar a unidade do usuário
        if request.user.unidade:
            unidade_obj = request.user.unidade

    # 3. CRIAÇÃO/BUSCA DO MAPA
    if unidade_obj:
        mapa, created = MapaDiario.objects.get_or_create(
            data=hoje, 
            unidade=unidade_obj, 
            defaults={'criado_por': request.user}
        )
        if created:
            HistoricoAlteracao.objects.create(
                mapa=mapa, usuario=request.user, tipo_acao='CREATE',
                descricao=f"Iniciou a composição do mapa força para {unidade_obj.nome}."
            )

    # 4. FILTRAGEM DA LISTA DE UNIDADES (O QUE APARECE NO SELETOR)
    codigos_secao = list(Posto.objects.filter(unidade=categoria).values_list('cod_secao', flat=True))
    qs_unidades = Unidade.objects.filter(
        Q(codigo_secao__in=codigos_secao) | 
        Q(parent__nome__icontains=categoria.replace('º', '').replace('°', '').strip())
    ).distinct()

    if request.user.role == 'SGB':
        qs_unidades = qs_unidades.filter(Q(id=request.user.unidade.id) | Q(parent=request.user.unidade))
    elif request.user.role == 'POSTO':
        qs_unidades = qs_unidades.filter(id=request.user.unidade.id)

    todas_unidades = qs_unidades.order_by('nome')

    # 5. PREPARAÇÃO DO CONTEXTO
    viaturas_disponiveis = []
    if categoria:
        # Filtra todas as viaturas pertencentes ao Grupamento (OPM) selecionado
        viaturas_disponiveis = Viatura.objects.filter(
            opmcb__icontains=categoria.strip()
        ).exclude(prefixo='TELEGRAFIA').order_by('prefixo')

    context = {
        'mapa': mapa, 
        'todas_unidades': todas_unidades,
        'unidade_selecionada': unidade_obj, 
        'viaturas_disponiveis': viaturas_disponiveis,
        'categorias_opm': lista_opm,
        'categoria_selecionada': categoria,
        'funcoes': Dictionary.objects.filter(tipo='FUNCAO_OPERACIONAL'),
        'user_gb': user_root_unit,
        'hoje': hoje,
        'base_template': 'base/partial.html' if request.headers.get('HX-Request') else 'base/base.html'
    }

    # 6. SELEÇÃO DE TEMPLATE BASEADO NA ROLE
    if request.user.role == 'COBOM':
        # Lógica adicional para funções específicas do COBOM
        f_names = ['Oficial de Operações DEJEM', 'Chefe de Equipe', 'Supervisor Despacho', 'Supervisor 193', 'Supervisor 7º GB', 'Cabine 7º GB', 'Supervisor 19º GB', 'Cabine 19º GB', 'Supervisor 15º GB', 'Cabine 15º GB', 'Supervisor 16º GB', 'Cabine 16º GB', 'Apoio Cabine 7º, 19º e 15º GB', 'Apoio Cabine 16º GB', 'Enfermeiro de Triagem', 'Inclusor', 'Supervisor COE Autoban', 'Atendente 193']
        funcoes_cobom = Dictionary.objects.filter(tipo='FUNCAO_OPERACIONAL', nome__in=f_names)
        
        funcs_com_alocacoes = []
        for f in funcoes_cobom:
            alocs = []
            if mapa:
                alocs = AlocacaoFuncionario.objects.filter(mapa=mapa, funcao=f)
            funcs_com_alocacoes.append({'funcao': f, 'alocacoes': alocs})
            
        context['funcs_com_alocacoes'] = funcs_com_alocacoes
        return render(request, 'mapa_forca/compor_mapa_cobom.html', context)

    # Caso padrão (Escalas de Posto/Batalhão/Admin)
    if request.headers.get('HX-Request') and not u_id:
        return render(request, 'mapa_forca/partials/select_postos.html', context)
        
    return render(request, 'escalas/compor_mapa.html', context)

@login_required
def buscar_funcionario_re(request):
    q = request.GET.get('funcionario_re', '').strip()
    mapa_id = request.GET.get('mapa_id')
    categoria = request.GET.get('categoria') # Captura a categoria (GB) selecionada
    
    if len(q) < 2: return HttpResponse('')
    
    # Limpa o Q para busca numérica se parecer um RE
    q_numeric = re.sub(r'\D', '', q)
    
    mapa_atual = get_object_or_404(MapaDiario, id=mapa_id) if mapa_id else None
    data_escala = mapa_atual.data if mapa_atual else get_data_operacional()
    
    efetivo_real = []
    funcs_locais = []

    # 1. BUSCA NO EFETIVO (DADOS DA PLANILHA)
    query_efetivo = Q(nome__icontains=q) | Q(nome_do_pm__icontains=q)
    if q_numeric:
        query_efetivo |= Q(re__icontains=q_numeric)
    
    ef_queryset = Efetivo.objects.filter(query_efetivo)
    
    # Aplica filtro de unidade se a categoria for informada e não for CBI-1 (COBOM)
    if categoria and categoria != 'CBI-1':
        ef_queryset = ef_queryset.filter(unidade__icontains=categoria.strip())
    
    efetivo_real = list(ef_queryset.order_by('nome')[:15])
    
    # 2. BUSCA NO LOCAL (FUNCIONARIOS JÁ CADASTRADOS)
    query_func = Q(nome_completo__icontains=q) | Q(nome_guerra__icontains=q)
    if q_numeric:
        query_func |= Q(re__icontains=q_numeric)
        
    funcs_locais = list(Funcionario.objects.filter(query_func).select_related('posto_graduacao').order_by('nome_completo')[:5])
    
    return render_busca_results(request, efetivo_real, funcs_locais, data_escala, q)

def render_busca_results(request, efetivo_real, funcs_locais, data_escala, query):
    """Função auxiliar para processar disponibilidade e renderizar o template."""
    # Verifica disponibilidade para cada resultado
    for e in efetivo_real:
        ja_alocado = AlocacaoFuncionario.objects.filter(
            mapa__data=data_escala,
            funcionario__nome_completo__iexact=e.nome_do_pm or e.nome
        ).select_related('alocacao_viatura__viatura', 'mapa__unidade').first()
        e.indisponivel = ja_alocado
        
    for f in funcs_locais:
        ja_alocado = AlocacaoFuncionario.objects.filter(
            mapa__data=data_escala,
            funcionario=f
        ).select_related('alocacao_viatura__viatura', 'mapa__unidade').first()
        f.indisponivel = ja_alocado
    
    return render(request, 'mapa_forca/partials/lista_busca_funcionarios.html', {
        'efetivo_extra': efetivo_real,
        'funcionarios': funcs_locais,
        'query': query
    })

@login_required
def adicionar_viatura_mapa(request, mapa_id):
    pref = request.POST.get('prefixo')
    mapa = get_object_or_404(MapaDiario, id=mapa_id)
    
    # Busca a viatura. Se for TELEGRAFIA e não existir, cria.
    if pref == 'TELEGRAFIA':
        status_op = Dictionary.objects.filter(tipo='STATUS_VIATURA', codigo='OPERANDO').first()
        tipo_vtr = Dictionary.objects.filter(tipo='TIPO_VIATURA', codigo='OUTROS').first()
        viat, _ = Viatura.objects.get_or_create(
            prefixo='TELEGRAFIA',
            defaults={
                'placa': 'INTERNO',
                'status_base': status_op,
                'tipo': tipo_vtr,
                'fonte': 'Sistema (Virtual)'
            }
        )
    else:
        viat = get_object_or_404(Viatura, prefixo=pref)
    
    # Validação: Viatura única por dia em todo o sistema (EXCETO TELEGRAFIA)
    if viat.prefixo != 'TELEGRAFIA':
        ja_alocada = AlocacaoViatura.objects.filter(
            mapa__data=mapa.data, 
            viatura=viat
        ).exclude(mapa=mapa).select_related('mapa__unidade').first()
        
        if ja_alocada:
            msg = f"A viatura {viat.prefixo} já está escalada hoje na unidade: {ja_alocada.mapa.unidade.nome}"
            return HttpResponse(f'<script>showToast("{msg}", "error");</script>')

    status_op = Dictionary.objects.filter(tipo='STATUS_VIATURA', codigo='OPERANDO').first()
    aloc, created = AlocacaoViatura.objects.get_or_create(mapa=mapa, viatura=viat, defaults={'status_no_dia': status_op})
    
    if not created:
        # Se já existe no mapa, apenas avisa e não retorna novo HTML para evitar duplicidade na tela
        return HttpResponse(f'<script>showToast("Viatura {viat.prefixo} já está no mapa.", "info");</script>', status=200)

    HistoricoAlteracao.objects.create(
        mapa=mapa,
        usuario=request.user,
        tipo_acao='UPDATE',
        descricao=f"Adicionou viatura {viat.prefixo} ao mapa."
    )
        
    return render(request, 'mapa_forca/partials/card_viatura_alocada.html', {'alocacao': aloc, 'funcoes': Dictionary.objects.filter(tipo='FUNCAO_OPERACIONAL')})

@login_required
def alocar_funcionario_viatura(request, alocacao_viatura_id):
    re_in = request.POST.get('funcionario_re', '').strip()
    nome_ex = request.POST.get('nome_extra', '').strip()
    efetivo_id = request.POST.get('efetivo_id')
    f_id = request.POST.get('funcao_id')
    dejem_val = request.POST.get('dejem') == 'true'
    inicio_dejem = request.POST.get('inicio_dejem')
    termino_dejem = request.POST.get('termino_dejem')
    
    # Horários COBOM
    inicio_servico = request.POST.get('inicio_servico')
    termino_servico = request.POST.get('termino_servico')
    
    if alocacao_viatura_id and int(alocacao_viatura_id) != 0:
        aloc_v = get_object_or_404(AlocacaoViatura, id=alocacao_viatura_id)
        mapa_aloc = aloc_v.mapa
        if aloc_v.equipe.count() >= 15: return HttpResponse('<script>showToast("Limite de 15 atingido!", "error");</script>')
    else:
        aloc_v = None
        # Precisamos do mapa_id do POST para alocações avulsas
        mapa_id = request.POST.get('mapa_id')
        mapa_aloc = get_object_or_404(MapaDiario, id=mapa_id)

    funcao = get_object_or_404(Dictionary, id=f_id)

    # 1. Busca no Efetivo Real (Dados do Sheets)
    efetivo_real = None
    if efetivo_id:
        efetivo_real = Efetivo.objects.filter(id=efetivo_id).first()
    if not efetivo_real:
        efetivo_real = Efetivo.objects.filter(Q(re=re_in) | Q(nome=nome_ex or re_in)).first()

    # 2. Tenta achar o militar local
    militar = None
    if efetivo_real and efetivo_real.re:
        militar = Funcionario.objects.filter(re=efetivo_real.re).first()
    if not militar:
        militar = Funcionario.objects.filter(re=re_in).first()
    if not militar:
        militar = Funcionario.objects.filter(nome_completo__iexact=nome_ex if nome_ex else re_in).first()

    # 3. Cria ou atualiza o militar local com os dados reais
    if efetivo_real:
        nome_padrao = efetivo_real.nome 
        re_match = re.search(r'(\d{6}-\d{1})', nome_padrao)
        re_real = re_match.group(1) if re_match else (efetivo_real.re if efetivo_real.re else None)
        
        if not re_real:
            import hashlib
            re_real = f"T-{hashlib.md5(nome_padrao.encode()).hexdigest()[:6]}"

        p_codigo = "SD_PM"
        if 'SUB' in nome_padrao: p_codigo = 'SUBTEN_PM'
        elif 'SGT' in nome_padrao: p_codigo = 'SGT_PM'
        elif 'CB' in nome_padrao: p_codigo = 'CB_PM'
        elif 'SD' in nome_padrao: p_codigo = 'SD_PM'
        elif '1º TEN' in nome_padrao: p_codigo = 'TEN_PM'
        elif '2º TEN' in nome_padrao: p_codigo = 'TEN_PM'
        elif 'CAP' in nome_padrao: p_codigo = 'CAP_PM'
        elif 'MAJ' in nome_padrao: p_codigo = 'MAJ_PM'
        
        posto_obj = Dictionary.objects.filter(tipo='POSTO_GRADUACAO', codigo=p_codigo).first()
        nguerra = nome_padrao.split(')')[-1].strip() if ')' in nome_padrao else nome_padrao.split()[-1]

        if not militar:
            militar = Funcionario.objects.create(
                re=re_real,
                nome_completo=nome_padrao,
                nome_guerra=nguerra,
                posto_graduacao=posto_obj,
                mergulho=efetivo_real.mergulho,
                ovb=efetivo_real.ovb
            )
        else:
            militar.nome_completo = nome_padrao
            militar.mergulho = efetivo_real.mergulho
            militar.ovb = efetivo_real.ovb
            if posto_obj: militar.posto_graduacao = posto_obj
            militar.save()

    # 4. Finaliza a alocação
    if militar:
        # Trava: Militar só pode ser escalado uma vez por dia (Unicidade Diária)
        ja_alocado_hoje = AlocacaoFuncionario.objects.filter(
            mapa__data=mapa_aloc.data, 
            funcionario=militar
        ).first()
        
        if ja_alocado_hoje:
            msg = f"Militar já escalado hoje em {ja_alocado_hoje.mapa.unidade.nome}!"
            return HttpResponse(f'<script>showToast("{msg}", "error");</script>')

        # Define horários padrão se não informados (para GB é sempre 07:30 - 07:30)
        if not inicio_servico:
            inicio_servico = "07:30:00"
            termino_servico = "07:30:00"

        af = AlocacaoFuncionario.objects.create(
            mapa=mapa_aloc, 
            alocacao_viatura=aloc_v, 
            funcionario=militar, 
            funcao=funcao,
            dejem=(dejem_val == True),
            inicio_dejem=inicio_dejem if dejem_val and inicio_dejem else None,
            termino_dejem=termino_dejem if dejem_val and termino_dejem else None,
            inicio_servico=inicio_servico,
            termino_servico=termino_servico
        )
        
        vtr_prefix = aloc_v.viatura.prefixo if aloc_v else "Avulso"
        HistoricoAlteracao.objects.create(
            mapa=mapa_aloc,
            usuario=request.user,
            tipo_acao='UPDATE',
            descricao=f"Alocou {militar.nome_guerra} na viatura {vtr_prefix} como {funcao.nome}."
        )
        
        return render(request, 'mapa_forca/partials/linha_funcionario_viatura.html', {'aloc_func': af, 'is_cobom': aloc_v is None})
    
    return HttpResponse('<script>showToast("Erro ao processar militar!", "error");</script>')

@login_required
def remover_viatura_mapa(request, alocacao_id):
    aloc = get_object_or_404(AlocacaoViatura, id=alocacao_id)
    mapa = aloc.mapa
    pref = aloc.viatura.prefixo
    aloc.delete()
    
    HistoricoAlteracao.objects.create(
        mapa=mapa,
        usuario=request.user,
        tipo_acao='DELETE',
        descricao=f"Removeu viatura {pref} do mapa."
    )
    return HttpResponse("")

@login_required
def remover_funcionario_viatura(request, aloc_func_id):
    af = get_object_or_404(AlocacaoFuncionario, id=aloc_func_id)
    mapa = af.mapa
    nome = af.funcionario.nome_guerra
    vtr = af.alocacao_viatura.viatura.prefixo if af.alocacao_viatura else "Avulso"
    af.delete()
    
    HistoricoAlteracao.objects.create(
        mapa=mapa,
        usuario=request.user,
        tipo_acao='DELETE',
        descricao=f"Removeu {nome} da viatura {vtr}."
    )
    return HttpResponse("")

@login_required
def get_viaturas_por_unidade(request):
    gb_nome = request.GET.get('categoria') # Ex: "15º GB"
    
    try:
        # Filtra viaturas da OPM selecionada (opmcb na planilha)
        query = Q()
        if gb_nome:
            # Busca exata ou parcial pelo nome normalizado
            query = Q(opmcb__icontains=gb_nome.strip())
        
        viats = Viatura.objects.filter(query).exclude(prefixo='TELEGRAFIA').order_by('sgb', 'garagem', 'prefixo')
        
        data = []
        
        # Injeta TELEGRAFIA (Sempre disponível)
        data.append({
            'VIATURAS': 'TELEGRAFIA',
            'SGB': 'INTERNO',
            'STATUS': 'OPERANDO',
            'PLACA': 'INTERNO',
            'Garagem': 'BASE'
        })
        
        for v in viats:
            data.append({
                'VIATURAS': v.prefixo,
                'SGB': v.sgb or 'N/D',
                'STATUS': v.status_base.nome if v.status_base else 'RESERVA',
                'PLACA': v.placa or 'S/ PLACA',
                'Garagem': v.garagem or '---'
            })
        
        return JsonResponse(data, safe=False)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def validar_mapa_final(request, mapa_id):
    mapa = get_object_or_404(MapaDiario, id=mapa_id)
    
    if request.user.role == 'COBOM' or mapa.unidade.nome == 'CBI-1':
        f_names = ['Oficial de Operações DEJEM', 'Chefe de Equipe', 'Supervisor Despacho', 'Supervisor 193', 'Supervisor 7º GB', 'Cabine 7º GB', 'Supervisor 19º GB', 'Cabine 19º GB', 'Supervisor 15º GB', 'Cabine 15º GB', 'Supervisor 16º GB', 'Cabine 16º GB', 'Apoio Cabine 7º, 19º e 15º GB', 'Apoio Cabine 16º GB', 'Enfermeiro de Triagem', 'Inclusor', 'Supervisor COE Autoban', 'Atendente 193']
        funcoes = Dictionary.objects.filter(tipo='FUNCAO_OPERACIONAL', nome__in=f_names)
        faltantes = []
        for f in funcoes:
            if not mapa.alocacoes_funcionarios.filter(funcao=f).exists():
                faltantes.append(f.nome)
        
        if faltantes:
            msg = "Falta preencher: " + ", ".join(faltantes)
            return HttpResponse(f'<script>showToast("{msg}", "error");</script>')
    else:
        # 1. Verifica se há viaturas sem guarnição (Excluindo a TELEGRAFIA da obrigatoriedade)
        vazias = [
            al.viatura.prefixo for al in mapa.alocacoes_viaturas.all() 
            if al.equipe.count() == 0 and al.viatura.prefixo != 'TELEGRAFIA'
        ]
        
        if vazias:
            return HttpResponse(f'<script>showToast("ERRO: Viaturas vazias: {", ".join(vazias)}", "error");</script>')
    
    # 2. Marca o mapa como finalizado
    mapa.finalizado = True
    mapa.save()
    
    HistoricoAlteracao.objects.create(
        mapa=mapa,
        usuario=request.user,
        tipo_acao='FINISH',
        descricao="Finalizou o mapa força do dia."
    )
    
    # 3. Retorna sucesso e recarrega para atualizar status visual
    return HttpResponse('''
        <script>
            showToast("MAPA FORÇA SALVO COM SUCESSO!", "success");
            setTimeout(() => { window.location.href = "/unidades/visao-cobom/"; }, 2000);
        </script>
    ''')

@login_required
def historico_view(request):
    data_str = request.GET.get('data')
    u_id = request.GET.get('unidade_id')
    sgb_id = request.GET.get('sgb_id')
    v_prefixo = request.GET.get('viatura_prefixo')
    dejem_only = request.GET.get('dejem') == 'true'
    view_type = request.GET.get('view', 'cards') # 'cards' ou 'table'
    export_format = request.GET.get('export') # 'csv' ou 'pdf'
    
    # Se não vier data, assume hoje
    if data_str:
        try:
            data_selecionada = timezone.datetime.strptime(data_str, '%Y-%m-%d').date()
        except ValueError:
            data_selecionada = timezone.now().date()
    else:
        data_selecionada = timezone.now().date()
        
    # Lógica de Filtro de Mapas
    filtros = Q(data=data_selecionada)
    
    if u_id:
        filtros &= Q(unidade_id=u_id)
    elif sgb_id:
        subunidades = Unidade.objects.filter(Q(id=sgb_id) | Q(parent_id=sgb_id)).values_list('id', flat=True)
        filtros &= Q(unidade_id__in=subunidades)
    
    if v_prefixo:
        filtros &= Q(alocacoes_viaturas__viatura__prefixo__icontains=v_prefixo)

    # Busca os mapas
    mapas = MapaDiario.objects.filter(filtros).distinct().select_related('unidade', 'criado_por').prefetch_related(
        'alocacoes_viaturas__viatura',
        'alocacoes_viaturas__equipe__funcionario__posto_graduacao',
        'alocacoes_viaturas__equipe__funcao',
        'historico__usuario'
    )

    # Lógica de Exportação CSV
    if export_format == 'csv':
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="mapa-forca-{data_selecionada}.csv"'
        writer = csv.writer(response)
        writer.writerow(['Unidade', 'Viatura', 'Posto/Grad', 'Nome', 'Função', 'DEJEM', 'Horário'])
        for m in mapas:
            for aloc in m.alocacoes_viaturas.all():
                for af in aloc.equipe.all():
                    if not dejem_only or af.dejem:
                        p_grad = af.funcionario.posto_graduacao.nome if af.funcionario.posto_graduacao else 'S/P'
                        f_nome = af.funcao.nome if af.funcao else 'S/F'
                        writer.writerow([
                            m.unidade.nome, aloc.viatura.prefixo, 
                            p_grad, af.funcionario.nome_guerra,
                            f_nome, 'SIM' if af.dejem else 'NÃO',
                            f"{af.inicio_dejem}-{af.termino_dejem}" if af.dejem else '-'
                        ])
        return response

    # Lógica de Exportação PDF (Renderização otimizada para impressão)
    if export_format == 'pdf':
        return render(request, 'escalas/export/mapa_pdf.html', {
            'mapas': mapas,
            'data_selecionada': data_selecionada,
            'dejem_only': dejem_only
        })
    
    # Contexto comum para a view
    sgbs = Unidade.objects.filter(Q(nome__icontains='SGB') | Q(tipo_unidade__codigo='BATALHAO')).order_by('nome')
    if sgb_id:
        unidades_lista = Unidade.objects.filter(parent_id=sgb_id).order_by('nome')
    else:
        unidades_lista = Unidade.objects.filter(tipo_unidade__codigo='POSTO').order_by('nome')

    context = {
        'mapas': mapas,
        'data_selecionada': data_selecionada,
        'sgbs': sgbs,
        'unidades_lista': unidades_lista,
        'sgb_selecionado': int(sgb_id) if sgb_id else None,
        'unidade_selecionada_id': int(u_id) if u_id else None,
        'v_prefixo': v_prefixo,
        'dejem_only': dejem_only,
        'view_type': view_type,
    }

    if request.headers.get('HX-Request'):
        template = 'escalas/partials/conteudo_historico_tabela.html' if view_type == 'table' else 'escalas/partials/conteudo_historico.html'
        return render(request, template, context)
    
    return render(request, 'escalas/historico.html', context)

# === API REST ===
class MapaDiarioViewSet(viewsets.ModelViewSet):
    queryset = MapaDiario.objects.prefetch_related('alocacoes_viaturas','alocacoes_funcionarios','unidade').all()
    serializer_class = MapaDiarioSerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['data', 'unidade']
    ordering = ['-data', 'unidade']
    def perform_create(self, serializer): serializer.save(criado_por=self.request.user)
    @action(detail=False, methods=['post'], url_path='clone')
    def clone(self, request):
        s = CloneMapaSerializer(data=request.data)
        if s.is_valid():
            try: orig = MapaDiario.objects.get(data=s.validated_data['data_origem'], unidade_id=s.validated_data['unidade_id'])
            except MapaDiario.DoesNotExist: return Response({"error": "Não encontrado"}, 404)
            novo = MapaDiario.objects.create(data=s.validated_data['data_destino'], unidade_id=s.validated_data['unidade_id'], criado_por=request.user)
            v_map = {av.id: AlocacaoViatura.objects.create(mapa=novo, viatura=av.viatura, status_no_dia=av.status_no_dia) for av in AlocacaoViatura.objects.filter(mapa=orig)}
            for af in AlocacaoFuncionario.objects.filter(mapa=orig): AlocacaoFuncionario.objects.create(mapa=novo, funcionario=af.funcionario, alocacao_viatura=v_map.get(af.alocacao_viatura_id), funcao=af.funcao)
            return Response(MapaDiarioSerializer(novo).data, 201)
        return Response(s.errors, 400)

class AlocacaoFuncionarioViewSet(viewsets.ModelViewSet):
    queryset = AlocacaoFuncionario.objects.all()
    serializer_class = AlocacaoFuncionarioSerializer

class AlocacaoViaturaViewSet(viewsets.ModelViewSet):
    queryset = AlocacaoViatura.objects.all()
    serializer_class = AlocacaoViaturaSerializer

@login_required
def update_mapa_cobom(request, mapa_id):
    mapa = get_object_or_404(MapaDiario, id=mapa_id)
    if 'prontidao' in request.POST:
        mapa.prontidao = request.POST.get('prontidao')
    if 'equipe' in request.POST:
        mapa.equipe = request.POST.get('equipe')
    if 'periodo' in request.POST:
        mapa.periodo = request.POST.get('periodo')
    mapa.save()
    # Retorna vazio para o HTMX não substituir nada (out-of-band updates se necessário, 
    # mas aqui queremos apenas trigger silent)
    return HttpResponse("")

