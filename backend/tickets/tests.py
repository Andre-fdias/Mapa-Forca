from django.test import TestCase, Client
from django.urls import reverse
from accounts.models import User
from .models import Ticket, TicketMessage

class TicketsTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(email='user@tickets.com', password='password', status='approved')
        self.admin = User.objects.create_superuser(email='admin@tickets.com', password='password')

    def test_ticket_creation_logic(self):
        """Testa a criação do Ticket, protocolo automático e mapeamento de prioridade."""
        ticket = Ticket.objects.create(
            requisitante=self.user,
            titulo='ERRO_MAPA_FORCA',
            descricao='Não consigo finalizar o mapa'
        )
        self.assertEqual(ticket.prioridade, 'URGENTE') # Mapeado de ERRO_MAPA_FORCA
        self.assertIsNotNone(ticket.protocolo)
        self.assertTrue(ticket.protocolo.startswith(ticket.criado_em.strftime('%Y%m%d')))
        self.assertEqual(ticket.status, 'ABERTO')

    def test_ticket_message_creation(self):
        """Testa o envio de mensagens em um ticket."""
        ticket = Ticket.objects.create(
            requisitante=self.user,
            titulo='OUTRO',
            descricao='Teste'
        )
        msg = TicketMessage.objects.create(
            ticket=ticket,
            autor=self.admin,
            mensagem="Estamos verificando."
        )
        self.assertEqual(ticket.mensagens.count(), 1)
        self.assertEqual(msg.autor, self.admin)

    def test_view_lista_tickets_access(self):
        """Testa acesso à view de listagem de tickets."""
        self.client.login(email='user@tickets.com', password='password')
        url = reverse('tickets:ticket_list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'tickets/lista_tickets.html')

    def test_view_criar_ticket(self):
        """Testa a criação de um ticket via POST."""
        self.client.login(email='user@tickets.com', password='password')
        url = reverse('tickets:ticket_create')
        data = {
            'titulo': 'SUGESTAO_MELHORIA',
            'descricao': 'Sugiro um botão de exportar PDF'
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 302) # Redirect após sucesso
        self.assertEqual(Ticket.objects.filter(requisitante=self.user).count(), 1)
        
    def test_view_detalhe_ticket(self):
        """Testa a visualização detalhada do ticket."""
        ticket = Ticket.objects.create(requisitante=self.user, titulo='DUVIDA_SISTEMA', descricao='?')
        self.client.login(email='user@tickets.com', password='password')
        url = reverse('tickets:ticket_detail', args=[ticket.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, ticket.descricao)
