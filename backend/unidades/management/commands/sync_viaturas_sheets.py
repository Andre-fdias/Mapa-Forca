import os
import gspread
from google.oauth2.service_account import Credentials
from django.core.management.base import BaseCommand
from unidades.models import Viatura, Unidade
from dictionaries.models import Dictionary
from django.conf import settings

class Command(BaseCommand):
    help = 'Sincroniza as viaturas da planilha Google Sheets (Aba QFF) com o banco de dados'

    def handle(self, *args, **options):
        # 1. Configurar Credenciais
        creds_path = os.path.join(settings.BASE_DIR, 'core', 'credentials.json')
        
        if not os.path.exists(creds_path):
            self.stdout.write(self.style.ERROR(f'ERRO: Arquivo de credenciais não encontrado em {creds_path}'))
            self.stdout.write(self.style.WARNING('Por favor, coloque o seu credentials.json (Service Account) na pasta backend/core/.'))
            return

        scopes = ["https://www.googleapis.com/auth/spreadsheets.readonly"]
        
        try:
            self.stdout.write("Conectando à Google Sheets API...")
            creds = Credentials.from_service_account_file(creds_path, scopes=scopes)
            client = gspread.authorize(creds)
            
            # ID da Planilha do link fornecido
            sheet_id = '1OlbWTO9JrWTxB247DlMrLQADy9p_dwFTEVEwqxAVeUU'
            spreadsheet = client.open_by_key(sheet_id)
            worksheet = spreadsheet.worksheet("QFF")
            
            # 2. Ler Dados
            self.stdout.write("Lendo aba QFF...")
            data = worksheet.get_all_values() # Retorna lista de listas
            
            if not data:
                self.stdout.write(self.style.WARNING("Planilha vazia ou sem dados."))
                return

            # Obter Status "OPERANDO" do nosso dicionário
            status_operando = Dictionary.objects.get(tipo='STATUS_VIATURA', codigo='OPERANDO')
            
            synced_count = 0
            # Pula o cabeçalho se houver (assumindo que a primeira linha é cabeçalho)
            for row in data[1:]:
                if len(row) < 2: continue
                
                prefixo = row[0].strip()
                status_text = row[1].strip().upper()
                
                if not prefixo: continue
                
                # Filtro: Apenas OPERANDO
                if status_text == "OPERANDO":
                    # Tenta atualizar ou criar
                    # Nota: unidade_base pode ficar nula se não soubermos qual é pela planilha
                    viatura, created = Viatura.objects.update_or_create(
                        prefixo=prefixo,
                        defaults={
                            'status_base': status_operando,
                            'fonte': 'Google Sheets'
                        }
                    )
                    synced_count += 1
                    status_msg = "Criada" if created else "Atualizada"
                    self.stdout.write(f"  - [{status_msg}] {prefixo}")

            self.stdout.write(self.style.SUCCESS(f'Sincronização concluída: {synced_count} viaturas sincronizadas.'))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Falha na sincronização: {str(e)}'))
