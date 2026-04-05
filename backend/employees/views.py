from rest_framework import viewsets, filters
from django_filters.rest_framework import DjangoFilterBackend
from .models import Funcionario
from .serializers import FuncionarioSerializer

class FuncionarioViewSet(viewsets.ModelViewSet):
    queryset = Funcionario.objects.all()
    serializer_class = FuncionarioSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['posto_grad']
    search_fields = ['nome_completo', 'nome_guerra', 're']
    ordering_fields = ['posto_grad', 'nome_completo', 're']
    ordering = ['posto_grad', 'nome_completo']
