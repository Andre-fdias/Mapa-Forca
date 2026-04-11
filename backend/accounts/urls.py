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
    path('approve-link/<int:user_id>/', views.approve_link_view, name='approve_link'),
    path('inactive/', views.account_inactive_view, name='account_inactive'),
]
