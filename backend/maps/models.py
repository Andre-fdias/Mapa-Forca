from django.db import models
from django.conf import settings
from employees.models import Funcionario
from resources.models import Posto, Viatura
from dictionaries.models import Dictionary

class MapaDiario(models.Model):
    data = models.DateField(unique=True)
    criado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Mapa de Força - {self.data}"

    class Meta:
        verbose_name = 'Mapa Diário'
        verbose_name_plural = 'Mapas Diários'
        ordering = ['-data']

class AlocacaoFuncionario(models.Model):
    mapa = models.ForeignKey(MapaDiario, on_delete=models.CASCADE, related_name='alocacoes_funcionarios')
    funcionario = models.ForeignKey(Funcionario, on_delete=models.CASCADE)
    posto = models.ForeignKey(Posto, on_delete=models.CASCADE)
    funcao = models.CharField(max_length=100, blank=True)

    def __str__(self):
        return f"{self.funcionario.nome_guerra} em {self.posto.nome}"

    class Meta:
        verbose_name = 'Alocação de Funcionário'
        verbose_name_plural = 'Alocações de Funcionários'
        unique_together = ('mapa', 'funcionario')

class AlocacaoViatura(models.Model):
    mapa = models.ForeignKey(MapaDiario, on_delete=models.CASCADE, related_name='alocacoes_viaturas')
    viatura = models.ForeignKey(Viatura, on_delete=models.CASCADE)
    posto = models.ForeignKey(Posto, on_delete=models.CASCADE)
    status_no_dia = models.ForeignKey(Dictionary, on_delete=models.SET_NULL, null=True, limit_choices_to={'tipo': 'STATUS_VIATURA'})
    observacao = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return f"{self.viatura.prefixo} em {self.posto.nome}"

    class Meta:
        verbose_name = 'Alocação de Viatura'
        verbose_name_plural = 'Alocações de Viaturas'
        unique_together = ('mapa', 'viatura')
