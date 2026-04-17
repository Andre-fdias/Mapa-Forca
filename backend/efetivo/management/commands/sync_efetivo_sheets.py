import pandas as pd
import requests
import io
import re
from django.core.management.base import BaseCommand
from efetivo.models import Efetivo, Funcionario
from dictionaries.models import Dictionary
from django.utils import timezone

class Command(BaseCommand):
    help = 'Sincroniza o efetivo (Efetivo e Funcionario) e remove registros obsoletos'

    def handle(self, *args, **options):
        xlsx_url = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQIPOEm8NSpz2DAul4LEn4g0Sc1Be2hk5OqYWHpFSYcKvdImtXOrn-cYya7bBkhQWIATKHH27j5HAo5/pub?output=xlsx"
        
        try:
            self.stdout.write(f"Baixando planilha de {xlsx_url}...")
            response = requests.get(xlsx_url)
            response.raise_for_status()
            
            df = pd.read_excel(io.BytesIO(response.content), sheet_name='efetivo')
            
            if df.empty:
                self.stdout.write(self.style.WARNING("Planilha vazia."))
                return

            synced_names = []
            synced_res = []
            count = 0
            
            # Cache de Graduações para performance
            grad_map = {g.nome: g for g in Dictionary.objects.filter(tipo='POSTO_GRADUACAO')}

            def clean_val(val):
                if pd.isna(val) or str(val).lower() in ['nan', 'none', '']:
                    return None
                return str(val).strip()

            def parse_nome_padrao(nome_padrao):
                """Extrai Posto/Graduação e Nome de Guerra. Ex: 'CEL PM ANDRE' -> ('CEL PM', 'ANDRE')"""
                if not nome_padrao: return None, None
                for grad_nome in grad_map.keys():
                    if nome_padrao.startswith(grad_nome):
                        guerra = nome_padrao.replace(grad_nome, "").strip()
                        return grad_map[grad_nome], guerra
                return None, nome_padrao

            for _, row in df.iterrows():
                try:
                    nome_padrao = clean_val(row.get('NOME PADRAO'))
                    if not nome_padrao or len(nome_padrao) < 3:
                        continue
                    
                    re_num = clean_val(row.get('RE'))
                    dig = clean_val(row.get('DIG'))
                    
                    # Formata RE para 000000-0
                    if re_num and dig:
                        re_completo = f"{str(re_num).zfill(6)}-{dig}"
                    else:
                        re_completo = str(re_num) if re_num else None

                    # 1. Atualiza Tabela Flat (Efetivo)
                    Efetivo.objects.update_or_create(
                        nome=nome_padrao,
                        defaults={
                            're': re_completo,
                            'dig': dig,
                            'nome_do_pm': clean_val(row.get('NOME_DO_PM')),
                            'nome_guerra': clean_val(row.get('NOME DE GUERRA')),
                            'nome_padrao': nome_padrao,
                            'unidade': clean_val(row.get('UNIDADE')),
                            'sgb': clean_val(row.get('SGB')),
                            'posto_secao': clean_val(row.get('POSTO_SECAO')),
                            'chave_posto': clean_val(row.get('CHAVE_POSTO')),
                            'email': clean_val(row.get('EMAIL')),
                            'mergulho': clean_val(row.get('MERGULHO')),
                            'ovb': clean_val(row.get('OVB')),
                            'telefone': clean_val(row.get('telefone')),
                            'fonte': 'Google Sheets (MultiGB)',
                            'data_importacao': timezone.now()
                        }
                    )
                    synced_names.append(nome_padrao)

                    # 2. Atualiza Tabela Oficial (Funcionario) - Necessária para Escalas
                    if re_completo and "-" in re_completo:
                        grad, guerra = parse_nome_padrao(nome_padrao)
                        Funcionario.objects.update_or_create(
                            re=re_completo,
                            defaults={
                                'nome_completo': clean_val(row.get('NOME_DO_PM')) or nome_padrao,
                                'nome_guerra': guerra,
                                'posto_graduacao': grad,
                                'mergulho': clean_val(row.get('MERGULHO')),
                                'ovb': clean_val(row.get('OVB')),
                            }
                        )
                        synced_res.append(re_completo)

                    count += 1
                except Exception as row_error:
                    self.stdout.write(self.style.WARNING(f"Erro ao processar {nome_padrao}: {str(row_error)}"))

            # LIMPEZA
            del_efetivo, _ = Efetivo.objects.exclude(nome__in=synced_names).delete()
            del_func, _ = Funcionario.objects.exclude(re__in=synced_res).delete()

            self.stdout.write(self.style.SUCCESS(f'Sincronização concluída: {count} militares.'))
            if del_efetivo or del_func:
                self.stdout.write(self.style.WARNING(f'Removidos {del_efetivo} registros de Efetivo e {del_func} de Funcionario.'))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Falha na sincronização: {str(e)}'))
