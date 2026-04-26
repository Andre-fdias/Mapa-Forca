from django.shortcuts import render
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from rest_framework import viewsets
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from .models import Dictionary
from .serializers import DictionarySerializer

class DictionaryViewSet(viewsets.ModelViewSet):
    queryset = Dictionary.objects.all()
    serializer_class = DictionarySerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['tipo', 'codigo', 'ativo']
    search_fields = ['nome', 'codigo', 'descricao']
    ordering_fields = ['ordem', 'nome', 'codigo']
    ordering = ['tipo', 'ordem', 'nome']

@login_required
def abrir_modal_funcao(request):
    tipo_contexto = request.GET.get('contexto', 'GB')
    return render(request, 'dictionaries/partials/modal_nova_funcao.html', {
        'tipo_contexto': tipo_contexto
    })

@login_required
def salvar_nova_funcao(request):
    if request.method == 'POST':
        nome = request.POST.get('nome', '').strip().upper()
        contexto = request.POST.get('contexto', 'GB')
        tipo_especifico = f'FUNCAO_OPERACIONAL_{contexto}'
        codigo = nome.replace(' ', '_')
        
        if nome:
            Dictionary.objects.get_or_create(
                tipo=tipo_especifico,
                codigo=codigo,
                defaults={'nome': nome, 'ordem': 99}
            )
            
            # Retorna o select atualizado respeitando as regras de filtragem rigorosa
            if contexto == 'COBOM':
                funcoes = Dictionary.objects.filter(tipo='FUNCAO_OPERACIONAL_COBOM', ativo=True).order_by('ordem', 'nome')
            else:
                funcoes = Dictionary.objects.filter(
                    Q(tipo='FUNCAO_OPERACIONAL') | Q(tipo='FUNCAO_OPERACIONAL_GB'),
                    ativo=True
                ).order_by('ordem', 'nome')
            
            return render(request, 'dictionaries/partials/select_funcoes_fragment.html', {
                'funcoes': funcoes
            })
            
    return HttpResponse('Erro ao salvar', status=400)
