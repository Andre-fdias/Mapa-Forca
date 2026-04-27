from django.test import TestCase, Client
from django.urls import reverse
from .models import Unidade, Viatura, Municipio, Posto
from dictionaries.models import Dictionary
from accounts.models import User
from django.core.exceptions import ValidationError

class UnidadesModelsTestCase(TestCase):
    def setUp(self):
        # Criar dicionários necessários para as FKs dos modelos
        self.tipo_unidade_bt = Dictionary.objects.create(tipo='TIPO_UNIDADE', codigo='BATALHAO', nome='Batalhão')
        self.tipo_unidade_posto = Dictionary.objects.create(tipo='TIPO_UNIDADE', codigo='POSTO', nome='Posto Operacional')
        
        self.tipo_posto_eb = Dictionary.objects.create(tipo='TIPO_POSTO', codigo='EB', nome='Estação de Bombeiros')
        self.tipo_posto_adm = Dictionary.objects.create(tipo='TIPO_POSTO', codigo='ADM', nome='Administrativo')
        
        self.tipo_vtr_as = Dictionary.objects.create(tipo='TIPO_VIATURA', codigo='AS', nome='Auto Salvamento')
        self.status_vtr_op = Dictionary.objects.create(tipo='STATUS_VIATURA', codigo='OPERANDO', nome='Operando')

    def test_unidade_creation_and_clean_logic(self):
        """Testa criação de Unidade e a lógica automática de tipo_servico no clean()."""
        # 1. Criação simples
        bt = Unidade.objects.create(
            nome="15º GB - TESTE",
            tipo_unidade=self.tipo_unidade_bt,
            codigo_secao="99999"
        )
        self.assertEqual(str(bt), "15º GB - TESTE")
        self.assertIsNone(bt.parent)

        # 2. Teste de hierarquia e root_unit
        posto = Unidade.objects.create(
            nome="1ª EB - TESTE",
            parent=bt,
            tipo_unidade=self.tipo_unidade_posto,
            descricao="UNIDADE EB", # Deve disparar a lógica do clean() para tipo_servico=EB
            codigo_secao="88888"
        )
        self.assertEqual(posto.root_unit, bt)
        self.assertEqual(posto.tipo_servico, self.tipo_posto_eb)

        # 3. Teste de alteração de descrição disparando clean()
        posto.descricao = "SETOR ADM"
        posto.tipo_servico = None # Reseta para testar re-atribuição
        posto.save()
        self.assertEqual(posto.tipo_servico, self.tipo_posto_adm)

    def test_viatura_creation_and_sanitization(self):
        """Testa criação de Viatura, sanitização de campos e lógicas automáticas."""
        bt = Unidade.objects.create(nome="VTR_UNIT", tipo_unidade=self.tipo_unidade_bt, codigo_secao="V1")
        
        vtr = Viatura.objects.create(
            prefixo="AS-15101",
            placa="ABC1D23",
            municipio="SãO PaULo", # Deve normalizar para SAO PAULO
            opmcb="15º GB",
            sgb="1sgb", # Deve normalizar para 1º SGB
            unidade_base=bt,
            vol_agua="4000L",
            combustivel="Diesel"
        )
        
        self.assertEqual(vtr.municipio, "SAO PAULO")
        self.assertEqual(vtr.sgb, "1º SGB")
        self.assertEqual(vtr.status_base, self.status_vtr_op) # Default via clean()
        self.assertEqual(vtr.tipo, self.tipo_vtr_as) # Inferido do prefixo via clean()
        self.assertEqual(str(vtr), "AS-15101")

    def test_viatura_clean_edge_cases(self):
        """Testa casos de borda no clean() da Viatura (prefixos desconhecidos, campos vazios)."""
        # 1. Prefixo que não existe no dicionário TIPO_VIATURA
        vtr = Viatura.objects.create(prefixo="UNK-999")
        self.assertIsNone(vtr.tipo) # Não deve explodir, apenas ficar None

        # 2. Município e SGB vazios
        vtr2 = Viatura.objects.create(prefixo="AS-02", municipio="", sgb="")
        self.assertEqual(vtr2.municipio, "")
        self.assertEqual(vtr2.sgb, "")

    def test_unidade_clean_missing_dictionary(self):
        """Testa se o clean da Unidade não falha se o código do dicionário não existir."""
        u = Unidade.objects.create(nome="U-TESTE", descricao="CODIGO_INEXISTENTE")
        # Não deve atribuir tipo_servico e não deve dar erro
        self.assertIsNone(u.tipo_servico)

    def test_municipio_all_fields(self):
        """Testa a gravação de todos os campos do modelo Município."""
        mun = Municipio.objects.create(
            id_cidade="123",
            nome="CIDADE TESTE",
            tipo_cidade="Sede",
            area_km2=100.50,
            populacao=50000,
            hab_km2=497.51,
            email="teste@cidade.com",
            bandeira="http://link.com/img.png",
            codigo="999",
            fonte="Manual"
        )
        refresh_mun = Municipio.objects.get(id=mun.id)
        self.assertEqual(refresh_mun.area_km2, 100.50)
        self.assertEqual(refresh_mun.populacao, 50000)

    def test_posto_all_fields(self):
        """Testa a gravação de todos os campos do modelo Posto."""
        posto = Posto.objects.create(
            nome="Posto Completo",
            unidade="15º GB",
            sgb="1º SGB",
            cod_secao="SEC01",
            cidade_posto="TESTE",
            operacional_adm="OPERACIONAL",
            endereco_quarte="Rua X, 10",
            telefone="1199999999",
            fonte="Manual"
        )
        self.assertEqual(posto.cod_secao, "SEC01")
        self.assertEqual(posto.operacional_adm, "OPERACIONAL")

class UnidadesViewsTestCase(TestCase):
    def setUp(self):
        # Setup similar ao Models mas com Usuário e Client
        self.client = Client()
        self.tipo_bt = Dictionary.objects.create(tipo='TIPO_UNIDADE', codigo='BATALHAO', nome='Batalhão')
        self.bt = Unidade.objects.create(nome="15º GB", tipo_unidade=self.tipo_bt, codigo_secao="GB15")
        
        # Usuário Admin
        self.admin_user = User.objects.create_superuser(
            email='admin@teste.com', 
            password='password123',
            role='ADMIN'
        )
        # Usuário de Posto com unidade vinculada
        self.posto_unit = Unidade.objects.create(nome="1ª EB", parent=self.bt, codigo_secao="EB1")
        self.posto_user = User.objects.create_user(
            email='posto@teste.com',
            password='password123',
            role='POSTO',
            unidade=self.posto_unit,
            status='approved'
        )

    def test_dashboard_batalhao_access_restricted(self):
        """Testa se usuário de POSTO é redirecionado para dashboard_cobom (sua visão permitida)."""
        self.client.login(email='posto@teste.com', password='password123')
        # Tenta acessar dashboard_batalhao especificamente
        response = self.client.get(reverse('dashboard_batalhao'))
        # A view dashboard_batalhao redireciona para cobom se não tiver ?view=batalhao
        # ou se o usuário for redirecionado internamente
        self.assertEqual(response.status_code, 200)
        # Verifica se renderizou o template do cobom (que é a visão tática padrão)
        self.assertTemplateUsed(response, 'dashboard/cobom.html')

    def test_cadastro_viaturas_permission_filtering(self):
        """Testa se a listagem de viaturas filtra por unidade do usuário não-admin."""
        # Viatura do 15º GB
        Viatura.objects.create(prefixo="AS-15", opmcb="15º GB")
        # Viatura de outro GB
        Viatura.objects.create(prefixo="AS-07", opmcb="07º GB")
        
        # Usuário do 15º GB (vinculado via 1ª EB que é filha do 15º GB no setUp)
        self.client.login(email='posto@teste.com', password='password123')
        
        response = self.client.get(reverse('cadastro_viaturas'))
        self.assertContains(response, "AS-15")
        self.assertNotContains(response, "AS-07")

    def test_sync_sheets_access(self):
        """Testa acesso ao endpoint de sincronização."""
        self.client.login(email='admin@teste.com', password='password123')
        # Patch no local onde a view consome o call_command
        from unittest.mock import patch
        with patch('unidades.views.call_command') as mock_call:
            response = self.client.get(reverse('sync_viaturas_sheets'))
            self.assertEqual(response.status_code, 200)
            mock_call.assert_called_with('sync_viaturas_sheets')

    def test_cadastro_viaturas_view_filters(self):
        """Testa a view de listagem de viaturas e seus filtros."""
        Viatura.objects.create(prefixo="AS-01", opmcb="15º GB")
        Viatura.objects.create(prefixo="ABTS-02", opmcb="07º GB")
        
        self.client.login(email='admin@teste.com', password='password123')
        
        # Busca por prefixo
        response = self.client.get(reverse('cadastro_viaturas'), {'q': 'AS-01'})
        self.assertContains(response, "AS-01")
        self.assertNotContains(response, "ABTS-02")

        # Filtro de Unidade
        response = self.client.get(reverse('cadastro_viaturas'), {'unidade': '15º GB'})
        self.assertContains(response, "AS-01")

    def test_lista_postos_view(self):
        """Testa a listagem de postos."""
        Posto.objects.create(nome="POSTO_TESTE", unidade="15º GB")
        self.client.login(email='admin@teste.com', password='password123')
        response = self.client.get(reverse('lista_postos'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "POSTO_TESTE")
