from rest_framework import serializers
from .models import Unidade, Viatura

class UnidadeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Unidade
        fields = '__all__'

class ViaturaSerializer(serializers.ModelSerializer):
    unidade_base_nome = serializers.ReadOnlyField(source='unidade_base.nome')
    status_base_nome = serializers.ReadOnlyField(source='status_base.nome')
    status_base_codigo = serializers.ReadOnlyField(source='status_base.codigo')
    tipo_nome = serializers.ReadOnlyField(source='tipo.nome')

    class Meta:
        model = Viatura
        fields = '__all__'
