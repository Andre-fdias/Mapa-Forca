import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from employees.models import Funcionario
from resources.models import Viatura, Posto

def seed():
    print("Populando dados de teste...")
    
    # 1. Garantir que os postos existem (já rodamos antes, mas por segurança)
    if Posto.objects.count() == 0:
        postos = ["CENTRAL", "POSTO 1", "POSTO 2", "POSTO 3"]
        for p in postos:
            Posto.objects.get_or_create(nome=p)

    # 2. Criar Funcionários de Exemplo
    funcionarios = [
        {"re": "100200-1", "nome_completo": "JOÃO BATISTA SILVA", "nome_guerra": "SILVA", "posto_grad": "SGT PM"},
        {"re": "150300-2", "nome_completo": "MARCOS ANTONIO OLIVEIRA", "nome_guerra": "OLIVEIRA", "posto_grad": "CB PM"},
        {"re": "200400-3", "nome_completo": "RICARDO GOMES", "nome_guerra": "GOMES", "posto_grad": "SD PM"},
        {"re": "250500-4", "nome_completo": "CARLOS EDUARDO SOUZA", "nome_guerra": "SOUZA", "posto_grad": "SD PM"},
        {"re": "300600-5", "nome_completo": "FERNANDO COSTA", "nome_guerra": "COSTA", "posto_grad": "TEN PM"},
    ]

    for f in funcionarios:
        Funcionario.objects.get_or_create(
            re=f['re'],
            defaults={
                'nome_completo': f['nome_completo'],
                'nome_guerra': f['nome_guerra'],
                'posto_grad': f['posto_grad']
            }
        )

    # 3. Criar Viaturas de Exemplo
    viaturas = [
        {"prefixo": "L-10", "placa": "ABC-1234", "status_base": "OPERANDO"},
        {"prefixo": "ABTS-05", "placa": "DEF-5678", "status_base": "OPERANDO"},
        {"prefixo": "UR-02", "placa": "GHI-9012", "status_base": "RESERVA"},
    ]

    posto_central = Posto.objects.first()
    for v in viaturas:
        Viatura.objects.get_or_create(
            prefixo=v['prefixo'],
            defaults={
                'placa': v['placa'],
                'posto_base': posto_central,
                'status_base': v['status_base']
            }
        )

    print(f"Sucesso: {Funcionario.objects.count()} funcionários e {Viatura.objects.count()} viaturas cadastrados.")

if __name__ == "__main__":
    seed()
