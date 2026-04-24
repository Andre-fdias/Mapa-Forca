from django.db import models
from django.conf import settings

class Ticket(models.Model):
    STATUS_CHOICES = [
        ('ABERTO', 'Aberto'),
        ('EM_ANDAMENTO', 'Em Andamento'),
        ('RESOLVIDO', 'Resolvido'),
        ('FECHADO', 'Fechado'),
    ]

    ASSUNTO_CHOICES = [
        ('ERRO_LOGIN', 'Dificuldade de Acesso / Login'),
        ('CORRECAO_EFETIVO', 'Correção de Dados do Efetivo'),
        ('VIATURA_INDISPONIVEL', 'Viatura não aparece no seletor'),
        ('ERRO_MAPA_FORCA', 'Erro ao salvar/finalizar Mapa'),
        ('SOLICITAR_UNIDADE', 'Cadastro de nova Unidade/Posto'),
        ('DUVIDA_SISTEMA', 'Dúvida sobre funcionalidade'),
        ('SUGESTAO_MELHORIA', 'Sugestão de Melhoria'),
        ('OUTRO', 'Outro Assunto'),
    ]

    # Mapeamento Automático de Prioridade
    PRIORIDADE_MAP = {
        'ERRO_LOGIN': 'ALTA',
        'CORRECAO_EFETIVO': 'MEDIA',
        'VIATURA_INDISPONIVEL': 'ALTA',
        'ERRO_MAPA_FORCA': 'URGENTE',
        'SOLICITAR_UNIDADE': 'BAIXA',
        'DUVIDA_SISTEMA': 'BAIXA',
        'SUGESTAO_MELHORIA': 'BAIXA',
        'OUTRO': 'MEDIA',
    }

    PRIORIDADE_CHOICES = [
        ('BAIXA', 'Baixa'),
        ('MEDIA', 'Média'),
        ('ALTA', 'Alta'),
        ('URGENTE', 'Urgente'),
    ]

    requisitante = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='tickets_criados')
    protocolo = models.CharField(max_length=20, unique=True, blank=True, null=True)
    titulo = models.CharField(max_length=100, choices=ASSUNTO_CHOICES)
    descricao = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='ABERTO')
    prioridade = models.CharField(max_length=20, choices=PRIORIDADE_CHOICES, default='MEDIA')
    
    # Flags de Notificação
    lido_pelo_suporte = models.BooleanField(default=False)
    lido_pelo_requisitante = models.BooleanField(default=True) # Começa True pois o user que cria já viu
    
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-criado_em']
        verbose_name = 'Chamado'
        verbose_name_plural = 'Chamados'

    def save(self, *args, **kwargs):
        # Define a prioridade automaticamente com base no assunto
        if not self.id:
            self.prioridade = self.PRIORIDADE_MAP.get(self.titulo, 'MEDIA')
        
        super().save(*args, **kwargs)
        
        # Gera o protocolo após o primeiro save (para ter o ID)
        if not self.protocolo:
            from django.utils import timezone
            data_hoje = self.criado_em or timezone.now()
            data_str = data_hoje.strftime('%Y%m%d')
            self.protocolo = f"{data_str}-{self.id}"
            Ticket.objects.filter(id=self.id).update(protocolo=self.protocolo)

    def __str__(self):
        return f"{self.protocolo or self.id} - {self.get_titulo_display()}"

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
