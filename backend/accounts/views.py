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
    total_usuarios = User.objects.count()
    total_mapas_hoje = MapaDiario.objects.count()
    total_viaturas = Viatura.objects.count()
    all_users = User.objects.all().order_by('-date_joined')
    pending_users = User.objects.filter(is_active=False).order_by('-date_joined')
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
    user_to_approve.is_active = True
    user_to_approve.save()
    messages.success(request, f"Usuário {user_to_approve.email} aprovado com sucesso!")
    return redirect('admin_dashboard')

@login_required
@user_passes_test(lambda u: u.is_superuser or u.role == 'ADMIN')
def delete_user_view(request, user_id):
    u = get_object_or_404(User, id=user_id)
    if not u.is_superuser:
        u.delete()
        messages.success(request, "Usuário removido.")
    return redirect('admin_dashboard')

def account_inactive_view(request):
    if request.user.is_authenticated and request.user.is_active:
        return redirect('setup_profile')
    return render(request, 'account/account_inactive.html')

@login_required
def setup_profile(request):
    """Estágio 2: Escolha de Unidade após aprovação."""
    if request.user.unidade and not request.user.is_superuser:
        return redirect('home')

    if request.method == 'POST':
        grupamento_nome = request.POST.get('grupamento_nome')
        posto_id = request.POST.get('posto_id')
        
        unidade_final = None
        if posto_id and posto_id != 'ROOT':
            unidade_final = get_object_or_404(Unidade, id=posto_id)
        else:
            # Busca ou cria a unidade raiz para o vínculo
            match = re.search(r'(\d+)', grupamento_nome)
            g_num = match.group(1) if match else grupamento_nome
            unidade_final, _ = Unidade.objects.get_or_create(nome__icontains=g_num, parent__isnull=True, defaults={'nome': grupamento_nome})

        if unidade_final:
            request.user.unidade = unidade_final
            # Define papel automático: CBI/COBOM = ADMIN, outros = POSTO
            if 'CBI' in unidade_final.nome.upper() or 'COBOM' in unidade_final.nome.upper():
                request.user.role = 'ADMIN'
            else:
                request.user.role = 'POSTO'
            request.user.save()
            return redirect('home')

    opcoes_grupamentos = ['CBI-1', 'COBOM', '07 Grupamento de bombeiros', '15º Grupamento de bombeiros', '16º Grupamento de bombeiros', '19º Grupamento de bombeiros']
    return render(request, 'accounts/setup_profile.html', {'grupamentos': opcoes_grupamentos})

@login_required
def get_postos_unidade(request):
    """Retorna os postos reais para o 15º GB ou opção de comando para outros."""
    g_nome = request.GET.get('grupamento_nome')
    if not g_nome:
        return HttpResponse('<option value="">Selecione o Grupamento</option>')
    
    # Identifica se é o 15º GB
    if "15" in g_nome:
        unidade_raiz = Unidade.objects.filter(nome__icontains='15', parent__isnull=True).first()
        if unidade_raiz:
            sgbs = Unidade.objects.filter(parent=unidade_raiz).order_by('nome')
            options = '<option value="">Selecione o Posto Operacional</option>'
            
            for sgb in sgbs:
                options += f'<optgroup label="{sgb.nome}">'
                # Busca postos (netos)
                postos = Unidade.objects.filter(parent=sgb).order_by('nome')
                for p in postos:
                    options += f'<option value="{p.id}">{p.nome}</option>'
                # Inclui o próprio SGB como opção
                options += f'<option value="{sgb.id}">-- Comando do {sgb.nome} --</option>'
                options += '</optgroup>'
            return HttpResponse(options)
    
    # Para outras unidades (07, 16, 19, CBI, COBOM)
    options = f'<option value="ROOT">Vincular ao Comando do {g_nome}</option>'
    return HttpResponse(options)
