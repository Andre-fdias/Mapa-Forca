import random
from datetime import date, time
from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Q
from escalas.models import MapaDiario, AlocacaoViatura, AlocacaoFuncionario
from unidades.models import Unidade, Viatura
from efetivo.models import Funcionario, Efetivo
from dictionaries.models import Dictionary

class Command(BaseCommand):
    help = 'Simulação completa: preenche TODOS os campos, métricas, postos e TELEGRAFIA.'

    def handle(self, *args, **options):
        hoje = date.today()
        self.stdout.write(f"Iniciando Simulação Total para {hoje}...")

        # 1. Preparar Dicionários
        try:
            status_operando = Dictionary.objects.get(tipo='STATUS_VIATURA', codigo='OPERANDO')
            f_cmt = Dictionary.objects.get(tipo='FUNCAO_OPERACIONAL', codigo='COMANDANTE')
            f_mot = Dictionary.objects.get(tipo='FUNCAO_OPERACIONAL', codigo='MOTORISTA')
            f_aux = Dictionary.objects.get(tipo='FUNCAO_OPERACIONAL', codigo='AUXILIAR')
            f_sup = Dictionary.objects.get(tipo='FUNCAO_OPERACIONAL', codigo='SUPERVISOR')
            f_tele = Dictionary.objects.filter(tipo='FUNCAO_OPERACIONAL', nome__icontains='Telegrafista').first() or f_aux
            f_chefe = Dictionary.objects.filter(tipo='FUNCAO_OPERACIONAL', nome__icontains='Chefe').first() or f_cmt
        except Dictionary.DoesNotExist as e:
            self.stderr.write(f"Erro de dicionário: {e}")
            return

        unidades = Unidade.objects.all()
        funcionarios = list(Funcionario.objects.all())
        
        # 2. Garantir dados de Efetivo
        for f in funcionarios:
            ef, _ = Efetivo.objects.get_or_create(re=f.re, defaults={'nome': f.nome_guerra})
            if not ef.telefone:
                ef.telefone = f"(11) 9{random.randint(7000, 9999)}-{random.randint(1000, 9999)}"
            ef.mergulho = "SIM (S)" if random.random() < 0.2 else "NÃO"
            ef.save()

        FUNCOES_COBOM_ESPERADAS = [
            'Oficial de Operações DEJEM', 'Chefe de Equipe', 'Supervisor Despacho', 
            'Supervisor 193', 'Atendente 193', 'Enfermeiro de Triagem', 'Inclusor', 
            'Supervisor COE Autoban'
        ]

        with transaction.atomic():
            for unidade in unidades:
                mapa, _ = MapaDiario.objects.get_or_create(
                    data=hoje, unidade=unidade,
                    defaults={'prontidao': 'VERDE', 'equipe': 'A', 'periodo': 'dia', 'finalizado': True}
                )
                mapa.finalizado = True
                mapa.save()

                AlocacaoFuncionario.objects.filter(mapa=mapa).delete()
                AlocacaoViatura.objects.filter(mapa=mapa).delete()
                
                disponiveis = random.sample(funcionarios, min(len(funcionarios), 30))

                # --- 3. TELEGRAFIA (Inserir como se fosse uma viatura virtual para cada unidade) ---
                vtr_tele, _ = Viatura.objects.get_or_create(
                    prefixo='TELEGRAFIA',
                    defaults={'placa': 'SIM-0000', 'opmcb': 'GERAL', 'status_base': status_operando}
                )
                
                aloc_vtr_tele = AlocacaoViatura.objects.create(
                    mapa=mapa, viatura=vtr_tele, status_no_dia=status_operando
                )
                
                if disponiveis:
                    # Alocar um militar na "Viatura" de Telegrafia
                    func_tele = disponiveis.pop()
                    AlocacaoFuncionario.objects.create(
                        mapa=mapa,
                        alocacao_viatura=aloc_vtr_tele,
                        funcionario=func_tele,
                        funcao=f_tele,
                        inicio_servico=time(7, 30),
                        termino_servico=time(7, 30)
                    )

                # --- 4. COBOM / CBI (Campos Específicos) ---
                if "COBOM" in unidade.nome.upper() or "CBI" in unidade.nome.upper():
                    for func_nome in FUNCOES_COBOM_ESPERADAS:
                        if disponiveis:
                            f_obj, _ = Dictionary.objects.get_or_create(
                                tipo='FUNCAO_OPERACIONAL', nome=func_nome,
                                defaults={'codigo': func_nome.upper().replace(' ', '_')[:10]}
                            )
                            AlocacaoFuncionario.objects.create(
                                mapa=mapa, funcionario=disponiveis.pop(), funcao=f_obj,
                                inicio_servico=time(6, 45), termino_servico=time(19, 0)
                            )

                # --- 5. BATALHÃO ---
                if "GB" in unidade.nome.upper() and "SGB" not in unidade.nome.upper():
                    if disponiveis:
                        AlocacaoFuncionario.objects.create(
                            mapa=mapa, funcionario=disponiveis.pop(), funcao=f_sup, sub_funcao='supervisor',
                            inicio_servico=time(7, 30), termino_servico=time(7, 30)
                        )
                    if disponiveis:
                        AlocacaoFuncionario.objects.create(
                            mapa=mapa, funcionario=disponiveis.pop(), funcao=f_cmt, is_oficial_area=True,
                            inicio_servico=time(7, 30), termino_servico=time(7, 30)
                        )

                # --- 6. VIATURAS OPERACIONAIS ---
                viaturas = Viatura.objects.filter(Q(unidade_base=unidade) | Q(opmcb__icontains=unidade.nome)).exclude(prefixo='TELEGRAFIA')[:2]
                for vtr in viaturas:
                    vtr.combustivel = random.choice(['1/1', '3/4', '1/2'])
                    vtr.save()
                    aloc_vtr = AlocacaoViatura.objects.create(mapa=mapa, viatura=vtr, status_no_dia=status_operando)
                    equipe_funcoes = [f_cmt, f_mot, f_aux]
                    for func_tipo in equipe_funcoes:
                        if disponiveis:
                            AlocacaoFuncionario.objects.create(
                                mapa=mapa, alocacao_viatura=aloc_vtr, funcionario=disponiveis.pop(), 
                                funcao=func_tipo, sub_funcao='motorista' if func_tipo == f_mot else None,
                                dejem=random.random() < 0.2,
                                inicio_servico=time(7, 30), termino_servico=time(7, 30)
                            )

                # --- 7. COMANDANTE DE PRONTIDÃO ---
                if ("SGB" in unidade.nome.upper() or not "GB" in unidade.nome.upper()) and "COBOM" not in unidade.nome.upper() and "CBI" not in unidade.nome.upper():
                    if disponiveis:
                        AlocacaoFuncionario.objects.create(
                            mapa=mapa, funcionario=disponiveis.pop(), funcao=f_cmt, is_comandante_prontidao=True,
                            inicio_servico=time(7, 30), termino_servico=time(7, 30)
                        )

                self.stdout.write(f"OK: {unidade.nome}")

        self.stdout.write(self.style.SUCCESS('Simulação TOTAL com TELEGRAFIA concluída!'))
