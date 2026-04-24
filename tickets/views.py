from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Ticket, TicketMessage
from django.db.models import Q

@login_required
def ticket_list_view(request):
    """Lista os chamados (seus próprios ou todos se for Admin/COBOM)."""
    user = request.user
    is_support_team = user.is_superuser or user.role in ['ADMIN', 'COBOM']
    
    if is_support_team:
        tickets = Ticket.objects.all()
    else:
        tickets = Ticket.objects.filter(requisitante=user)
    
    # Filtros simples
    status_filter = request.GET.get('status')
    if status_filter:
        tickets = tickets.filter(status=status_filter)
        
    return render(request, 'tickets/lista_tickets.html', {
        'tickets': tickets,
        'is_support_team': is_support_team,
        'status_filter': status_filter
    })

@login_required
def ticket_create_view(request):
    """Abre um novo chamado com assunto padronizado."""
    if request.method == 'POST':
        titulo = request.POST.get('titulo')
        descricao = request.POST.get('descricao')
        
        ticket = Ticket.objects.create(
            requisitante=request.user,
            titulo=titulo,
            descricao=descricao,
            lido_pelo_suporte=False, # Novo chamado: suporte precisa ver
            lido_pelo_requisitante=True # O user acabou de criar
        )
        messages.success(request, f"Chamado #{ticket.protocolo} aberto com sucesso! Prioridade: {ticket.get_prioridade_display()}")
        return redirect('tickets:ticket_detail', pk=ticket.id)
        
    return render(request, 'tickets/novo_ticket.html', {
        'assuntos': Ticket.ASSUNTO_CHOICES
    })

@login_required
def ticket_detail_view(request, pk):
    """Detalhes do chamado e histórico de mensagens."""
    user = request.user
    is_support_team = user.is_superuser or user.role in ['ADMIN', 'COBOM']
    
    if is_support_team:
        ticket = get_object_or_404(Ticket, pk=pk)
        # Ao suporte abrir o detalhe, marca como lido por ele
        if not ticket.lido_pelo_suporte:
            ticket.lido_pelo_suporte = True
            ticket.save()
    else:
        ticket = get_object_or_404(Ticket, pk=pk, requisitante=user)
        # Ao user abrir o detalhe, marca como lido por ele
        if not ticket.lido_pelo_requisitante:
            ticket.lido_pelo_requisitante = True
            ticket.save()
        
    if request.method == 'POST':
        # Adicionar mensagem
        mensagem_texto = request.POST.get('mensagem')
        if mensagem_texto:
            TicketMessage.objects.create(
                ticket=ticket,
                autor=user,
                mensagem=mensagem_texto
            )
            
            # Ajuste de flags de notificação
            if is_support_team:
                ticket.lido_pelo_requisitante = False # Requisitante precisa ver resposta
                # Se o suporte respondeu, muda status para EM_ANDAMENTO
                if ticket.status == 'ABERTO':
                    ticket.status = 'EM_ANDAMENTO'
            else:
                ticket.lido_pelo_suporte = False # Suporte precisa ver resposta do user
                
            ticket.save()
                
            messages.success(request, "Mensagem enviada.")
            return redirect('tickets:ticket_detail', pk=ticket.id)
            
    return render(request, 'tickets/detalhe_ticket.html', {
        'ticket': ticket,
        'is_support_team': is_support_team
    })

@login_required
def ticket_update_status(request, pk):
    """Ação rápida para mudar o status (Apenas suporte)."""
    user = request.user
    if not (user.is_superuser or user.role in ['ADMIN', 'COBOM']):
        return redirect('tickets:ticket_list')
        
    ticket = get_object_or_404(Ticket, pk=pk)
    new_status = request.POST.get('status')
    if new_status in dict(Ticket.STATUS_CHOICES):
        ticket.status = new_status
        ticket.lido_pelo_requisitante = False # Status mudou, avisa o user
        ticket.save()
        messages.success(request, f"Status do chamado #{ticket.id} atualizado para {ticket.get_status_display()}.")
        
    return redirect('tickets:ticket_detail', pk=ticket.id)
