from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.contrib import messages

class ApprovalSocialAccountAdapter(DefaultSocialAccountAdapter):
    def save_user(self, request, sociallogin, form=None):
        user = super().save_user(request, sociallogin, form)
        # Desativa o usuário recém-criado via Social Login
        user.is_active = False
        user.save()
        return user

    def authentication_error(self, request, provider_id, error, exception, extra_context):
        messages.error(request, "Sua conta está aguardando aprovação de um administrador.")
