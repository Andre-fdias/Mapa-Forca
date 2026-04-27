from django.test import TestCase, Client
from django.urls import reverse
from .models import Funcionario, Efetivo
from dictionaries.models import Dictionary
from accounts.models import User
from django.core.exceptions import ValidationError

class EfetivoModelsTestCase(TestCase):
    def setUp(self):
        self.tipo_pg = Dictionary.objects.create(tipo='POSTO_GRADUACAO', codigo='CB', nome='CB PM', ordem=10)
        self.tipo_pg_sgt = Dictionary.objects.create(tipo='POSTO_GRADUACAO', codigo='SGT', nome='1º SGT PM', ordem=8)

    def test_funcionario_creation_and_properties(self):
        """Testa criação de Funcionario, validação de RE e properties."""
        f = Funcionario.objects.create(
            re="123456-7",
            nome_completo="JOAO DA SILVA",
            nome_guerra="JOAO",
            posto_graduacao=self.tipo_pg,
            telefone="11988887777"
        )
        self.assertEqual(f.identidade_militar, "CB PM 123456-7 JOAO")
        self.assertEqual(f.nome_curto, "CB PM JOAO")
        self.assertEqual(str(f), "CB PM 123456-7 JOAO")

    def test_funcionario_re_validation(self):
        """Testa se a validação do RE (Regex) está funcionando."""
        f = Funcionario(re="12345-6", nome_completo="Erro") # RE faltando 1 dígito
        with self.assertRaises(ValidationError):
            f.full_clean()

    def test_efetivo_creation_all_fields(self):
        """Testa criação do modelo Efetivo (importado) com todos os campos."""
        e = Efetivo.objects.create(
            nome="PM TESTE",
            re="111222",
            dig="3",
            nome_do_pm="POLICIAL TESTE DE OLIVEIRA",
            nome_guerra="OLIVEIRA",
            nome_padrao="PM OLIVEIRA",
            unidade="15º GB",
            sgb="1º SGB",
            posto_secao="1ª EB",
            chave_posto="POSTO_X",
            email="oliveira@teste.com",
            mergulho="SIM",
            ovb="PESADO",
            telefone="11777776666"
        )
        self.assertEqual(e.re, "111222")
        self.assertEqual(e.ovb, "PESADO")

class EfetivoViewsTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin = User.objects.create_superuser(email='admin@efetivo.com', password='password')
        
        # Unidades para teste de permissão
        self.bt_dict = Dictionary.objects.create(tipo='TIPO_UNIDADE', codigo='BATALHAO', nome='Batalhão')
        self.bt15 = Unidade = type('Unidade', (object,), {'nome': '15º GB', 'tipo_unidade': self.bt_dict, 'parent': None, 'root_unit': None}) 
        # Como o model Unidade não foi importado aqui, vou usar o real se possível
        from unidades.models import Unidade
        self.bt15 = Unidade.objects.create(nome="15º GB", tipo_unidade=self.bt_dict)
        
        self.user_15gb = User.objects.create_user(
            email='user15@teste.com', 
            password='password',
            role='BATALHAO',
            unidade=self.bt15,
            status='approved'
        )

    def test_lista_efetivo_importado_access(self):
        """Testa acesso à lista de efetivo importado."""
        self.client.login(email='admin@efetivo.com', password='password')
        response = self.client.get(reverse('lista_efetivo_importado'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'efetivo/lista_importada.html')

    def test_lista_efetivo_filtering_by_permission(self):
        """Testa se o filtro de unidade é aplicado automaticamente para usuários de Batalhão."""
        Efetivo.objects.create(nome="PM 15", unidade="15º GB")
        Efetivo.objects.create(nome="PM 07", unidade="07º GB")
        
        self.client.login(email='user15@teste.com', password='password')
        response = self.client.get(reverse('lista_efetivo_importado'))
        
        self.assertContains(response, "PM 15")
        self.assertNotContains(response, "PM 07")

    def test_sync_efetivo_sheets_mock(self):
        """Testa o acionamento da sincronização do efetivo."""
        self.client.login(email='admin@efetivo.com', password='password')
        from unittest.mock import patch
        with patch('efetivo.views.call_command') as mock_call:
            response = self.client.get(reverse('sync_efetivo_sheets'))
            self.assertEqual(response.status_code, 200)
            mock_call.assert_called_with('sync_efetivo_sheets')
