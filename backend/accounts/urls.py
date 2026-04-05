from django.urls import path
from allauth.socialaccount.providers.google.views import GoogleOAuth2Adapter
from allauth.socialaccount.providers.oauth2.client import OAuth2Client
from dj_rest_auth.registration.views import SocialLoginView

class GoogleLogin(SocialLoginView):
    adapter_class = GoogleOAuth2Adapter
    callback_url = "http://localhost:5173" # URL do frontend
    client_class = OAuth2Client

urlpatterns = [
    path('google/', GoogleLogin.as_view(), name='google_login'),
]
