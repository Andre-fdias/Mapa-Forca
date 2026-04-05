from rest_framework import serializers
from .models import Funcionario

class FuncionarioSerializer(serializers.ModelSerializer):
    identidade_militar = serializers.ReadOnlyField()

    class Meta:
        model = Funcionario
        fields = '__all__'
