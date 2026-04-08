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

# === VIEWS HTMX ===

@login_required
def compor_mapa_view(request):
    hoje = timezone.now().date()
    u_id = request.GET.get('unidade_id')
    unidade = get_object_or_404(Unidade, id=u_id) if u_id else request.user.unidade
    if not unidade: return render(request, 'escalas/erro_permissao.html', {'mensagem': 'Unidade não encontrada.'})
    
    mapa, _ = MapaDiario.objects.get_or_create(data=hoje, unidade=unidade, defaults={'criado_por': request.user})
    v_ids = mapa.alocacoes_viaturas.values_list('viatura_id', flat=True)
    v_disp = Viatura.objects.filter(Q(unidade_base=unidade) | Q(unidade_base__isnull=True)).exclude(prefixo__in=v_ids).order_by('prefixo')

    return render(request, 'mapa_forca/compose.html', {
        'mapa': mapa, 'viaturas_disponiveis': v_disp, 'todas_unidades': Unidade.objects.all().order_by('nome'),
        'unidade_selecionada': unidade, 'funcoes': Dictionary.objects.filter(tipo='FUNCAO_OPERACIONAL'),
    })

@login_required
def buscar_funcionario_re(request):
    q = request.GET.get('funcionario_re', '').strip()
    if len(q) < 2: return HttpResponse('')
    
    funcs = Funcionario.objects.filter(Q(re__icontains=q) | Q(nome_completo__icontains=q) | Q(nome_guerra__icontains=q)).select_related('posto_graduacao').order_by('posto_graduacao__ordem', 'nome_completo')[:10]
    extra = Efetivo.objects.filter(nome__icontains=q).exclude(nome__in=[f.nome_completo for f in funcs]).order_by('nome')[:5] if len(funcs) < 5 else []
    
    return render(request, 'mapa_forca/partials/lista_busca_funcionarios.html', {'funcionarios': funcs, 'efetivo_extra': extra})

@login_required
def adicionar_viatura_mapa(request, mapa_id):
    pref = request.POST.get('prefixo')
    mapa = get_object_or_404(MapaDiario, id=mapa_id)
    viat = get_object_or_404(Viatura, prefixo=pref)
    status_op = Dictionary.objects.filter(tipo='STATUS_VIATURA', codigo='OPERANDO').first()
    aloc, _ = AlocacaoViatura.objects.get_or_create(mapa=mapa, viatura=viat, defaults={'status_no_dia': status_op})
    return render(request, 'mapa_forca/partials/card_viatura_alocada.html', {'alocacao': aloc, 'funcoes': Dictionary.objects.filter(tipo='FUNCAO_OPERACIONAL')})

@login_required
def alocar_funcionario_viatura(request, alocacao_viatura_id):
    re_in = request.POST.get('funcionario_re', '').strip()
    nome_ex = request.POST.get('nome_extra', '').strip()
    f_id = request.POST.get('funcao_id')
    aloc_v = get_object_or_404(AlocacaoViatura, id=alocacao_viatura_id)
    funcao = get_object_or_404(Dictionary, id=f_id)
    
    if aloc_v.equipe.count() >= 15: return HttpResponse('<script>showToast("Limite de 15 atingido!", "error");</script>')

    # Tenta achar o militar
    militar = Funcionario.objects.filter(re=re_in).first()
    if not militar: militar = Funcionario.objects.filter(nome_completo__iexact=nome_ex if nome_ex else re_in).first()

    # Se for novo (Sheets), cadastra
    if not militar and (nome_ex or len(re_in) > 5):
        nome = (nome_ex if nome_ex else re_in).upper()
        import hashlib
        tre = f"T-{hashlib.md5(nome.encode()).hexdigest()[:6]}"
        
        # Tenta extrair posto do nome (Ex: CB PM ANDRE -> Posto: CB)
        p_sigla = "SD"
        for s in ['CB', 'SGT', 'TEN', 'CAP', 'MAJ', 'SUB']:
            if s in nome: p_sigla = s; break
        
        posto = Dictionary.objects.filter(tipo='POSTO_GRADUACAO', codigo=p_sigla).first()
        # Nome de guerra é a última parte do nome
        nguerra = nome.split()[-1]
        
        militar = Funcionario.objects.create(re=tre, nome_completo=nome, nome_guerra=nguerra, posto_graduacao=posto)

    if militar:
        AlocacaoFuncionario.objects.filter(mapa=aloc_v.mapa, funcionario=militar).delete()
        af = AlocacaoFuncionario.objects.create(mapa=aloc_v.mapa, alocacao_viatura=aloc_v, funcionario=militar, funcao=funcao)
        return render(request, 'mapa_forca/partials/linha_funcionario_viatura.html', {'aloc_func': af})
    
    return HttpResponse('<script>showToast("Militar não encontrado!", "error");</script>')

@login_required
def remover_viatura_mapa(request, alocacao_id):
    get_object_or_404(AlocacaoViatura, id=alocacao_id).delete()
    return HttpResponse("")

@login_required
def remover_funcionario_viatura(request, aloc_func_id):
    get_object_or_404(AlocacaoFuncionario, id=aloc_func_id).delete()
    return HttpResponse("")

@login_required
def get_viaturas_por_unidade(request):
    u_id = request.GET.get('unidade_id')
    if not u_id: return HttpResponse('<option>Selecione o posto...</option>')
    viats = Viatura.objects.filter(unidade_base_id=u_id).order_by('prefixo')
    opts = ['<option value="">Selecione a viatura...</option>']
    for v in viats: opts.append(f'<option value="{v.prefixo}">{v.prefixo} — {v.tipo.nome if v.tipo else ""}</option>')
    return HttpResponse("".join(opts))

@login_required
def validar_mapa_final(request, mapa_id):
    mapa = get_object_or_404(MapaDiario, id=mapa_id)
    vazias = [al.viatura.prefixo for al in mapa.alocacoes_viaturas.all() if al.equipe.count() == 0]
    if vazias: return HttpResponse(f'<script>showToast("ERRO: Viaturas vazias: {", ".join(vazias)}", "error");</script>')
    return HttpResponse('<script>showToast("MAPA FORÇA SALVO COM SUCESSO!", "success");</script>')

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
