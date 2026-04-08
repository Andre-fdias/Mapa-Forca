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

            # A coluna I é o índice 8 (A=0, B=1, ..., I=8)
            # No pandas, podemos acessar pelo índice da coluna se não soubermos o nome exato do cabeçalho
            coluna_nome_index = 8
            
            synced_count = 0
            
            for index, row in df.iterrows():
                try:
                    # Verifica se a linha tem colunas suficientes
                    if len(row) <= coluna_nome_index:
                        continue
                        
                    nome = str(row.iloc[coluna_nome_index]).strip()
                    
                    # Ignora valores vazios, 'nan' ou cabeçalhos
                    if not nome or nome.lower() in ['nan', 'none', 'nome', ''] or len(nome) < 3:
                        continue
                    
                    # Tenta atualizar ou criar para garantir idempotência
                    efetivo, created = Efetivo.objects.update_or_create(
                        nome=nome,
                        defaults={
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
