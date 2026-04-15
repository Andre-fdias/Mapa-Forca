import pandas as pd
import requests
import io
import re
from django.core.management.base import BaseCommand
from unidades.models import Municipio, Posto, Unidade
from dictionaries.models import Dictionary

class Command(BaseCommand):
    help = 'Sincroniza municípios, postos e a hierarquia de Unidades'

    def handle(self, *args, **options):
        xlsx_url = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQIPOEm8NSpz2DAul4LEn4g0Sc1Be2hk5OqYWHpFSYcKvdImtXOrn-cYya7bBkhQWIATKHH27j5HAo5/pub?output=xlsx"
        
        try:
            self.stdout.write(f"Baixando postos...")
            response = requests.get(xlsx_url)
            response.raise_for_status()
            
            df = pd.read_excel(io.BytesIO(response.content), sheet_name='postos')
            
            if df.empty:
                self.stdout.write(self.style.WARNING("Planilha vazia."))
                return

            def clean_val(val):
                if pd.isna(val) or str(val).lower() in ['nan', 'none', '']:
                    return None
                return str(val).strip()

            def normalize_opm(opm_val):
                """Normaliza '7º GB' para '07º GB'"""
                if not opm_val: return None
                val = str(opm_val).upper().replace(' ', '')
                match = re.search(r'(\d+)', val)
                if match:
                    num = match.group(1).zfill(2)
                    return f"{num}º GB"
                return val

            def normalize_sgb(sgb_val):
                """Transforma '1' ou '1 SGB' em '1º SGB'"""
                if not sgb_val: return None
                val = str(sgb_val).upper().replace('º', '').replace('°', '')
                if val.isdigit():
                    return f"{val}º SGB"
                match = re.match(r'(\d+)\s*SGB', val)
                if match:
                    return f"{match.group(1)}º SGB"
                return val

            synced_postos = []
            synced_municipios = []
            synced_unidades = []

            # Dicionários de tipos de unidade
            tipo_batalhao = Dictionary.objects.filter(tipo='TIPO_UNIDADE', codigo='BATALHAO').first()
            tipo_posto = Dictionary.objects.filter(tipo='TIPO_UNIDADE', codigo='POSTO').first()

            # 0. Unidade Raiz
            raiz, _ = Unidade.objects.get_or_create(
                nome='CBPMESP',
                defaults={'tipo_unidade': tipo_batalhao}
            )
            synced_unidades.append(raiz.nome)

            for _, row in df.iterrows():
                try:
                    m_nome = clean_val(row.get('MUNICÍPIO'))
                    p_raw_nome = clean_val(row.get('Postos'))
                    sgb_raw = clean_val(row.get('sgb'))
                    sgb_nome = normalize_sgb(sgb_raw)
                    unidade_nome = normalize_opm(clean_val(row.get('Unidade')))
                    chave_posto = clean_val(row.get('CHAVE_POSTO'))
                    
                    if not m_nome or not p_raw_nome:
                        continue

                    # 1. Município
                    municipio, _ = Municipio.objects.get_or_create(
                        nome=m_nome,
                        defaults={'fonte': 'Google Sheets (MultiGB)'}
                    )
                    synced_municipios.append(m_nome)

                    # 2. OPM
                    opm_obj = raiz
                    if unidade_nome:
                        opm_obj, _ = Unidade.objects.update_or_create(
                            nome=unidade_nome,
                            defaults={'parent': raiz, 'tipo_unidade': tipo_batalhao}
                        )
                        synced_unidades.append(opm_obj.nome)

                    # 3. SGB
                    sgb_obj = None
                    if sgb_nome:
                        sgb_obj, _ = Unidade.objects.update_or_create(
                            nome=f"{unidade_nome} - {sgb_nome}" if unidade_nome else sgb_nome,
                            defaults={'parent': opm_obj, 'tipo_unidade': tipo_posto}
                        )
                        synced_unidades.append(sgb_obj.nome)

                    # 4. Unidade Posto (Hierarquia)
                    # Usamos a chave do posto para garantir que o objeto seja o mesmo
                    unidade_posto, _ = Unidade.objects.update_or_create(
                        codigo_secao=chave_posto,
                        defaults={
                            'nome': p_raw_nome,
                            'parent': sgb_obj or opm_obj,
                            'tipo_unidade': tipo_posto
                        }
                    )
                    synced_unidades.append(unidade_posto.nome)

                    # 5. Posto (Model Flat)
                    Posto.objects.update_or_create(
                        nome=p_raw_nome,
                        defaults={
                            'unidade': unidade_nome,
                            'sgb': sgb_nome,
                            'cod_secao': chave_posto,
                            'fonte': 'Google Sheets (MultiGB)'
                        }
                    )
                    synced_postos.append(p_raw_nome)
                    
                    # Município (Muitos para Muitos)
                    p_obj = Posto.objects.get(nome=p_raw_nome)
                    p_obj.municipios.add(municipio)

                except Exception as row_error:
                    self.stdout.write(self.style.WARNING(f"Erro ao importar {row.get('Postos')}: {str(row_error)}"))

            # LIMPEZA
            Posto.objects.exclude(nome__in=synced_postos).delete()
            # Municipio.objects.exclude(nome__in=synced_municipios).delete()
            # Unidade.objects.exclude(nome__in=synced_unidades).delete()

            self.stdout.write(self.style.SUCCESS(f'Sincronização concluída. Postos: {len(synced_postos)}.'))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Falha na sincronização: {str(e)}'))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Falha na sincronização: {str(e)}'))
