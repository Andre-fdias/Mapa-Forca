from rest_framework import serializers
from .models import MapaDiario, AlocacaoFuncionario, AlocacaoViatura
from employees.serializers import FuncionarioSerializer
from resources.serializers import ViaturaSerializer, PostoSerializer

class AlocacaoFuncionarioSerializer(serializers.ModelSerializer):
    identidade_militar = serializers.CharField(source='funcionario.identidade_militar', read_only=True)
    posto_nome = serializers.CharField(source='posto.nome', read_only=True)

    class Meta:
        model = AlocacaoFuncionario
        fields = '__all__'

class AlocacaoViaturaSerializer(serializers.ModelSerializer):
    viatura_prefixo = serializers.CharField(source='viatura.prefixo', read_only=True)
    viatura_municipio = serializers.CharField(source='viatura.municipio', read_only=True)
    viatura_garagem = serializers.CharField(source='viatura.garagem', read_only=True)
    viatura_tipo_nome = serializers.CharField(source='viatura.tipo.nome', read_only=True)
    posto_nome = serializers.CharField(source='posto.nome', read_only=True)
    status_no_dia_nome = serializers.CharField(source='status_no_dia.nome', read_only=True)
    status_no_dia_codigo = serializers.CharField(source='status_no_dia.codigo', read_only=True)

    class Meta:
        model = AlocacaoViatura
        fields = '__all__'

class MapaDiarioSerializer(serializers.ModelSerializer):
    alocacoes_funcionarios = AlocacaoFuncionarioSerializer(many=True, read_only=True)
    alocacoes_viaturas = AlocacaoViaturaSerializer(many=True, read_only=True)
    criado_por_email = serializers.EmailField(source='criado_por.email', read_only=True)

    class Meta:
        model = MapaDiario
        fields = '__all__'

class CloneMapaSerializer(serializers.Serializer):
    data_origem = serializers.DateField()
    data_destino = serializers.DateField()

    def validate_data_destino(self, value):
        if MapaDiario.objects.filter(data=value).exists():
            raise serializers.ValidationError("Já existe um mapa para esta data.")
        return value
