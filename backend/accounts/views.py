from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib import messages
from .models import User
from escalas.models import MapaDiario, HistoricoAlteracao
from unidades.models import Unidade, Viatura
from django.db.models import Count, Q
from allauth.socialaccount.models import SocialAccount

@login_required
def profile_view(request):
    is_social = SocialAccount.objects.filter(user=request.user).exists()
    todas_unidades = Unidade.objects.all().order_by('nome')
    
    if request.method == 'POST':
        # Caso 1: Troca de Senha (apenas admin local)
        if 'change_password' in request.POST and not is_social:
            form = PasswordChangeForm(request.user, request.POST)
            if form.is_valid():
                user = form.save()
                update_session_auth_hash(request, user)
                messages.success(request, 'Sua senha foi alterada com sucesso!')
                return redirect('profile')
            else:
                messages.error(request, 'Erro ao alterar senha.')
        
        # Caso 2: Solicitação de Vínculo
        elif 'request_link' in request.POST:
            role = request.POST.get('requested_role')
            unidades_ids = request.POST.getlist('requested_unidades')
            
            request.user.requested_role = role
            request.user.is_link_pending = True
            request.user.save()
            request.user.requested_unidades.set(unidades_ids)
            
            messages.info(request, 'Sua solicitação de vínculo foi enviada para auditoria.')
            return redirect('profile')

    form = PasswordChangeForm(request.user) if not is_social else None
    
    context = {
        'form': form,
        'user': request.user,
        'is_social': is_social,
        'unidades': todas_unidades,
        'role_choices': User.ROLE_CHOICES,
    }
    return render(request, 'account/profile.html', context)

@login_required
@user_passes_test(lambda u: u.is_superuser or u.role == 'ADMIN')
def admin_dashboard_view(request):
    """Painel de Gestão restrito a Administradores."""
    total_usuarios = User.objects.count()
    total_mapas_hoje = MapaDiario.objects.count()
    total_viaturas = Viatura.objects.count()

    # Todos os usuários para a listagem completa
    all_users = User.objects.all().order_by('-date_joined')

    # Novos usuários (Google) inativos
    pending_users = User.objects.filter(is_active=False).order_by('-date_joined')

    # Usuários com solicitação de vínculo pendente
    pending_links = User.objects.filter(is_link_pending=True).prefetch_related('requested_unidades')

    recent_activities = HistoricoAlteracao.objects.select_related('usuario', 'mapa__unidade').order_by('-data_hora')[:10]

    context = {
        'total_usuarios': total_usuarios,
        'total_mapas_hoje': total_mapas_hoje,
        'total_viaturas': total_viaturas,
        'all_users': all_users,
        'pending_users': pending_users,
        'pending_links': pending_links,
        'recent_activities': recent_activities,
    }
    return render(request, 'accounts/admin_dashboard.html', context)

@login_required
@user_passes_test(lambda u: u.is_superuser or u.role == 'ADMIN')
def approve_user_view(request, user_id):
    user_to_approve = get_object_or_404(User, id=user_id)
    user_to_approve.is_active = True
    user_to_approve.save()
    messages.success(request, f"Usuário {user_to_approve.email} aprovado com sucesso!")
    return redirect('admin_dashboard')

@login_required
@user_passes_test(lambda u: u.is_superuser or u.role == 'ADMIN')
def approve_link_view(request, user_id):
    u = get_object_or_404(User, id=user_id)
    # Efetiva o cargo
    u.role = u.requested_role
    # Efetiva a primeira unidade como principal (ForeignKey)
    primeira_unidade = u.requested_unidades.first()
    if primeira_unidade:
        u.unidade = primeira_unidade
    
    u.is_link_pending = False
    u.save()
    
    messages.success(request, f"Vínculo de {u.email} aprovado e atualizado!")
    return redirect('admin_dashboard')

def account_inactive_view(request):
    return render(request, 'account/account_inactive.html')
