from django.urls import path
from allauth.socialaccount.providers.google.views import GoogleOAuth2Adapter
from allauth.socialaccount.providers.oauth2.client import OAuth2Client
from dj_rest_auth.registration.views import SocialLoginView
from . import views

class GoogleLogin(SocialLoginView):
    adapter_class = GoogleOAuth2Adapter
    callback_url = "http://localhost:5173" # URL do frontend
    client_class = OAuth2Client

urlpatterns = [
    path('api/auth/social/google/', GoogleLogin.as_view(), name='google_login'),
    path('profile/', views.profile_view, name='profile'),
    path('admin-dashboard/', views.admin_dashboard_view, name='admin_dashboard'),
    path('approve-user/<int:user_id>/', views.approve_user_view, name='approve_user'),
    path('reject-user/<int:user_id>/', views.reject_user_view, name='reject_user'),
    path('request-access/', views.request_access_view, name='request_access'),
    path('waiting-approval/', views.waiting_approval_view, name='waiting_approval'),
    path('update-role/<int:user_id>/', views.update_user_role_view, name='update_user_role'),
    path('api/htmx/sgbs/', views.get_sgbs_htmx, name='get_sgbs_htmx'),
    path('api/htmx/postos/', views.get_postos_htmx, name='get_postos_htmx'),
]
