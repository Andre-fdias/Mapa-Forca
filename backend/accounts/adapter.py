from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.shortcuts import redirect
from django.urls import reverse

class ApprovalSocialAccountAdapter(DefaultSocialAccountAdapter):
    def save_user(self, request, sociallogin, form=None):
        user = super().save_user(request, sociallogin, form)
        # O model User já define status='pending' por default.
        return user

    def get_login_redirect_url(self, request):
        user = request.user
        
        # 1. Se o status é pending e o usuário ainda não escolheu sua unidade, vai para o Form de Setup
        if user.status == 'pending' and not user.unidade:
            return reverse('request_access')
            
        # 2. Se já escolheu a unidade mas continua pending, vai para a tela de aviso de aprovação
        if user.status == 'pending':
            return reverse('waiting_approval')
            
        # 3. Se foi aprovado, vai para a rota padrão operacional
        if user.status == 'approved':
            return reverse('index')
            
        return reverse('waiting_approval')
