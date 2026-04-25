from rest_framework import serializers
from .models import MapaDiario, AlocacaoFuncionario, AlocacaoViatura
from efetivo.serializers import FuncionarioSerializer
from unidades.serializers import ViaturaSerializer, UnidadeSerializer

class AlocacaoFuncionarioSerializer(serializers.ModelSerializer):
    identidade_militar = serializers.CharField(source='funcionario.identidade_militar', read_only=True)
    viatura_prefixo = serializers.CharField(source='alocacao_viatura.viatura.prefixo', read_only=True)
    funcao_nome = serializers.CharField(source='funcao.nome', read_only=True)

    class Meta:
        model = AlocacaoFuncionario
        fields = '__all__'

class AlocacaoViaturaSerializer(serializers.ModelSerializer):
    viatura_prefixo = serializers.CharField(source='viatura.prefixo', read_only=True)
    viatura_tipo_nome = serializers.CharField(source='viatura.tipo.nome', read_only=True)
    status_no_dia_nome = serializers.CharField(source='status_no_dia.nome', read_only=True)
    equipe = AlocacaoFuncionarioSerializer(many=True, read_only=True)

    class Meta:
        model = AlocacaoViatura
        fields = '__all__'

class MapaDiarioSerializer(serializers.ModelSerializer):
    alocacoes_viaturas = AlocacaoViaturaSerializer(many=True, read_only=True)
    alocacoes_funcionarios_avulsos = serializers.SerializerMethodField()
    unidade_nome = serializers.CharField(source='unidade.nome', read_only=True)
    criado_por_email = serializers.EmailField(source='criado_por.email', read_only=True)

    class Meta:
        model = MapaDiario
        fields = '__all__'

    def get_alocacoes_funcionarios_avulsos(self, obj):
        avulsos = obj.alocacoes_funcionarios.filter(alocacao_viatura__isnull=True)
        return AlocacaoFuncionarioSerializer(avulsos, many=True).data

class CloneMapaSerializer(serializers.Serializer):
    data_origem = serializers.DateField()
    data_destino = serializers.DateField()
    unidade_id = serializers.IntegerField()

    def validate(self, data):
        if MapaDiario.objects.filter(data=data['data_destino'], unidade_id=data['unidade_id']).exists():
            raise serializers.ValidationError("Já existe um mapa para esta data e unidade.")
        return data
