from django.db import models
from django.conf import settings
from efetivo.models import Funcionario
from unidades.models import Unidade, Viatura
from dictionaries.models import Dictionary

class MapaDiario(models.Model):
    """
    Representa a escala de um dia específico para uma unidade específica.
    """
    data = models.DateField()
    unidade = models.ForeignKey(
        Unidade, 
        on_delete=models.CASCADE, 
        related_name='mapas_diarios'
    )
    
    criado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True
    )
    criado_em = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Mapa {self.unidade.nome} - {self.data}"

    class Meta:
        verbose_name = 'Mapa Diário'
        verbose_name_plural = 'Mapas Diários'
        unique_together = ('data', 'unidade')
        ordering = ['-data', 'unidade']

class AlocacaoViatura(models.Model):
    """
    Registra quais viaturas estão escaladas em um determinado mapa (dia/unidade).
    """
    mapa = models.ForeignKey(
        MapaDiario, 
        on_delete=models.CASCADE, 
        related_name='alocacoes_viaturas'
    )
    viatura = models.ForeignKey(Viatura, on_delete=models.CASCADE)
    
    status_no_dia = models.ForeignKey(
        Dictionary, 
        on_delete=models.SET_NULL, 
        null=True, 
        limit_choices_to={'tipo': 'STATUS_VIATURA'}
    )
    observacao = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return f"{self.viatura.prefixo} em {self.mapa}"

    class Meta:
        verbose_name = 'Alocação de Viatura'
        verbose_name_plural = 'Alocações de Viaturas'
        unique_together = ('mapa', 'viatura')

class AlocacaoFuncionario(models.Model):
    """
    Aloca um funcionário a uma viatura dentro de um mapa, ou o mantém avulso no mapa.
    """
    mapa = models.ForeignKey(
        MapaDiario, 
        on_delete=models.CASCADE, 
        related_name='alocacoes_funcionarios'
    )
    alocacao_viatura = models.ForeignKey(
        AlocacaoViatura, 
        on_delete=models.CASCADE, 
        related_name='equipe',
        null=True,
        blank=True,
        help_text='Viatura na qual o funcionário está alocado. Se vazio, está avulso na unidade.'
    )
    funcionario = models.ForeignKey(Funcionario, on_delete=models.CASCADE)
    
    funcao = models.ForeignKey(
        Dictionary, 
        on_delete=models.SET_NULL, 
        null=True, 
        limit_choices_to={'tipo': 'FUNCAO_OPERACIONAL'},
        help_text='Comandante, Motorista, Auxiliar, Supervisor, etc.'
    )

    def __str__(self):
        viatura_str = self.alocacao_viatura.viatura.prefixo if self.alocacao_viatura else 'Avulso'
        return f"{self.funcionario.nome_guerra} ({viatura_str})"

    class Meta:
        verbose_name = 'Alocação de Funcionário'
        verbose_name_plural = 'Alocações de Funcionários'
        unique_together = ('mapa', 'funcionario')
