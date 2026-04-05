import re
import unicodedata
from django.db import models
from dictionaries.models import Dictionary

def normalize_text(text):
    if not text:
        return ""
    # Remove acentos
    text = ''.join(c for c in unicodedata.normalize('NFD', str(text)) if unicodedata.category(c) != 'Mn')
    text = text.upper().strip()
    return text

class Posto(models.Model):
    nome = models.CharField(max_length=100, unique=True)
    mapa_sgb = models.CharField(max_length=50, blank=True, null=True)
    codigo_secao = models.CharField(max_length=50, unique=True, null=True)
    descricao = models.CharField(max_length=255, blank=True, null=True)
    tipo = models.ForeignKey(Dictionary, on_delete=models.SET_NULL, null=True, limit_choices_to={'tipo': 'TIPO_POSTO'})
    ativo = models.BooleanField(default=True)

    def __str__(self):
        return self.nome

    def clean(self):
        # Auto-determina o tipo através da descrição
        if self.descricao and not self.tipo_id:
            desc = self.descricao.upper()
            tipo_codigo = None
            if "CMT" in desc: tipo_codigo = "CMT"
            elif "ADM" in desc: tipo_codigo = "ADM"
            elif "EB" in desc: tipo_codigo = "EB"
            elif "TELEGRAF" in desc: tipo_codigo = "TELEGRAFIA"
            elif "MOTOMEC" in desc: tipo_codigo = "MOTOMEC"
            elif "COBOM" in desc: tipo_codigo = "COBOM"
            elif "SEC ADM" in desc: tipo_codigo = "SEC_ADM"
            elif "ATIV TEC" in desc: tipo_codigo = "ATIV_TEC"
            
            if tipo_codigo:
                dict_tipo = Dictionary.objects.filter(tipo='TIPO_POSTO', codigo=tipo_codigo).first()
                if dict_tipo:
                    self.tipo = dict_tipo

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = 'Posto'
        verbose_name_plural = 'Postos'
        ordering = ['nome']

class Viatura(models.Model):
    prefixo = models.CharField(max_length=20, primary_key=True)
    placa = models.CharField(max_length=8, unique=True, null=True, blank=True)
    municipio = models.CharField(max_length=100, blank=True, null=True)
    opmcb = models.CharField(max_length=100, blank=True, null=True)
    sgb = models.CharField(max_length=50, blank=True, null=True)
    garagem = models.CharField(max_length=100, blank=True, null=True)
    
    tipo = models.ForeignKey(Dictionary, on_delete=models.SET_NULL, null=True, related_name='viaturas_por_tipo', limit_choices_to={'tipo': 'TIPO_VIATURA'})
    status_base = models.ForeignKey(Dictionary, on_delete=models.SET_NULL, null=True, related_name='viaturas_por_status', limit_choices_to={'tipo': 'STATUS_VIATURA'})
    posto_base = models.ForeignKey(Posto, on_delete=models.SET_NULL, null=True, related_name='viaturas_base')

    def clean(self):
        # Padroniza SGB (Ex: "1ºSGB" -> "1º SGB", "15]GB" -> "15º GB")
        if self.sgb:
            s_sgb = normalize_text(self.sgb)
            s_sgb = re.sub(r'(\d+)[°º\]]?(S?GB)', r'\1º \2', s_sgb)
            self.sgb = s_sgb

        if self.municipio:
            self.municipio = normalize_text(self.municipio)
        
        # Garante o Default Status para Operando se vazio
        if not self.status_base_id:
            op_status = Dictionary.objects.filter(tipo='STATUS_VIATURA', codigo='OPERANDO').first()
            if op_status:
                self.status_base = op_status
                
        # Extrai o tipo automaticamente a partir do prefixo
        if self.prefixo and not self.tipo_id:
            # Ex: AB-15106 -> AB
            tipo_prefixo = self.prefixo.split('-')[0].upper()
            dict_tipo = Dictionary.objects.filter(tipo='TIPO_VIATURA', codigo=tipo_prefixo).first()
            if dict_tipo:
                self.tipo = dict_tipo

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.prefixo

    class Meta:
        verbose_name = 'Viatura'
        verbose_name_plural = 'Viaturas'
        ordering = ['prefixo']
