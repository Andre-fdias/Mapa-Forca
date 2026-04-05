from rest_framework import serializers
from .models import Posto, Viatura

class PostoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Posto
        fields = '__all__'

class ViaturaSerializer(serializers.ModelSerializer):
    posto_base_nome = serializers.ReadOnlyField(source='posto_base.nome')
    status_base_nome = serializers.ReadOnlyField(source='status_base.nome')
    status_base_codigo = serializers.ReadOnlyField(source='status_base.codigo')
    tipo_nome = serializers.ReadOnlyField(source='tipo.nome')

    class Meta:
        model = Viatura
        fields = '__all__'
