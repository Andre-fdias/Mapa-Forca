from django.db import models
from django.conf import settings

class Ticket(models.Model):
    STATUS_CHOICES = [
        ('ABERTO', 'Aberto'),
        ('EM_ANDAMENTO', 'Em Andamento'),
        ('RESOLVIDO', 'Resolvido'),
        ('FECHADO', 'Fechado'),
    ]

    PRIORIDADE_CHOICES = [
        ('BAIXA', 'Baixa'),
        ('MEDIA', 'Média'),
        ('ALTA', 'Alta'),
        ('URGENTE', 'Urgente'),
    ]

    CATEGORIA_CHOICES = [
        ('ERRO_SISTEMA', 'Erro de Sistema'),
        ('CORRECAO_DADOS', 'Correção de Dados'),
        ('DUVIDA', 'Dúvida'),
        ('SUGESTAO', 'Sugestão'),
        ('OUTRO', 'Outro'),
    ]

    requisitante = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='tickets_criados')
    titulo = models.CharField(max_length=255)
    descricao = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='ABERTO')
    prioridade = models.CharField(max_length=20, choices=PRIORIDADE_CHOICES, default='MEDIA')
    categoria = models.CharField(max_length=20, choices=CATEGORIA_CHOICES, default='OUTRO')
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-criado_em']
        verbose_name = 'Chamado'
        verbose_name_plural = 'Chamados'

    def __str__(self):
        return f"#{self.id} - {self.titulo} ({self.get_status_display()})"

class TicketMessage(models.Model):
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name='mensagens')
    autor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    mensagem = models.TextField()
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['criado_em']
        verbose_name = 'Mensagem do Chamado'
        verbose_name_plural = 'Mensagens do Chamado'

    def __str__(self):
        return f"Msg em #{self.ticket.id} por {self.autor.email}"
