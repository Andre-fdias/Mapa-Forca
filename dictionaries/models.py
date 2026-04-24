from django.db import models

class Dictionary(models.Model):
    tipo = models.CharField(max_length=100)
    codigo = models.CharField(max_length=100)
    nome = models.CharField(max_length=255)
    descricao = models.TextField(blank=True, null=True)
    ativo = models.BooleanField(default=True)
    ordem = models.IntegerField(default=0)

    class Meta:
        verbose_name = 'Dicionário'
        verbose_name_plural = 'Dicionários'
        unique_together = ('tipo', 'codigo')
        ordering = ['tipo', 'ordem', 'nome']

    def __str__(self):
        return f"[{self.tipo}] {self.nome} ({self.codigo})"
