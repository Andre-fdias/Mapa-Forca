import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from unidades.models import Posto

postos = [
    "Posto 01 - Centro", "Posto 02 - Norte", "Posto 03 - Sul", "Posto 04 - Leste", "Posto 05 - Oeste",
    "Posto 06 - Industrial", "Posto 07 - Porto", "Posto 08 - Aeroporto", "Posto 09 - Rodoviária", "Posto 10 - Campus",
    "Posto 11 - Hospital", "Posto 12 - Estádio", "Posto 13 - Parque", "Posto 14 - Vila A", "Posto 15 - Vila B",
    "Posto 16 - Serra", "Posto 17 - Vale", "Posto 18 - Lago", "Posto 19 - Praia", "Posto 20 - Ilha",
    "Posto 21 - Distrito 1", "Posto 22 - Distrito 2", "Posto 23 - Distrito 3", "Posto 24 - Distrito 4", "Posto 25 - Distrito 5",
    "Posto 26 - Rural 1", "Posto 27 - Rural 2", "Posto 28 - Central de Comando"
]

for nome in postos:
    Posto.objects.get_or_create(nome=nome)

print(f"{len(postos)} postos criados com sucesso.")
