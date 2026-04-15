import pandas as pd
import requests
import io
import re
from django.core.management.base import BaseCommand
from unidades.models import Viatura, Unidade
from dictionaries.models import Dictionary
from django.utils import timezone

class Command(BaseCommand):
    help = 'Sincroniza viaturas e limpa as que não constam na nova planilha'

    def handle(self, *args, **options):
        xlsx_url = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQIPOEm8NSpz2DAul4LEn4g0Sc1Be2hk5OqYWHpFSYcKvdImtXOrn-cYya7bBkhQWIATKHH27j5HAo5/pub?output=xlsx"
        
        try:
            self.stdout.write(f"Baixando viaturas...")
            response = requests.get(xlsx_url)
            response.raise_for_status()
            
            df = pd.read_excel(io.BytesIO(response.content), sheet_name='viaturas')
            
            if df.empty:
                self.stdout.write(self.style.WARNING("Planilha de viaturas vazia."))
                return

            status_map = {
                'OPERANDO': Dictionary.objects.filter(tipo='STATUS_VIATURA', codigo='OPERANDO').first(),
                'RESERVA': Dictionary.objects.filter(tipo='STATUS_VIATURA', codigo='RESERVA').first(),
                'BAIXADO': Dictionary.objects.filter(tipo='STATUS_VIATURA', codigo='BAIXADO').first(),
            }

            def clean_val(val):
                if pd.isna(val) or str(val).lower() in ['nan', 'none', '']:
                    return None
                return str(val).strip()

            def normalize_opm(opm_val):
                """Normaliza variações como '15ºGB', '15°GB', '15 GB' -> '15º GB'"""
                if not opm_val: return None
                val = str(opm_val).upper().replace(' ', '')
                match = re.search(r'(\d+)', val)
                if match:
                    num = match.group(1).zfill(2)
                    return f"{num}º GB"
                return val

            synced_prefixes = []
            count = 0
            
            for _, row in df.iterrows():
                try:
                    prefixo = clean_val(row.get('VIATURAS'))
                    if not prefixo or len(prefixo) < 3:
                        continue
                    prefixo = prefixo.upper()

                    status_txt = str(row.get('STATUS') or "").upper()
                    final_status = status_map['OPERANDO']
                    if 'RESERVA' in status_txt: 
                        final_status = status_map['RESERVA']
                    elif any(s in status_txt for s in ['MANU', 'BAIXA', 'RECOLHIDO', 'CSM']): 
                        final_status = status_map['BAIXADO']

                    garagem = clean_val(row.get('Garagem'))
                    unidade = Unidade.objects.filter(nome__icontains=garagem).first() if garagem else None
                    opm_norm = normalize_opm(clean_val(row.get('OPMCB')))

                    Viatura.objects.update_or_create(
                        prefixo=prefixo,
                        defaults={
                            'opmcb': opm_norm,
                            'sgb': clean_val(row.get('SGB')),
                            'placa': str(row.get('PLACA')).upper() if pd.notna(row.get('PLACA')) else None,
                            'status_base': final_status,
                            'garagem': garagem,
                            'vol_agua': clean_val(row.get('Água')),
                            'combustivel': clean_val(row.get('Combustível')),
                            'municipio': clean_val(row.get('MUNICÍPIO')),
                            'unidade_base': unidade,
                            'fonte': 'Google Sheets (MultiGB)'
                        }
                    )
                    synced_prefixes.append(prefixo)
                    count += 1
                except Exception as row_error:
                    self.stdout.write(self.style.WARNING(f"Erro no prefixo {prefixo}: {str(row_error)}"))

            # LIMPEZA: Remove viaturas que não estão na lista atual
            deleted_count, _ = Viatura.objects.exclude(prefixo__in=synced_prefixes).delete()

            self.stdout.write(self.style.SUCCESS(f'Sincronização concluída: {count} viaturas ativas.'))
            if deleted_count:
                self.stdout.write(self.style.WARNING(f'{deleted_count} viaturas obsoletas removidas.'))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Falha na sincronização: {str(e)}'))
