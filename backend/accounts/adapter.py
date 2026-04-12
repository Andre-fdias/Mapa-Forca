from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.shortcuts import redirect
from django.urls import reverse

class ApprovalSocialAccountAdapter(DefaultSocialAccountAdapter):
    def save_user(self, request, sociallogin, form=None):
        # Verifica se o usuário já existe no banco antes de salvar
        user_exists = sociallogin.is_existing
        user = super().save_user(request, sociallogin, form)
        
        if not user_exists:
            # Se é um novo usuário social, BLOQUEIA IMEDIATAMENTE
            user.is_active = False
            user.save()
        return user

    def get_login_redirect_url(self, request):
        user = request.user
        
        # 1. Se ainda está inativo, vai para a página de "Aguarde aprovação"
        if not user.is_active:
            return reverse('account_inactive')
        
        # 2. Se já foi aprovado mas NÃO TEM unidade vinculada, vai para o "Escolha sua Unidade"
        if not user.unidade:
            return reverse('setup_profile')
            
        # 3. Se está tudo ok, vai para a home
        return reverse('index')
