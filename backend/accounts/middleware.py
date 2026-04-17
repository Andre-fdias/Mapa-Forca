from django.shortcuts import redirect
from django.urls import reverse

class ApprovalRequiredMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            try:
                allowed_paths = [
                    reverse('request_access'),
                    reverse('waiting_approval'),
                    reverse('account_logout'),
                    '/admin/',
                    '/accounts/', # allauth base routes
                ]
                
                is_allowed = any(request.path.startswith(path) for path in allowed_paths)
                
                if not is_allowed:
                    if request.user.is_superuser or request.user.role == 'ADMIN':
                        pass # Admins are immune
                    else:
                        if request.user.status == 'pending' and not request.user.unidade:
                            return redirect('request_access')
                        
                        if request.user.status == 'pending':
                            return redirect('waiting_approval')
                            
                        if request.user.status == 'rejected':
                            return redirect('waiting_approval')
            except Exception:
                pass

        response = self.get_response(request)
        return response
