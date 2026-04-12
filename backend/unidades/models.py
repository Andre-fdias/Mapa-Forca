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

class Unidade(models.Model):
    """
    Representa qualquer unidade da corporação: Grande Comando, Batalhão ou Posto.
    Suporta hierarquia recursiva.
    """
    nome = models.CharField(max_length=100, unique=True)
    parent = models.ForeignKey(
        'self', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='subunidades',
        help_text='Unidade superior (ex: Batalhão para um Posto)'
    )
    
    # Níveis: GRANDE_COMANDO, BATALHAO, POSTO, CENTRAL
    tipo_unidade = models.ForeignKey(
        Dictionary, 
        on_delete=models.SET_NULL, 
        null=True, 
        related_name='unidades_por_nivel', 
        limit_choices_to={'tipo': 'TIPO_UNIDADE'}
    )
    
    # Campo para manter compatibilidade com a lógica anterior (tipo funcional: EB, ADM, etc)
    tipo_servico = models.ForeignKey(
        Dictionary, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='unidades_por_servico', 
        limit_choices_to={'tipo': 'TIPO_POSTO'}
    )

    mapa_sgb = models.CharField(max_length=50, blank=True, null=True)
    codigo_secao = models.CharField(max_length=50, unique=True, null=True)
    descricao = models.CharField(max_length=255, blank=True, null=True)
    telefone = models.CharField(max_length=20, blank=True, null=True)
    ativo = models.BooleanField(default=True)

    def __str__(self):
        return self.nome

    @property
    def root_unit(self):
        """Sobe na hierarquia até encontrar a unidade raiz (Grupamento)."""
        curr = self
        while curr.parent:
            curr = curr.parent
        return curr

    def clean(self):
        # Auto-determina o tipo de serviço através da descrição (lógica legada)
        if self.descricao and not self.tipo_servico_id:
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
                    self.tipo_servico = dict_tipo

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = 'Unidade'
        verbose_name_plural = 'Unidades'
        ordering = ['nome']

class Viatura(models.Model):
    prefixo = models.CharField(max_length=20, primary_key=True)
    placa = models.CharField(max_length=20, null=True, blank=True)
    municipio = models.CharField(max_length=100, blank=True, null=True)
    opmcb = models.CharField(max_length=100, blank=True, null=True)
    sgb = models.CharField(max_length=50, blank=True, null=True)
    garagem = models.CharField(max_length=100, blank=True, null=True)
    vol_agua = models.CharField(max_length=50, blank=True, null=True, verbose_name="Volume de Água")
    combustivel = models.CharField(max_length=100, blank=True, null=True)
    
    tipo = models.ForeignKey(
        Dictionary, 
        on_delete=models.SET_NULL, 
        null=True, 
        related_name='viaturas_por_tipo', 
        limit_choices_to={'tipo': 'TIPO_VIATURA'}
    )
    status_base = models.ForeignKey(
        Dictionary, 
        on_delete=models.SET_NULL, 
        null=True, 
        related_name='viaturas_por_status', 
        limit_choices_to={'tipo': 'STATUS_VIATURA'}
    )
    unidade_base = models.ForeignKey(
        Unidade, 
        on_delete=models.SET_NULL, 
        null=True, 
        related_name='viaturas_base'
    )
    fonte = models.CharField(max_length=100, default="Local", help_text="Origem do dado: Local ou Google Sheets")

    def clean(self):
        if self.sgb:
            s_sgb = normalize_text(self.sgb)
            s_sgb = re.sub(r'(\d+)[°º\]]?(S?GB)', r'\1º \2', s_sgb)
            self.sgb = s_sgb

        if self.municipio:
            self.municipio = normalize_text(self.municipio)
        
        if not self.status_base_id:
            op_status = Dictionary.objects.filter(tipo='STATUS_VIATURA', codigo='OPERANDO').first()
            if op_status:
                self.status_base = op_status
                
        if self.prefixo and not self.tipo_id:
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

class Municipio(models.Model):
    id_cidade = models.CharField(max_length=50, null=True, blank=True)
    nome = models.CharField(max_length=255, unique=True)
    tipo_cidade = models.CharField(max_length=100, null=True, blank=True)
    area_km2 = models.DecimalField(max_digits=15, decimal_places=3, null=True, blank=True)
    populacao = models.IntegerField(null=True, blank=True)
    hab_km2 = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    email = models.EmailField(max_length=255, null=True, blank=True)
    bandeira = models.CharField(max_length=255, null=True, blank=True)
    codigo = models.CharField(max_length=50, null=True, blank=True)
    fonte = models.CharField(max_length=100, default='Google Sheets')

    def __str__(self):
        return self.nome

    class Meta:
        verbose_name = 'Município'
        verbose_name_plural = 'Municípios'
        ordering = ['nome']

class Posto(models.Model):
    nome = models.CharField(max_length=255, unique=True)
    sgb = models.CharField(max_length=100, null=True, blank=True)
    cod_secao = models.CharField(max_length=100, null=True, blank=True)
    cidade_posto = models.CharField(max_length=255, null=True, blank=True)
    operacional_adm = models.CharField(max_length=100, null=True, blank=True)
    endereco_quarte = models.CharField(max_length=255, null=True, blank=True)
    telefone = models.CharField(max_length=100, null=True, blank=True)
    municipios = models.ManyToManyField(Municipio, related_name='postos')
    fonte = models.CharField(max_length=100, default='Google Sheets')

    @property
    def num_municipios(self):
        return self.municipios.count()

    def __str__(self):
        return self.nome

    class Meta:
        verbose_name = 'Posto'
        verbose_name_plural = 'Postos'
        ordering = ['nome']
