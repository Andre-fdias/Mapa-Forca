from rest_framework import serializers
from .models import Dictionary

class DictionarySerializer(serializers.ModelSerializer):
    class Meta:
        model = Dictionary
        fields = ['id', 'tipo', 'codigo', 'nome', 'descricao', 'ativo', 'ordem']
