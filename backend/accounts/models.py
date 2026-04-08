from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from unidades.models import Unidade

class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('O campo Email deve ser definido')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('role', 'ADMIN')
        return self.create_user(email, password, **extra_fields)

class User(AbstractUser):
    ROLE_CHOICES = (
        ('ADMIN', 'Administrador'),
        ('POSTO', 'Operador de Posto'),
        ('BATALHAO', 'Operador de Batalhão'),
        ('GRANDE_COMANDO', 'Grande Comando'),
        ('CENTRAL', 'Central de Controle'),
    )

    username = None
    email = models.EmailField(unique=True)
    
    role = models.CharField(
        max_length=20, 
        choices=ROLE_CHOICES, 
        default='POSTO'
    )
    
    unidade = models.ForeignKey(
        Unidade, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='usuarios',
        help_text='Unidade à qual este usuário pertence'
    )
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    objects = UserManager()

    def __str__(self):
        return f"{self.email} ({self.get_role_display()})"

    @property
    def is_posto(self):
        return self.role == 'POSTO'

    @property
    def is_batalhao(self):
        return self.role == 'BATALHAO'

    @property
    def is_admin(self):
        return self.role == 'ADMIN' or self.is_superuser
