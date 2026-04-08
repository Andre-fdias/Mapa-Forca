import pandas as pd
import requests
import io
import re
from django.core.management.base import BaseCommand
from unidades.models import Viatura, Unidade, normalize_text
from dictionaries.models import Dictionary
from django.utils import timezone

class Command(BaseCommand):
    help = 'Sincroniza viaturas da aba QFF baixando a planilha pública em formato XLSX'

    def handle(self, *args, **options):
        # URL de exportação direta para XLSX da planilha especificada
        xlsx_url = "https://docs.google.com/spreadsheets/d/1OlbWTO9JrWTxB247DlMrLQADy9p_dwFTEVEwqxAVeUU/export?format=xlsx"
        
        try:
            self.stdout.write(f"Baixando planilha de {xlsx_url}...")
            response = requests.get(xlsx_url)
            response.raise_for_status()
            
            # Lê o conteúdo baixado como um arquivo Excel
            self.stdout.write("Processando aba 'QFF'...")
            df = pd.read_excel(io.BytesIO(response.content), sheet_name='QFF')
            
            if df.empty:
                self.stdout.write(self.style.WARNING("Planilha vazia ou aba não encontrada."))
                return

            # Mapeamento dinâmico baseado nos cabeçalhos reais identificados
            header = df.columns.tolist()
            col_map = {}
            for i, h in enumerate(header):
                h_norm = normalize_text(h)
                if h_norm == 'VIATURAS': col_map['prefixo'] = i
                elif h_norm == 'OPMCB': col_map['opmcb'] = i
                elif h_norm == 'SGB': col_map['sgb'] = i
                elif h_norm == 'PLACA': col_map['placa'] = i
                elif h_norm == 'STATUS': col_map['status'] = i
                elif h_norm == 'GARAGEM': col_map['garagem'] = i
                elif 'VOL' in h_norm and 'AGUA' in h_norm: col_map['vol_agua'] = i
                elif 'COMBUSTIVEL' in h_norm: col_map['combustivel'] = i
                elif h_norm == 'MUNICIPIO DA UNIDADE': col_map['municipio'] = i

            self.stdout.write(f"Mapeamento detectado: {col_map}")

            if 'prefixo' not in col_map:
                self.stdout.write(self.style.ERROR("Coluna 'VIATURAS' não encontrada na planilha."))
                return

            # Mapas de dicionário para status
            status_map = {
                'OPERANDO': Dictionary.objects.filter(tipo='STATUS_VIATURA', codigo='OPERANDO').first(),
                'RESERVA': Dictionary.objects.filter(tipo='STATUS_VIATURA', codigo='RESERVA').first(),
                'BAIXADO': Dictionary.objects.filter(tipo='STATUS_VIATURA', codigo='MANUTENCAO').first(),
            }

            def clean_val(val):
                if pd.isna(val) or str(val).lower() in ['nan', 'none', '']:
                    return None
                return str(val).strip()

            synced_prefixes = []
            count = 0
            
            for index, row in df.iterrows():
                try:
                    prefixo = clean_val(row.iloc[col_map['prefixo']])
                    if not prefixo or len(prefixo) < 3: continue
                    prefixo = prefixo.upper()

                    # Extração segura dos campos
                    opmcb = clean_val(row.iloc[col_map.get('opmcb')]) if 'opmcb' in col_map else None
                    sgb = clean_val(row.iloc[col_map.get('sgb')]) if 'sgb' in col_map else None
                    placa = clean_val(row.iloc[col_map.get('placa')]) if 'placa' in col_map else None
                    status_txt = str(row.iloc[col_map.get('status')]).upper() if 'status' in col_map else ""
                    garagem = clean_val(row.iloc[col_map.get('garagem')]) if 'garagem' in col_map else None
                    vol_agua = clean_val(row.iloc[col_map.get('vol_agua')]) if 'vol_agua' in col_map else None
                    combustivel = clean_val(row.iloc[col_map.get('combustivel')]) if 'combustivel' in col_map else None
                    municipio = clean_val(row.iloc[col_map.get('municipio')]) if 'municipio' in col_map else None

                    # Decidir Status
                    final_status = status_map['OPERANDO']
                    if 'RESERVA' in status_txt: 
                        final_status = status_map['RESERVA']
                    elif any(s in status_txt for s in ['MANU', 'BAIXA', 'RECOLHIDO', 'CSM']): 
                        final_status = status_map['BAIXADO']

                    # Tentar achar Unidade pelo nome da Garagem/Posto
                    unidade = Unidade.objects.filter(nome__icontains=garagem).first() if garagem else None

                    # Criar/Atualizar para garantir dados reais
                    Viatura.objects.update_or_create(
                        prefixo=prefixo,
                        defaults={
                            'opmcb': opmcb,
                            'sgb': sgb,
                            'placa': placa.upper() if placa else None,
                            'status_base': final_status,
                            'garagem': garagem,
                            'vol_agua': vol_agua,
                            'combustivel': combustivel,
                            'municipio': municipio,
                            'unidade_base': unidade,
                            'fonte': 'Google Sheets (Público)'
                        }
                    )
                    synced_prefixes.append(prefixo)
                    count += 1
                except Exception as row_error:
                    self.stdout.write(self.style.WARNING(f"Erro na linha {index}: {str(row_error)}"))

            # Remove viaturas sincronizadas anteriormente que não estão mais na planilha
            # e limpa dados de teste antigos
            Viatura.objects.exclude(prefixo__in=synced_prefixes).delete()

            self.stdout.write(self.style.SUCCESS(f'Sincronização concluída: {count} viaturas sincronizadas com dados REAIS.'))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Falha na sincronização: {str(e)}'))
