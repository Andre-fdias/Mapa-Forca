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

@login_required
def compor_mapa_view(request):
    hoje = get_data_operacional()
    u_id = request.GET.get('unidade_id')
    categoria = request.GET.get('categoria')
    mapa = None
    
    # 1. Busca as Unidades (Grupamentos) disponíveis na planilha
    lista_opm = list(Posto.objects.exclude(unidade__isnull=True).exclude(unidade='').values_list('unidade', flat=True).distinct().order_by('unidade'))
    
    # 2. Define a categoria padrão se nenhuma for selecionada
    if not categoria:
        if lista_opm:
            categoria = lista_opm[0]
        else:
            categoria = '15º GB'

    # 3. Gerencia a seleção do Posto específico
    unidade_obj = None
    if u_id:
        unidade_obj = get_object_or_404(Unidade, id=u_id)
    elif request.user.unidade and request.user.unidade.tipo_unidade and request.user.unidade.tipo_unidade.codigo == 'POSTO':
        unidade_obj = request.user.unidade

    if unidade_obj:
        mapa, created = MapaDiario.objects.get_or_create(data=hoje, unidade=unidade_obj, defaults={'criado_por': request.user})
        if created:
            HistoricoAlteracao.objects.create(
                mapa=mapa, usuario=request.user, tipo_acao='CREATE',
                descricao="Iniciou a composição do mapa força do dia."
            )

    # 4. FILTRAGEM DINÂMICA: Busca no model Unidade os postos que pertencem à Categoria (Grupamento)
    # Pegamos os códigos de seção que a planilha diz pertencer a este GB
    codigos_secao = list(Posto.objects.filter(unidade=categoria).values_list('cod_secao', flat=True))
    
    # Buscamos as Unidades que batem com esses códigos ou nomes específicos daquela categoria
    todas_unidades = Unidade.objects.filter(
        Q(codigo_secao__in=codigos_secao) | 
        Q(parent__nome__icontains=categoria.replace('º', '').replace('°', '').strip())
    ).distinct().order_by('nome')

    context = {
        'mapa': mapa, 
        'todas_unidades': todas_unidades,
        'unidade_selecionada': unidade_obj, 
        'categorias_opm': lista_opm,
        'categoria_selecionada': categoria,
        'funcoes': Dictionary.objects.filter(tipo='FUNCAO_OPERACIONAL'),
        'base_template': 'base/partial.html' if request.headers.get('HX-Request') else 'base/base.html'
    }

    if request.headers.get('HX-Request') and not u_id:
        return render(request, 'mapa_forca/partials/select_postos.html', context)

    return render(request, 'mapa_forca/compose.html', context)

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
    
    # Aplica filtro de unidade se a categoria for informada
    if categoria:
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
    # ... (restante do código anterior de busca de militar) ...
    re_in = request.POST.get('funcionario_re', '').strip()
    nome_ex = request.POST.get('nome_extra', '').strip()
    efetivo_id = request.POST.get('efetivo_id')
    f_id = request.POST.get('funcao_id')
    dejem_val = request.POST.get('dejem') == 'true'
    inicio_dejem = request.POST.get('inicio_dejem')
    termino_dejem = request.POST.get('termino_dejem')
    
    aloc_v = get_object_or_404(AlocacaoViatura, id=alocacao_viatura_id)
    funcao = get_object_or_404(Dictionary, id=f_id)
    
    if aloc_v.equipe.count() >= 15: return HttpResponse('<script>showToast("Limite de 15 atingido!", "error");</script>')

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

        # Mapeamento robusto de siglas para códigos do dicionário
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
        ja_alocado = AlocacaoFuncionario.objects.filter(
            mapa__data=aloc_v.mapa.data, 
            funcionario=militar
        ).exclude(alocacao_viatura=aloc_v).first()
        
        if ja_alocado:
            return HttpResponse(f'<script>showToast("Militar já escalado hoje!", "error");</script>')

        AlocacaoFuncionario.objects.filter(mapa=aloc_v.mapa, funcionario=militar).delete()
        af = AlocacaoFuncionario.objects.create(
            mapa=aloc_v.mapa, 
            alocacao_viatura=aloc_v, 
            funcionario=militar, 
            funcao=funcao,
            dejem=(dejem_val == True),
            inicio_dejem=inicio_dejem if dejem_val and inicio_dejem else None,
            termino_dejem=termino_dejem if dejem_val and termino_dejem else None
        )
        
        HistoricoAlteracao.objects.create(
            mapa=aloc_v.mapa,
            usuario=request.user,
            tipo_acao='UPDATE',
            descricao=f"Alocou {militar.nome_guerra} na viatura {aloc_v.viatura.prefixo} como {funcao.nome}."
        )
        
        return render(request, 'mapa_forca/partials/linha_funcionario_viatura.html', {'aloc_func': af})
    
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
            setTimeout(() => { window.location.href = "/"; }, 2000);
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
