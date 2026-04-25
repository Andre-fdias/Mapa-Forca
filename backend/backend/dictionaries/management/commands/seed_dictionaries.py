from django.core.management.base import BaseCommand
from dictionaries.models import Dictionary

class Command(BaseCommand):
    help = 'Popula as tabelas de domínio (Dicionários) com valores oficiais e ordenação correta'

    def handle(self, *args, **kwargs):
        # 1. POSTO / GRADUAÇÃO (ORDEM DE PRECEDÊNCIA)
        graduacoes = [
            ('CEL PM', 'CEL_PM', 1),
            ('TEN CEL PM', 'TEN_CEL_PM', 2),
            ('MAJ PM', 'MAJ_PM', 3),
            ('CAP PM', 'CAP_PM', 4),
            ('1º TEN PM', '1_TEN_PM', 5),
            ('2º TEN PM', '2_TEN_PM', 6),
            ('ASP PM', 'ASP_PM', 7),
            ('SUBTEN PM', 'SUBTEN_PM', 8),
            ('1º SGT PM', '1_SGT_PM', 9),
            ('2º SGT PM', '2_SGT_PM', 10),
            ('3º SGT PM', '3_SGT_PM', 11),
            ('CB PM', 'CB_PM', 12),
            ('SD PM', 'SD_PM', 13),
        ]

        # 2. FUNÇÕES OPERACIONAIS
        funcoes = [
            ('COMANDANTE', 'COMANDANTE', 1),
            ('MOTORISTA', 'MOTORISTA', 2),
            ('AUXILIAR', 'AUXILIAR', 3),
            ('TELEGRAFISTA', 'TELEGRAFISTA', 4),
            ('SUPERVISOR', 'SUPERVISOR', 5),
            ('ENCARREGADO', 'ENCARREGADO', 6),
        ]

        # 3. STATUS DE VIATURA
        status_vtr = [
            ('OPERANDO', 'OPERANDO', 1),
            ('RESERVA', 'RESERVA', 2),
            ('BAIXADO', 'BAIXADO', 3),
        ]

        # 4. TIPO DE UNIDADE
        tipos_unidade = [
            ('GRANDE COMANDO', 'GRANDE_COMANDO', 1),
            ('BATALHÃO', 'BATALHAO', 2),
            ('POSTO', 'POSTO', 3),
            ('CENTRAL', 'CENTRAL', 4),
        ]

        # Limpeza para evitar duplicatas com códigos antigos
        Dictionary.objects.filter(tipo='POSTO_GRADUACAO').delete()

        data_map = {
            'POSTO_GRADUACAO': graduacoes,
            'FUNCAO_OPERACIONAL': funcoes,
            'STATUS_VIATURA': status_vtr,
            'TIPO_UNIDADE': tipos_unidade,
        }

        created_count = 0
        for tipo, lista in data_map.items():
            for nome, codigo, ordem in lista:
                obj, created = Dictionary.objects.get_or_create(
                    tipo=tipo,
                    codigo=codigo,
                    defaults={'nome': nome, 'ordem': ordem}
                )
                if not created:
                    obj.nome = nome
                    obj.ordem = ordem
                    obj.save()
                created_count += 1
        
        self.stdout.write(self.style.SUCCESS(f'Sucesso: {created_count} dicionários configurados com a nova ordem.'))
