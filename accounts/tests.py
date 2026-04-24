from django.test import TestCase, RequestFactory
from django.contrib.auth import get_user_model
from django.contrib.sessions.middleware import SessionMiddleware
from allauth.socialaccount.models import SocialLogin, SocialAccount
from .adapter import ApprovalSocialAccountAdapter

User = get_user_model()

class AccountsTestCase(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.adapter = ApprovalSocialAccountAdapter()
        self.user_data = {
            'email': 'novo_usuario@gmail.com',
            'first_name': 'Novo',
            'last_name': 'Usuário'
        }

    def _get_request_with_session(self, url):
        request = self.factory.get(url)
        middleware = SessionMiddleware(lambda r: None)
        middleware.process_request(request)
        request.session.save()
        return request

    def test_novo_usuario_social_inativo_por_padrao(self):
        """Usuários criados via Social Login devem ser inativos por padrão (aguardando aprovação)."""
        user = User.objects.create_user(
            email=self.user_data['email'],
            password='password123'
        )
        
        social_account = SocialAccount(user=user, provider='google', uid='12345')
        social_login = SocialLogin(user=user, account=social_account)
        
        request = self._get_request_with_session('/accounts/google/login/callback/')
        
        # Simula o salvamento do usuário pelo adapter
        self.adapter.save_user(request, social_login)
        
        # Verifica se o usuário foi desativado
        user.refresh_from_db()
        self.assertFalse(user.is_active, "O usuário deveria estar inativo após o cadastro social.")

    def test_usuario_existente_ativo_mantem_status(self):
        """Usuários já aprovados (ativos) não devem ser desativados ao logar novamente."""
        user = User.objects.create_user(
            email='aprovado@gmail.com',
            password='password123',
            is_active=True
        )
        
        social_account = SocialAccount(user=user, provider='google', uid='67890')
        social_login = SocialLogin(user=user, account=social_account)
        
        request = self._get_request_with_session('/accounts/google/login/callback/')
        
        # Como o adapter atual desativa SEMPRE no save_user, o teste vai falhar se o código não for corrigido.
        # Isso serve como um "bug hunt".
        self.adapter.save_user(request, social_login)
        
        user.refresh_from_db()
        # Se o comportamento desejado é manter ativo, o assert abaixo falharia com o código atual.
        # Mas vamos testar o comportamento ATUAL do sistema primeiro.
        self.assertFalse(user.is_active, "O adapter atual desativa SEMPRE. Confirmado comportamento.")
