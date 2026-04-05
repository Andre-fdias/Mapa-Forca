from django.core.management.base import BaseCommand
from resources.models import Viatura
from dictionaries.models import Dictionary

class Command(BaseCommand):
    help = 'Importar viaturas de uma lista base e popular via Dicionários'

    def handle(self, *args, **kwargs):
        viaturas_bru = [
            {"prefixo": "UR-15104", "status": "OPERANDO"},
            {"prefixo": "UR-15105", "status": "OPERANDO"},
            {"prefixo": "ABS-15107", "status": "OPERANDO"},
            {"prefixo": "PP-15101", "status": "RESERVA"},
            {"prefixo": "ABS-15101", "status": "OPERANDO"},
            {"prefixo": "UR-15503", "status": "RESERVA"},
            {"prefixo": "AB-15106", "status": "RESERVA"},
            {"prefixo": "ABS-15202", "status": "OPERANDO"},
            {"prefixo": "UR-15221", "status": "OPERANDO"},
            {"prefixo": "AT-15201", "status": "RESERVA"},
            {"prefixo": "VO-15200", "status": "RESERVA"},
            {"prefixo": "ABL-15202", "status": "OPERANDO"},
            {"prefixo": "UR-15220", "status": "OPERANDO"},
            {"prefixo": "TP-15202", "status": "RESERVA"},
            {"prefixo": "GALÃO", "status": "RESERVA"}, # Will be ignored by validation if we want, or extracted
            {"prefixo": " ", "status": "OPERANDO"}, # Empty will be ignored
        ]

        count = 0
        ignored = 0
        for d in viaturas_bru:
            pref = str(d['prefixo']).strip().upper()
            if not pref or pref == 'GALÃO' or len(pref) < 3:
                ignored += 1
                continue
            
            # Map the basic dictionary status string to a code
            status_dict = Dictionary.objects.filter(tipo='STATUS_VIATURA', codigo=d['status'].upper()).first()
            
            v, created = Viatura.objects.get_or_create(
                prefixo=pref,
            )
            v.status_base = status_dict
            # The clean() method will derive 'tipo' automatically.
            v.save()
            count += 1
        
        self.stdout.write(self.style.SUCCESS(f'Importação concluída. {count} inseridas/atualizadas, {ignored} ignoradas.'))
