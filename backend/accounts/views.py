from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib import messages
from .models import User
from escalas.models import MapaDiario, HistoricoAlteracao
from unidades.models import Unidade, Viatura, Posto
from django.db.models import Count, Q
from allauth.socialaccount.models import SocialAccount
from django.http import HttpResponse
import re

@login_required
def profile_view(request):
    is_social = SocialAccount.objects.filter(user=request.user).exists()
    todas_unidades = Unidade.objects.all().order_by('nome')
    
    if request.method == 'POST':
        if 'change_password' in request.POST and not is_social:
            form = PasswordChangeForm(request.user, request.POST)
            if form.is_valid():
                user = form.save()
                update_session_auth_hash(request, user)
                messages.success(request, 'Sua senha foi alterada com sucesso!')
                return redirect('profile')
            else:
                messages.error(request, 'Erro ao alterar senha.')
        elif 'request_link' in request.POST:
            unidades_ids = request.POST.getlist('requested_unidades')
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
    total_usuarios = User.objects.exclude(status='rejected').count()
    total_mapas_hoje = MapaDiario.objects.count()
    total_viaturas = Viatura.objects.count()
    all_users = User.objects.all().order_by('-date_joined')
    pending_users = User.objects.filter(status='pending').order_by('-date_joined')
    recent_activities = HistoricoAlteracao.objects.select_related('usuario', 'mapa__unidade').order_by('-data_hora')[:10]

    context = {
        'total_usuarios': total_usuarios,
        'total_mapas_hoje': total_mapas_hoje,
        'total_viaturas': total_viaturas,
        'all_users': all_users,
        'pending_users': pending_users,
        'recent_activities': recent_activities,
    }
    return render(request, 'accounts/admin_dashboard.html', context)

@login_required
@user_passes_test(lambda u: u.is_superuser or u.role == 'ADMIN')
def approve_user_view(request, user_id):
    user_to_approve = get_object_or_404(User, id=user_id)
    user_to_approve.status = 'approved'
    user_to_approve.is_active = True
    user_to_approve.save()
    messages.success(request, f"Usuário {user_to_approve.email} aprovado com sucesso!")
    return redirect('admin_dashboard')

@login_required
@user_passes_test(lambda u: u.is_superuser or u.role == 'ADMIN')
def reject_user_view(request, user_id):
    u = get_object_or_404(User, id=user_id)
    if not u.is_superuser:
        u.status = 'rejected'
        u.save()
        messages.success(request, "Usuário rejeitado.")
    return redirect('admin_dashboard')

@login_required
def waiting_approval_view(request):
    """Estágio 3: Aguardando aprovação."""
    if request.user.role == 'ADMIN' or request.user.is_superuser:
        if request.user.status == 'pending':
            request.user.status = 'approved'
            request.user.save()
        return redirect('admin_dashboard')

    if request.user.status == 'approved':
        return redirect('index')
    return render(request, 'accounts/waiting_approval.html')

@login_required
def request_access_view(request):
    """Estágio 2: Formulário encadeado para escolher Batalhão > SGB > Posto."""
    if request.user.role == 'ADMIN' or request.user.is_superuser:
        if request.user.status == 'pending':
            request.user.status = 'approved'
            request.user.save()
        return redirect('admin_dashboard')

    if request.user.unidade and request.user.status != 'pending':
        return redirect('index')

    if request.method == 'POST':
        posto_id = request.POST.get('posto_id')
        sgb_id = request.POST.get('sgb_id')
        batalhao_id = request.POST.get('batalhao_id')
        role = 'POSTO' # Default for all new access requests
        
        unidade_final = None
        if posto_id:
            # We fetch the exact Posto which has all text fields
            posto_obj = get_object_or_404(Posto, id=posto_id)
            
            # Auto-build the Unidade tree if it doesn't exist
            # Important: Unidade.nome is unique=True globally! We must construct unique names for SGBs.
            gb_unidade, _ = Unidade.objects.get_or_create(nome=posto_obj.unidade, defaults={'parent': None})
            
            sgb_name = f"{posto_obj.sgb} - {posto_obj.unidade}" if posto_obj.sgb else f"SGB Padrão - {posto_obj.unidade}"
            sgb_unidade, _ = Unidade.objects.get_or_create(nome=sgb_name, defaults={'parent': gb_unidade})
            
            posto_unidade, _ = Unidade.objects.get_or_create(nome=posto_obj.nome, defaults={'parent': sgb_unidade})
            
            unidade_final = posto_unidade

        if unidade_final and role:
            request.user.unidade = unidade_final
            request.user.role = role
            request.user.status = 'pending'
            request.user.save()
            return redirect('waiting_approval')

    batalhoes = Posto.objects.values_list('unidade', flat=True).exclude(unidade__isnull=True).exclude(unidade='').distinct().order_by('unidade')
    return render(request, 'accounts/request_access.html', {
        'batalhoes': batalhoes, 
        'role_choices': User.ROLE_CHOICES
    })

@login_required
def get_sgbs_htmx(request):
    batalhao_nome = request.GET.get('batalhao_id')
    if not batalhao_nome:
        return HttpResponse('<option value="">Selecione o Batalhão primeiro</option>')
        
    sgbs = Posto.objects.filter(unidade=batalhao_nome).values_list('sgb', flat=True).exclude(sgb__isnull=True).exclude(sgb='').distinct().order_by('sgb')
    options = '<option value="">(Opcional) Selecione o SGB</option>'
    for sgb in sgbs:
        options += f'<option value="{sgb}">{sgb}</option>'
    return HttpResponse(options)

@login_required
def get_postos_htmx(request):
    batalhao_nome = request.GET.get('batalhao_id')
    sgb_nome = request.GET.get('sgb_id')
    if not sgb_nome or not batalhao_nome:
        return HttpResponse('<option value="">Selecione o SGB primeiro</option>')
        
    postos = Posto.objects.filter(unidade=batalhao_nome, sgb=sgb_nome).order_by('nome')
    options = '<option value="">(Opcional) Selecione o Posto</option>'
    for posto in postos:
        options += f'<option value="{posto.id}">{posto.nome}</option>'
    return HttpResponse(options)

@login_required
@user_passes_test(lambda u: u.role == 'ADMIN' or u.is_superuser)
def update_user_role_view(request, user_id):
    if request.method == 'POST':
        user = get_object_or_404(User, id=user_id)
        new_role = request.POST.get('role')
        if new_role in dict(User.ROLE_CHOICES).keys():
            user.role = new_role
            user.save()
            return HttpResponse(f'<span class="text-emerald-600 font-bold text-xs uppercase">✓ Atualizado</span>')
    return HttpResponse(status=400)
