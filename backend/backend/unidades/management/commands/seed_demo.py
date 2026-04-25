from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from dictionaries.models import Dictionary
from unidades.models import Unidade, Viatura
from efetivo.models import Funcionario
import random

User = get_user_model()

class Command(BaseCommand):
    help = 'Popula dados reais do 15º GB para demonstração do Dashboard COBOM'

    def handle(self, *args, **kwargs):
        self.stdout.write("Limpando dados antigos...")
        Viatura.objects.all().delete()
        Funcionario.objects.all().delete()
        Unidade.objects.all().delete()
        User.objects.all().delete()

        def get_dict(tipo, codigo):
            return Dictionary.objects.get(tipo=tipo, codigo=codigo)

        # 1. Criar o Grupamento (15º GB)
        grupamento = Unidade.objects.create(
            nome="15º Grupamento de Bombeiros",
            tipo_unidade=get_dict('TIPO_UNIDADE', 'GRANDE_COMANDO'),
            telefone="(15) 3232-1234"
        )

        # 2. Criar os 5 SGBs e seus Postos
        sgbs_config = {
            "1º SGB — Sorocaba": ["Cabreúva", "Central", "Éden", "Ipanema", "Santa Rosália", "Votorantim"],
            "2º SGB — Itu": ["Central Itu", "Porto Feliz", "Salto", "Tatuí", "Tietê"],
            "3º SGB — Itapeva": ["Apiaí", "Capão Bonito", "Central Itapeva", "Itararé"],
            "4º SGB — Itapetininga": ["Angatuba", "Boituva", "Central Itapetininga", "Cerquilho"],
            "5º SGB — São Roque": ["Central São Roque", "Ibiúna", "Mairinque", "Piedade"]
        }

        tipo_batalhao = get_dict('TIPO_UNIDADE', 'BATALHAO')
        tipo_posto = get_dict('TIPO_UNIDADE', 'POSTO')
        status_opr = get_dict('STATUS_VIATURA', 'OPERANDO')
        status_res = get_dict('STATUS_VIATURA', 'RESERVA')
        
        all_postos = []

        for sgb_nome, postos_nomes in sgbs_config.items():
            sgb_obj = Unidade.objects.create(
                nome=sgb_nome,
                parent=grupamento,
                tipo_unidade=tipo_batalhao
            )
            for p_nome in postos_nomes:
                posto = Unidade.objects.create(
                    nome=p_nome,
                    parent=sgb_obj,
                    tipo_unidade=tipo_posto,
                    telefone=f"(15) 32{random.randint(10, 99)}-{random.randint(1000, 9999)}"
                )
                all_postos.append(posto)

        # 3. Usuário Admin
        user = User.objects.create_superuser(email='admin@mapa.sp.gov.br', password='admin123')
        user.unidade = grupamento
        user.role = 'ADMIN'
        user.save()
        
        self.stdout.write(self.style.SUCCESS(f'Sucesso: 15º GB populado com {Unidade.objects.count()} unidades.'))
