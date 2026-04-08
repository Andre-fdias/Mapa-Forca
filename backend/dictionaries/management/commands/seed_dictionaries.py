from django.core.management.base import BaseCommand
from dictionaries.models import Dictionary

class Command(BaseCommand):
    help = 'Popula as tabelas de domínio (Dicionários) com valores iniciais'

    def handle(self, *args, **kwargs):
        data = {
            'STATUS_VIATURA': [
                ('OPERANDO', 'Operando', 1),
                ('BAIXADO', 'Baixado', 2),
                ('RESERVA', 'Reserva', 3),
                ('MANUTENCAO', 'Manutenção', 4),
            ],
            'TIPO_VIATURA': [
                ('AB', 'Auto Bomba', 1),
                ('UR', 'Unidade de Resgate', 2),
                ('AT', 'Auto Tanque', 3),
                ('VO', 'Viatura Operacional', 4),
                ('ABS', 'Auto Busca e Salvamento', 5),
                ('ABL', 'Auto Bomba Leve', 6),
                ('ABP', 'Auto Bomba Pesado', 7),
                ('USA', 'Unidade de Suporte Avançado', 8),
            ],
            'POSTO_GRADUACAO': [
                ('SD_PM', 'SD PM', 1),
                ('CB_PM', 'CB PM', 2),
                ('SGT_PM', 'SGT PM', 3),
                ('SUBTEN_PM', 'SUBTEN PM', 4),
                ('TEN_PM', 'TEN PM', 5),
                ('CAP_PM', 'CAP PM', 6),
            ],
            'STATUS_OPERACIONAL': [
                ('ATIVO', 'ATIVO', 1),
                ('INATIVO', 'INATIVO', 2),
                ('EM_OCORRENCIA', 'EM OCORRENCIA', 3),
                ('EM_APOIO', 'EM APOIO', 4),
            ],
            'TIPO_POSTO': [
                ('CMT', 'CMT', 1),
                ('ADM', 'ADM', 2),
                ('EB', 'EB', 3),
                ('TELEGRAFIA', 'TELEGRAFIA', 4),
                ('MOTOMEC', 'MOTOMEC', 5),
                ('COBOM', 'COBOM', 6),
                ('SEC_ADM', 'SEC ADM', 7),
                ('ATIV_TEC', 'ATIV TEC', 8),
            ],
            'TIPO_OCORRENCIA': [
                ('INCENDIO', 'INCENDIO', 1),
                ('RESGATE', 'RESGATE', 2),
                ('SALVAMENTO', 'SALVAMENTO', 3),
                ('APOIO', 'APOIO', 4),
                ('FALSO_ALARME', 'FALSO ALARME', 5),
            ],
            'TURNOS': [
                ('MANHA', 'MANHA', 1),
                ('TARDE', 'TARDE', 2),
                ('NOITE', 'NOITE', 3),
            ],
            'PRIORIDADE': [
                ('BAIXA', 'BAIXA', 1),
                ('MEDIA', 'MEDIA', 2),
                ('ALTA', 'ALTA', 3),
                ('CRITICA', 'CRITICA', 4),
            ],
            'STATUS_USUARIO': [
                ('ATIVO', 'ATIVO', 1),
                ('BLOQUEADO', 'BLOQUEADO', 2),
            ],
            'TIPO_ALERTA': [
                ('INFO', 'INFO', 1),
                ('ALERTA', 'ALERTA', 2),
                ('CRITICO', 'CRITICO', 3),
            ],
            'TIPO_UNIDADE': [
                ('GRANDE_COMANDO', 'Grande Comando', 1),
                ('BATALHAO', 'Batalhão', 2),
                ('POSTO', 'Posto de Bombeiros', 3),
                ('CENTRAL', 'Central de Controle', 4),
            ],
            'FUNCAO_OPERACIONAL': [
                ('COMANDANTE', 'Comandante', 1),
                ('MOTORISTA', 'Motorista', 2),
                ('AUXILIAR', 'Auxiliar', 3),
                ('SUPERVISOR', 'Supervisor', 4),
                ('DESPACHADOR', 'Despachador', 5),
                ('TELEGRAFISTA', 'Telegrafista', 6),
            ]
        }

        created_count = 0
        for tipo, items in data.items():
            for cod, nome, ordem in items:
                obj, created = Dictionary.objects.get_or_create(
                    tipo=tipo,
                    codigo=cod,
                    defaults={'nome': nome, 'ordem': ordem}
                )
                if created:
                    created_count += 1
        
        self.stdout.write(self.style.SUCCESS(f'Sucesso: {created_count} dicionários inseridos.'))
