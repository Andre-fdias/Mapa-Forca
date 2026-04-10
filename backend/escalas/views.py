from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, JsonResponse
from django.utils import timezone
from django.db.models import Q
from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend

from .models import MapaDiario, AlocacaoViatura, AlocacaoFuncionario
from unidades.models import Unidade, Viatura
from efetivo.models import Funcionario, Efetivo
from dictionaries.models import Dictionary
from .serializers import (
    MapaDiarioSerializer, AlocacaoFuncionarioSerializer, 
    AlocacaoViaturaSerializer, CloneMapaSerializer
)
import re

# === VIEWS HTMX ===

@login_required
def compor_mapa_view(request):
    hoje = timezone.now().date()
    u_id = request.GET.get('unidade_id')
    unidade = get_object_or_404(Unidade, id=u_id) if u_id else request.user.unidade
    if not unidade: return render(request, 'escalas/erro_permissao.html', {'mensagem': 'Unidade não encontrada.'})
    
    mapa, _ = MapaDiario.objects.get_or_create(data=hoje, unidade=unidade, defaults={'criado_por': request.user})
    
    # Filtra as unidades do 1º ao 5º SGB (excluindo 1 - EM)
    todas_unidades = Unidade.objects.filter(
        Q(parent__nome__icontains='1ºSGB') | 
        Q(parent__nome__icontains='2ºSGB') | 
        Q(parent__nome__icontains='3ºSGB') | 
        Q(parent__nome__icontains='4ºSGB') | 
        Q(parent__nome__icontains='5ºSGB')
    ).order_by('parent__nome', 'nome')

    return render(request, 'mapa_forca/compose.html', {
        'mapa': mapa, 
        'todas_unidades': todas_unidades,
        'unidade_selecionada': unidade, 
        'funcoes': Dictionary.objects.filter(tipo='FUNCAO_OPERACIONAL'),
    })

@login_required
def buscar_funcionario_re(request):
    q = request.GET.get('funcionario_re', '').strip()
    mapa_id = request.GET.get('mapa_id')
    if len(q) < 2: return HttpResponse('')
    
    # Limpa o Q para busca numérica se parecer um RE (contém números e possivelmente traço)
    q_numeric = re.sub(r'\D', '', q)
    
    mapa_atual = get_object_or_404(MapaDiario, id=mapa_id) if mapa_id else None
    data_escala = mapa_atual.data if mapa_atual else timezone.now().date()
    
    # 1. Busca no Efetivo Real (Sincronizado do Sheets)
    query_efetivo = Q(nome__icontains=q) | Q(nome_do_pm__icontains=q)
    if q_numeric:
        query_efetivo |= Q(re__icontains=q_numeric)
    
    efetivo_real = Efetivo.objects.filter(query_efetivo).order_by('nome')[:15]
    
    # 2. Busca no Funcionario (Local)
    query_func = Q(nome_completo__icontains=q) | Q(nome_guerra__icontains=q)
    if q_numeric:
        query_func |= Q(re__icontains=q_numeric)
        
    funcs_locais = Funcionario.objects.filter(query_func).select_related('posto_graduacao').order_by('nome_completo')[:5]
    
    # 3. Verifica disponibilidade para cada resultado
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
        'query': q
    })

@login_required
def adicionar_viatura_mapa(request, mapa_id):
    pref = request.POST.get('prefixo')
    mapa = get_object_or_404(MapaDiario, id=mapa_id)
    viat = get_object_or_404(Viatura, prefixo=pref)
    status_op = Dictionary.objects.filter(tipo='STATUS_VIATURA', codigo='OPERANDO').first()
    aloc, created = AlocacaoViatura.objects.get_or_create(mapa=mapa, viatura=viat, defaults={'status_no_dia': status_op})
    
    if created:
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
    # Para garantir que o usuário encontre qualquer viatura, listamos todas
    # e garantimos que o TELEGRAFISTA esteja na lista.
    viats = Viatura.objects.all().order_by('prefixo')
    
    opts = ['<option value="">Selecione a viatura...</option>']
    for v in viats: 
        opts.append(f'<option value="{v.prefixo}">{v.prefixo} — {v.tipo.nome if v.tipo else ""}</option>')
    return HttpResponse("".join(opts))


@login_required
def validar_mapa_final(request, mapa_id):
    mapa = get_object_or_404(MapaDiario, id=mapa_id)
    
    # 1. Verifica se há viaturas sem guarnição (Excluindo o Telegrafista da obrigatoriedade)
    vazias = [
        al.viatura.prefixo for al in mapa.alocacoes_viaturas.all() 
        if al.equipe.count() == 0 and al.viatura.prefixo != 'TELEGRAFISTA'
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
    
    # Se não vier data, assume hoje
    if data_str:
        data_selecionada = timezone.datetime.strptime(data_str, '%Y-%m-%d').date()
    else:
        data_selecionada = timezone.now().date()
        
    unidade = get_object_or_404(Unidade, id=u_id) if u_id else request.user.unidade
    
    # Busca o mapa daquela data/unidade
    mapa = MapaDiario.objects.filter(data=data_selecionada, unidade=unidade).first()
    
    # Se for uma requisição HTMX para trocar a data, retorna apenas o fragmento
    if request.headers.get('HX-Request'):
        template_name = 'escalas/partials/conteudo_historico.html'
    else:
        template_name = 'escalas/historico.html'

    # Busca as unidades para o seletor lateral (mesma lógica do compor)
    todas_unidades = Unidade.objects.filter(
        Q(parent__nome__icontains='1ºSGB') | 
        Q(parent__nome__icontains='2ºSGB') | 
        Q(parent__nome__icontains='3ºSGB') | 
        Q(parent__nome__icontains='4ºSGB') | 
        Q(parent__nome__icontains='5ºSGB')
    ).order_by('parent__nome', 'nome')

    return render(request, template_name, {
        'mapa': mapa,
        'data_selecionada': data_selecionada,
        'todas_unidades': todas_unidades,
        'unidade_selecionada': unidade,
    })

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
