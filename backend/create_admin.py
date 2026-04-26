import os
import django
from django.contrib.auth import get_user_model

def create_admin():
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
    django.setup()
    
    User = get_user_model()
    email = os.environ.get('ADMIN_EMAIL')
    password = os.environ.get('ADMIN_PASSWORD')
    
    if not email or not password:
        print("ADMIN_EMAIL ou ADMIN_PASSWORD não configurados. Pulando criação de superuser.")
        return

    if not User.objects.filter(email=email).exists():
        print(f"Criando superuser para {email}...")
        User.objects.create_superuser(email=email, password=password)
        print("Superuser criado com sucesso!")
    else:
        print(f"Superuser {email} já existe.")

if __name__ == "__main__":
    create_admin()
