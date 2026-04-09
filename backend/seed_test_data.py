import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from efetivo.models import Funcionario
from unidades.models import Viatura, Posto

def seed():
    print("O script de seed_test_data foi limpo para remover dados fictícios.")
    # Este script pode ser usado no futuro para carregar dados reais se necessário.
    pass

if __name__ == "__main__":
    seed()
