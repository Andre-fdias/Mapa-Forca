from django.db.models import Q
from unidades.models import Unidade

class RBACQuerysetMixin:
    """
    Mixin para class-based views do Django, reescrevendo o get_queryset() 
    para forçar o escaneamento hierárquico com base na role do usuário (ADMIN, COBOM, GB, SGB, POSTO).
    Espera que a View possua um atributo `unidade_field`, indicando qual a FK de Unidade que deve ser filtrada no Model alvo.
    """
    unidade_field = 'unidade' # default: model tem um campo chamado 'unidade'

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        
        # Filtro ZERO para Admins e COBOM, porém COBOM só poderá fazer Leitura depois (em permissão de Action)
        if user.role in ['ADMIN', 'COBOM'] or user.is_superuser:
            return qs

        if getattr(user, 'unidade', None) is None:
            return qs.none() # Sem unidade definida, sem acesso.
            
        unidade_field_kwarg = f"{self.unidade_field}__in"

        if user.role == 'BATALHAO' or user.role == 'GB':
            # GB pode ver qualquer unidade cuja origin (root) seja igual a ele
            # Buscando todos os descendentes
            descendentes = Unidade.objects.filter(Q(id=user.unidade.id) | Q(parent=user.unidade) | Q(parent__parent=user.unidade)).values_list('id', flat=True)
            return qs.filter(**{unidade_field_kwarg: descendentes})
            
        elif user.role == 'SGB':
            # SGB pode ver a si mesmo e aos Postos abaixo dele
            descendentes = Unidade.objects.filter(Q(id=user.unidade.id) | Q(parent=user.unidade)).values_list('id', flat=True)
            return qs.filter(**{unidade_field_kwarg: descendentes})
            
        elif user.role == 'POSTO':
            # Posto vê estritamente e somente ele
            return qs.filter(**{f"{self.unidade_field}": user.unidade})
            
        return qs.none()
