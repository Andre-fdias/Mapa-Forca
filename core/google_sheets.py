import gspread
import json
from django.conf import settings
from google.oauth2.service_account import Credentials

def get_gspread_client():
    """
    Retorna um cliente gspread autenticado usando as configurações do Django.
    Tenta primeiro o conteúdo JSON (string) e depois o caminho do arquivo.
    """
    scopes = [
        'https://www.googleapis.com/auth/spreadsheets',
        'https://www.googleapis.com/auth/drive'
    ]

    if settings.GOOGLE_SHEETS_CREDENTIALS_JSON:
        creds_dict = json.loads(settings.GOOGLE_SHEETS_CREDENTIALS_JSON)
        credentials = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    elif settings.GOOGLE_SHEETS_CREDENTIALS_FILE:
        credentials = Credentials.from_service_account_file(settings.GOOGLE_SHEETS_CREDENTIALS_FILE, scopes=scopes)
    else:
        raise ValueError("Configurações de credenciais do Google Sheets não encontradas (JSON ou FILE).")

    return gspread.authorize(credentials)

def get_spreadsheet():
    """
    Retorna a planilha configurada no settings.py
    """
    client = get_gspread_client()
    return client.open_by_key(settings.GOOGLE_SHEETS_SPREADSHEET_ID)
