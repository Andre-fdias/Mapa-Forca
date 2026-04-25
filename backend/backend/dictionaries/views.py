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
