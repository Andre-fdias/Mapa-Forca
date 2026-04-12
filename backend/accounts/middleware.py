from django.shortcuts import redirect
from django.urls import reverse

class OnboardingMiddleware:
    """
    Middleware que força o usuário logado e ativo a configurar sua unidade
    antes de acessar qualquer outra parte do sistema.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated and request.user.is_active:
            # URLs que o usuário PODE acessar sem ter unidade vinculada
            allowed_urls = [
                reverse('setup_profile'),
                reverse('get_postos_unidade'),
                reverse('account_logout'),
                reverse('account_inactive'),
                '/admin/', # Permite acesso ao admin para superusers
            ]
            
            # Se o usuário NÃO tem unidade e não é superuser, e está tentando acessar algo fora da lista permitida
            if not request.user.unidade and not request.user.is_superuser:
                if request.path not in allowed_urls and not request.path.startswith('/accounts/google/'):
                    return redirect('setup_profile')

        response = self.get_response(request)
        return response
