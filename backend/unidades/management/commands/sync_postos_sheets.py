import pandas as pd
import requests
import io
from django.core.management.base import BaseCommand
from unidades.models import Municipio, Posto, normalize_text
from django.utils import timezone

class Command(BaseCommand):
    help = 'Sincroniza municípios e postos a partir de uma planilha Google Sheets'

    def handle(self, *args, **options):
        xlsx_url = "https://docs.google.com/spreadsheets/d/e/2PACX-1vT5UZ9PW-3N2_jkfgPdu4HNHshAABNfl_SsNvxMaM_ugJh4OzL5nVIlIfiqHkftY9bUmjXt_YN4kIal/pub?output=xlsx"
        
        try:
            self.stdout.write(f"Baixando planilha de {xlsx_url}...")
            response = requests.get(xlsx_url)
            response.raise_for_status()
            
            self.stdout.write("Processando aba 'municipios'...")
            try:
                df = pd.read_excel(io.BytesIO(response.content), sheet_name='municipios')
            except:
                df = pd.read_excel(io.BytesIO(response.content))
            
            if df.empty:
                self.stdout.write(self.style.WARNING("Planilha vazia ou aba não encontrada."))
                return

            # Mapeamento conforme fornecido pelo usuário
            # A=0, B=1, C=2, D=3, E=4, F=5, G=6, H=7, I=8, J=9, K=10, L=11, M=12, N=13, O=14, P=15
            idx_codigo = 0
            idx_sgb = 1
            idx_cod_secao = 2
            idx_posto_nome = 3
            idx_cidade_posto = 4
            idx_id_cidade = 5
            idx_tipo_cidade = 6
            idx_operacional_adm = 7
            idx_municipio_nome = 8
            idx_area = 9
            idx_populacao = 10
            idx_hab_km2 = 11
            idx_email = 12
            idx_bandeira = 13
            idx_endereco = 14
            idx_telefone = 15

            def clean_val(val):
                if pd.isna(val) or str(val).lower() in ['nan', 'none', '']:
                    return None
                return str(val).strip()

            def clean_num(val):
                if pd.isna(val) or str(val).lower() in ['nan', 'none', '']:
                    return None
                try:
                    s_val = str(val).replace('.', '').replace(',', '.')
                    return float(s_val)
                except:
                    return None

            self.stdout.write("Sincronizando dados...")

            for index, row in df.iterrows():
                try:
                    m_nome = clean_val(row.iloc[idx_municipio_nome])
                    p_nome = clean_val(row.iloc[idx_posto_nome])
                    tipo_cidade = clean_val(row.iloc[idx_tipo_cidade])
                    
                    if not m_nome or not p_nome:
                        continue

                    # 1. Sincroniza Município
                    municipio, _ = Municipio.objects.update_or_create(
                        nome=m_nome,
                        defaults={
                            'id_cidade': clean_val(row.iloc[idx_id_cidade]),
                            'tipo_cidade': tipo_cidade,
                            'area_km2': clean_num(row.iloc[idx_area]),
                            'populacao': int(clean_num(row.iloc[idx_populacao])) if clean_num(row.iloc[idx_populacao]) else None,
                            'hab_km2': clean_num(row.iloc[idx_hab_km2]),
                            'email': clean_val(row.iloc[idx_email]),
                            'bandeira': clean_val(row.iloc[idx_bandeira]),
                            'codigo': clean_val(row.iloc[idx_codigo]),
                            'fonte': 'Google Sheets (Público)'
                        }
                    )

                    # 2. Sincroniza Posto
                    # Se for SEDE, atualizamos todos os dados (incluindo endereço e telefone)
                    if tipo_cidade == 'SEDE':
                        posto, _ = Posto.objects.update_or_create(
                            nome=p_nome,
                            defaults={
                                'sgb': clean_val(row.iloc[idx_sgb]),
                                'cod_secao': clean_val(row.iloc[idx_cod_secao]),
                                'cidade_posto': clean_val(row.iloc[idx_cidade_posto]),
                                'operacional_adm': clean_val(row.iloc[idx_operacional_adm]),
                                'endereco_quarte': clean_val(row.iloc[idx_endereco]),
                                'telefone': clean_val(row.iloc[idx_telefone]),
                                'fonte': 'Google Sheets (Público)'
                            }
                        )
                    else:
                        # Se não for SEDE, apenas garante que o Posto existe (sem sobrescrever endereço/telefone com nulos)
                        posto, _ = Posto.objects.get_or_create(
                            nome=p_nome,
                            defaults={'fonte': 'Google Sheets (Público)'}
                        )
                    
                    # 3. Associa o município ao posto
                    posto.municipios.add(municipio)

                except Exception as row_error:
                    self.stdout.write(self.style.WARNING(f"Erro na linha {index}: {str(row_error)}"))

            self.stdout.write(self.style.SUCCESS(f'Sincronização concluída: {Municipio.objects.count()} municípios e {Posto.objects.count()} postos atualizados.'))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Falha na sincronização: {str(e)}'))
