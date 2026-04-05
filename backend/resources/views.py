from rest_framework import viewsets, filters
from django_filters.rest_framework import DjangoFilterBackend
from .models import Posto, Viatura
from .serializers import PostoSerializer, ViaturaSerializer

class PostoViewSet(viewsets.ModelViewSet):
    queryset = Posto.objects.filter(ativo=True)
    serializer_class = PostoSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ['nome']

class ViaturaViewSet(viewsets.ModelViewSet):
    queryset = Viatura.objects.all()
    serializer_class = ViaturaSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status_base', 'posto_base']
    search_fields = ['prefixo', 'placa']
    ordering = ['prefixo']
