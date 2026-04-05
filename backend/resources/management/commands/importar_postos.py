from django.core.management.base import BaseCommand
from resources.models import Posto

class Command(BaseCommand):
    help = 'Importar postos operacionais mapeando hierarquia'

    def handle(self, *args, **kwargs):
        postos_bru = [
            {"nome": "CMT 1ºSGB", "mapa_sgb": "1º SGB", "codigo_secao": "703151000", "descricao": "CMT 1ºSGB - COMANDO LOCAL"},
            {"nome": "PELOTÃO CERRADO", "mapa_sgb": "1º SGB", "codigo_secao": "703151001", "descricao": "ATENDIMENTO OPERACIONAL CERRADO"},
            {"nome": "ZONA NORTE", "mapa_sgb": "1º SGB", "codigo_secao": "703151002", "descricao": "ATENDIMENTO ZONA NORTE"},
            {"nome": "ITU", "mapa_sgb": "2º SGB", "codigo_secao": "703152001", "descricao": "UNIDADE ITU"},
            {"nome": "PORTO FELIZ", "mapa_sgb": "2º SGB", "codigo_secao": "703152002", "descricao": "UNIDADE PORTO FELIZ"},
            {"nome": "TELEGRAFISTA ZONA NORTE", "mapa_sgb": "1º SGB", "codigo_secao": "703151003", "descricao": "TELEGRAFIA ZN"},
            {"nome": "COBOM SOROCABA", "mapa_sgb": "15º GB", "codigo_secao": "703150000", "descricao": "COBOM OPERAÇÕES"},
        ]

        count = 0
        for d in postos_bru:
            p, created = Posto.objects.get_or_create(
                codigo_secao=d['codigo_secao'],
                defaults={
                    'nome': d['nome'],
                    'mapa_sgb': d['mapa_sgb'],
                    'descricao': d['descricao']
                }
            )
            # Aciona save() para auto-categorizar TIPO_POSTO
            if not created:
                p.nome = d['nome']
                p.mapa_sgb = d['mapa_sgb']
                p.descricao = d['descricao']
            p.save()
            count += 1
        
        self.stdout.write(self.style.SUCCESS(f'Importação concluída. {count} postos processados.'))
