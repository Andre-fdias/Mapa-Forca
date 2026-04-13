import pandas as pd
import requests
import io
from django.core.management.base import BaseCommand
from efetivo.models import Efetivo
from django.utils import timezone

class Command(BaseCommand):
    help = 'Sincroniza o efetivo a partir de uma planilha Google Sheets pública em formato XLSX'

    def handle(self, *args, **options):
        # URL fornecida para exportação XLSX direta
        xlsx_url = "https://docs.google.com/spreadsheets/d/e/2PACX-1vR4yu0eKjcxp699cPVHudx8fg0vDwHy3Yz46ECREFInZa4NjkZmayTz08wkXChjv88PhV0s8Ni_9z_n/pub?output=xlsx"
        
        try:
            self.stdout.write(f"Baixando planilha de {xlsx_url}...")
            response = requests.get(xlsx_url)
            response.raise_for_status()
            
            # Lê o conteúdo baixado como um arquivo em memória (Excel)
            # A aba é 'tb_banco' (verificar se é case sensitive)
            self.stdout.write("Processando aba 'tb_Banco'...")
            
            # Tenta ler a aba especificada
            df = pd.read_excel(io.BytesIO(response.content), sheet_name='tb_Banco')
            
            if df.empty:
                self.stdout.write(self.style.WARNING("Planilha vazia ou aba não encontrada."))
                return

            # Mapeamento de índices das colunas (B=1, E=4, G=6, H=7, I=8, K=10, L=11)
            idx_posto_secao = 1 # Coluna B (POSTO)
            idx_re = 4 # Coluna E
            idx_nome_do_pm = 6 # Coluna G
            idx_nome_padrao = 7 # Coluna H (NOME DE GUERRA)
            idx_sgb = 10 # Coluna K
            idx_mergulho = 56
            idx_ovb = 57
            
            synced_count = 0
            
            def clean_val(val):
                if pd.isna(val) or str(val).lower() in ['nan', 'none', '']:
                    return None
                return str(val).strip()

            for index, row in df.iterrows():
                try:
                    # O nome padrão (Nome de Guerra - Coluna H) é obrigatório para identificação
                    nome = clean_val(row.iloc[idx_nome_padrao])
                    
                    if not nome or len(nome) < 3:
                        continue
                    
                    # Extrai os demais campos com os índices corrigidos
                    posto_secao = clean_val(row.iloc[idx_posto_secao]) if len(row) > idx_posto_secao else None
                    re = clean_val(row.iloc[idx_re]) if len(row) > idx_re else None
                    nome_do_pm = clean_val(row.iloc[idx_nome_do_pm]) if len(row) > idx_nome_do_pm else None
                    sgb = clean_val(row.iloc[idx_sgb]) if len(row) > idx_sgb else None
                    mergulho = clean_val(row.iloc[idx_mergulho]) if len(row) > idx_mergulho else None
                    ovb = clean_val(row.iloc[idx_ovb]) if len(row) > idx_ovb else None

                    # Tenta atualizar ou criar para garantir idempotência
                    efetivo, created = Efetivo.objects.update_or_create(
                        nome=nome,
                        defaults={
                            're': re,
                            'nome_do_pm': nome_do_pm,
                            'sgb': sgb,
                            'posto_secao': posto_secao,
                            'mergulho': mergulho,
                            'ovb': ovb,
                            'fonte': 'Google Sheets (Público)',
                            'data_importacao': timezone.now()
                        }
                    )
                    
                    synced_count += 1
                except Exception as row_error:
                    self.stdout.write(self.style.WARNING(f"Erro na linha {index}: {str(row_error)}"))
                    continue

            self.stdout.write(self.style.SUCCESS(f'Sincronização concluída: {synced_count} militares sincronizados.'))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Falha na sincronização: {str(e)}'))
            # Se falhar por nome da aba, vamos listar as abas para ajudar no debug
            try:
                if "Worksheet named" in str(e):
                    xls = pd.ExcelFile(io.BytesIO(response.content))
                    self.stdout.write(self.style.NOTICE(f"Abas disponíveis: {xls.sheet_names}"))
            except:
                pass
