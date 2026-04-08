from django.db import models
from django.core.validators import RegexValidator
from dictionaries.models import Dictionary

class Funcionario(models.Model):
    re_validator = RegexValidator(
        regex=r'^\d{6}-\d{1}$',
        message='O RE deve estar no formato 000000-0'
    )

    re = models.CharField(
        max_length=8, 
        primary_key=True, 
        validators=[re_validator],
        help_text='Formato: 000000-0'
    )
    nome_completo = models.CharField(max_length=255)
    nome_guerra = models.CharField(max_length=100)
    posto_graduacao = models.ForeignKey(Dictionary, on_delete=models.SET_NULL, null=True, limit_choices_to={'tipo': 'POSTO_GRADUACAO'})

    @property
    def identidade_militar(self):
        pg = self.posto_graduacao.nome if self.posto_graduacao else 'S/P'
        return f"{pg} {self.re} {self.nome_guerra}"

    def __str__(self):
        return self.identidade_militar

    class Meta:
        verbose_name = 'Funcionário'
        verbose_name_plural = 'Funcionários'
        ordering = ['posto_graduacao__ordem', 'nome_completo']

class Efetivo(models.Model):
    nome = models.CharField(max_length=255, unique=True)
    re = models.CharField(max_length=50, null=True, blank=True)
    nome_do_pm = models.CharField(max_length=255, null=True, blank=True)
    sgb = models.CharField(max_length=100, null=True, blank=True)
    posto_secao = models.CharField(max_length=100, null=True, blank=True)
    mergulho = models.CharField(max_length=100, null=True, blank=True)
    ovb = models.CharField(max_length=100, null=True, blank=True)
    
    fonte = models.CharField(max_length=100, default='Google Sheets')
    data_importacao = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.nome

    class Meta:
        verbose_name = 'Efetivo'
        verbose_name_plural = 'Efetivos'
        ordering = ['nome']
