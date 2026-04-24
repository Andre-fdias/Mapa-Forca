from django.test import TestCase
from django.utils import timezone
from datetime import datetime, time, timedelta
from unittest.mock import patch
from .models import MapaDiario, AlocacaoViatura, AlocacaoFuncionario
from unidades.models import Unidade, Viatura
from efetivo.models import Funcionario
from dictionaries.models import Dictionary
from .views import get_data_operacional

class MapaForcaTestCase(TestCase):
    def setUp(self):
        # Setup de Dicionário
        self.tipo_posto = Dictionary.objects.create(tipo='TIPO_UNIDADE', codigo='POSTO', nome='Posto')
        self.funcao_cmd = Dictionary.objects.create(tipo='FUNCAO_OPERACIONAL', codigo='COMANDANTE', nome='Comandante')
        self.pg_sd = Dictionary.objects.create(tipo='POSTO_GRADUACAO', codigo='SD', nome='SD PM', ordem=10)

        # Setup de Unidade
        self.unidade = Unidade.objects.create(
            nome="Posto Teste", 
            tipo_unidade=self.tipo_posto
        )
        
        # Setup de Viatura
        self.viatura = Viatura.objects.create(
            prefixo="AB-01", 
            unidade_base=self.unidade
        )
        
        # Setup de Funcionário (RE deve seguir o formato 000000-0)
        self.funcionario = Funcionario.objects.create(
            re="123456-7", 
            nome_guerra="TESTE", 
            posto_graduacao=self.pg_sd,
            nome_completo="FUNCIONARIO DE TESTE"
        )

    def test_data_operacional_antes_do_reset(self):
        """Antes das 07:40, a data operacional deve ser o dia anterior."""
        with patch('django.utils.timezone.now') as mock_now:
            # Simulando dia 10/04/2026 às 06:00
            mock_now.return_value = timezone.make_aware(datetime(2026, 4, 10, 6, 0))
            data_op = get_data_operacional()
            self.assertEqual(data_op.day, 9)

    def test_data_operacional_apos_do_reset(self):
        """Após as 07:40, a data operacional deve ser o próprio dia."""
        with patch('django.utils.timezone.now') as mock_now:
            # Simulando dia 10/04/2026 às 08:00
            mock_now.return_value = timezone.make_aware(datetime(2026, 4, 10, 8, 0))
            data_op = get_data_operacional()
            self.assertEqual(data_op.day, 10)

    def test_unico_mapa_por_unidade_por_dia(self):
        """Deve impedir a criação de dois mapas para a mesma unidade no mesmo dia."""
        hoje = timezone.now().date()
        MapaDiario.objects.create(data=hoje, unidade=self.unidade)
        
        from django.db.utils import IntegrityError
        with self.assertRaises(IntegrityError):
            MapaDiario.objects.create(data=hoje, unidade=self.unidade)

    def test_funcionario_duplicado_no_mesmo_mapa(self):
        """Um funcionário não pode ser alocado duas vezes no mesmo mapa diário."""
        mapa = MapaDiario.objects.create(data=timezone.now().date(), unidade=self.unidade)
        
        # Primeira alocação (OK)
        AlocacaoFuncionario.objects.create(
            mapa=mapa, 
            funcionario=self.funcionario, 
            funcao=self.funcao_cmd
        )
        
        # Segunda alocação para o mesmo funcionário no mesmo mapa (Deve falhar)
        from django.db.utils import IntegrityError
        with self.assertRaises(IntegrityError):
            AlocacaoFuncionario.objects.create(
                mapa=mapa, 
                funcionario=self.funcionario, 
                funcao=self.funcao_cmd
            )

    def test_alocacao_viatura_duplicada(self):
        """Uma viatura não pode ser alocada duas vezes no mesmo mapa."""
        mapa = MapaDiario.objects.create(data=timezone.now().date(), unidade=self.unidade)
        
        AlocacaoViatura.objects.create(mapa=mapa, viatura=self.viatura)
        
        from django.db.utils import IntegrityError
        with self.assertRaises(IntegrityError):
            AlocacaoViatura.objects.create(mapa=mapa, viatura=self.viatura)

    def test_view_busca_funcionario_htmx(self):
        """A busca de funcionário deve retornar o partial correto para o HTMX."""
        from django.urls import reverse
        from django.contrib.auth import get_user_model
        
        # Cria um usuário para logar (Necessário @login_required)
        User = get_user_model()
        User.objects.create_user(email='test_view@gmail.com', password='password123', is_active=True)
        self.client.login(email='test_view@gmail.com', password='password123')
        
        url = reverse('buscar_funcionario_re')
        # Simulando uma busca pelo NOME do funcionário criado no setUp
        response = self.client.get(url, {'funcionario_re': 'TESTE'})
        
        self.assertEqual(response.status_code, 200)
        # O template correto na view é 'mapa_forca/partials/lista_busca_funcionarios.html'
        self.assertTemplateUsed(response, 'mapa_forca/partials/lista_busca_funcionarios.html')
        # Verifica se o nome do funcionário aparece no HTML retornado
        self.assertContains(response, self.funcionario.nome_guerra)
