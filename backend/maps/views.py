from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from .models import MapaDiario, AlocacaoFuncionario, AlocacaoViatura
from .serializers import (
    MapaDiarioSerializer, AlocacaoFuncionarioSerializer, 
    AlocacaoViaturaSerializer, CloneMapaSerializer
)

class MapaDiarioViewSet(viewsets.ModelViewSet):
    queryset = MapaDiario.objects.prefetch_related(
        'alocacoes_funcionarios__funcionario__posto_graduacao',
        'alocacoes_funcionarios__posto',
        'alocacoes_viaturas__posto',
        'alocacoes_viaturas__viatura__tipo',
        'alocacoes_viaturas__viatura__status_base',
        'alocacoes_viaturas__status_no_dia'
    ).all()
    serializer_class = MapaDiarioSerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['data']
    ordering = ['-data']

    def perform_create(self, serializer):
        serializer.save(criado_por=self.request.user)

    @action(detail=False, methods=['post'], url_path='clone')
    def clone(self, request):
        serializer = CloneMapaSerializer(data=request.data)
        if serializer.is_valid():
            data_origem = serializer.validated_data['data_origem']
            data_destino = serializer.validated_data['data_destino']
            
            try:
                mapa_origem = MapaDiario.objects.get(data=data_origem)
            except MapaDiario.DoesNotExist:
                return Response({"error": "Mapa de origem não encontrado."}, status=status.HTTP_404_NOT_FOUND)

            # Criar novo mapa
            mapa_novo = MapaDiario.objects.create(
                data=data_destino,
                criado_por=request.user
            )

            # Clonar alocações de funcionários
            aloc_func = AlocacaoFuncionario.objects.filter(mapa=mapa_origem)
            for af in aloc_func:
                AlocacaoFuncionario.objects.create(
                    mapa=mapa_novo,
                    funcionario=af.funcionario,
                    posto=af.posto,
                    funcao=af.funcao
                )

            # Clonar alocações de viaturas
            aloc_viat = AlocacaoViatura.objects.filter(mapa=mapa_origem)
            for av in aloc_viat:
                AlocacaoViatura.objects.create(
                    mapa=mapa_novo,
                    viatura=av.viatura,
                    posto=av.posto,
                    status_no_dia=av.status_no_dia,
                    observacao=av.observacao
                )

            return Response(MapaDiarioSerializer(mapa_novo).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class AlocacaoFuncionarioViewSet(viewsets.ModelViewSet):
    queryset = AlocacaoFuncionario.objects.select_related('funcionario__posto_graduacao', 'posto', 'mapa').all()
    serializer_class = AlocacaoFuncionarioSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['mapa', 'posto']

class AlocacaoViaturaViewSet(viewsets.ModelViewSet):
    queryset = AlocacaoViatura.objects.select_related(
        'viatura__tipo', 'viatura__status_base', 'posto', 'status_no_dia', 'mapa'
    ).all()
    serializer_class = AlocacaoViaturaSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['mapa', 'posto']
