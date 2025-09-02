from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import cache_page
from django.http import Http404
from django.core.cache import cache
from .models import Client, Message, Mailing, MailingAttempt
from .forms import ClientForm, MessageForm, MailingForm
from .utils import send_mailing


# Кэшируем главную страницу на 15 минут
@cache_page(60 * 15)
@login_required
def dashboard(request):
    user = request.user

    # Получаем только рассылки, связанные с клиентами пользователя
    if user.is_manager:
        mailings = Mailing.objects.all()
        clients = Client.objects.all()
    else:
        # Все клиенты, добавленные пользователем
        clients = Client.objects.filter(created_by=user) if hasattr(user, 'client_set') else Client.objects.none()
        # Все рассылки, использующие этих клиентов
        mailings = Mailing.objects.filter(clients__in=clients).distinct()

    total_mailings = mailings.count()
    active_mailings = mailings.filter(status='started').count()
    unique_clients = clients.count()

    # Статистика по попыткам
    attempts = MailingAttempt.objects.filter(mailing__in=mailings)
    successful_attempts = attempts.filter(status='Успешно').count()
    failed_attempts = attempts.filter(status='Не успешно').count()
    total_messages_sent = attempts.filter(status='Успешно').count()  # Одна попытка = одна рассылка (все получатели)

    # Кэшируем статистику (на 5 минут)
    stats_cache_key = f"user_stats_{user.id}"
    stats = cache.get(stats_cache_key)
    if stats is None:
        stats = {
            'total_mailings': total_mailings,
            'active_mailings': active_mailings,
            'unique_clients': unique_clients,
            'successful_attempts': successful_attempts,
            'failed_attempts': failed_attempts,
            'total_messages_sent': total_messages_sent,
        }
        cache.set(stats_cache_key, stats, 60 * 5)  # 5 минут

    return render(request, 'mailing/dashboard.html', stats)


# --- Универсальная проверка доступа ---
def can_access_mailing(request, mailing):
    if request.user.is_manager:
        return True
    clients = Client.objects.filter(created_by=request.user)
    return mailing.clients.filter(id__in=clients).exists()


# --- Клиенты ---
@login_required
def client_list(request):
    if request.user.is_manager:
        clients = Client.objects.all().order_by('name')
    else:
        clients = Client.objects.filter(created_by=request.user).order_by('name')
    return render(request, 'mailing/client_list.html', {'clients': clients})

@login_required
def client_create(request):
    if request.method == 'POST':
        form = ClientForm(request.POST)
        if form.is_valid():
            client = form.save(commit=False)
            client.created_by = request.user
            client.save()
            messages.success(request, 'Получатель успешно добавлен.')
            return redirect('mailing:client_list')
    else:
        form = ClientForm()
    return render(request, 'mailing/client_form.html', {'form': form, 'title': 'Добавить получателя'})

@login_required
def client_edit(request, pk):
    client = get_object_or_404(Client, pk=pk)
    if not request.user.is_manager and client.created_by != request.user:
        raise Http404("У вас нет прав на редактирование этого клиента.")
    if request.method == 'POST':
        form = ClientForm(request.POST, instance=client)
        if form.is_valid():
            form.save()
            messages.success(request, 'Получатель обновлён.')
            return redirect('mailing:client_list')
    else:
        form = ClientForm(instance=client)
    return render(request, 'mailing/client_form.html', {'form': form, 'title': 'Редактировать получателя'})

@login_required
def client_delete(request, pk):
    client = get_object_or_404(Client, pk=pk)
    if not request.user.is_manager and client.created_by != request.user:
        raise Http404("У вас нет прав на удаление этого клиента.")
    if request.method == 'POST':
        client.delete()
        messages.success(request, 'Получатель удалён.')
        return redirect('mailing:client_list')
    return render(request, 'mailing/client_confirm_delete.html', {'client': client})


# --- Сообщения ---
@login_required
def message_list(request):
    messages = Message.objects.all().order_by('-created_at')
    return render(request, 'mailing/message_list.html', {'messages': messages})

@login_required
def message_create(request):
    if request.method == 'POST':
        form = MessageForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Сообщение создано.')
            return redirect('mailing:message_list')
    else:
        form = MessageForm()
    return render(request, 'mailing/message_form.html', {'form': form, 'title': 'Создать сообщение'})

@login_required
def message_edit(request, pk):
    message = get_object_or_404(Message, pk=pk)
    if request.method == 'POST':
        form = MessageForm(request.POST, instance=message)
        if form.is_valid():
            form.save()
            messages.success(request, 'Сообщение обновлено.')
            return redirect('mailing:message_list')
    else:
        form = MessageForm(instance=message)
    return render(request, 'mailing/message_form.html', {'form': form, 'title': 'Редактировать сообщение'})

@login_required
def message_delete(request, pk):
    message = get_object_or_404(Message, pk=pk)
    if request.method == 'POST':
        message.delete()
        messages.success(request, 'Сообщение удалено.')
        return redirect('mailing:message_list')
    return render(request, 'mailing/message_confirm_delete.html', {'message': message})


# --- Рассылки ---
@login_required
def mailing_list(request):
    if request.user.is_manager:
        mailings = Mailing.objects.all().order_by('-first_send')
    else:
        clients = Client.objects.filter(created_by=request.user)
        mailings = Mailing.objects.filter(clients__in=clients).distinct().order_by('-first_send')
    return render(request, 'mailing/mailing_list.html', {'mailings': mailings})

@login_required
def mailing_create(request):
    if request.method == 'POST':
        form = MailingForm(request.POST)
        if form.is_valid():
            mailing = form.save()
            messages.success(request, 'Рассылка создана.')
            return redirect('mailing:mailing_list')
    else:
        form = MailingForm()
    return render(request, 'mailing/mailing_form.html', {'form': form, 'title': 'Создать рассылку'})

@login_required
def mailing_edit(request, pk):
    mailing = get_object_or_404(Mailing, pk=pk)
    if not can_access_mailing(request, mailing):
        raise Http404("У вас нет прав на редактирование этой рассылки.")
    if mailing.status != 'created':
        messages.warning(request, 'Редактировать можно только рассылки со статусом "Создана".')
        return redirect('mailing:mailing_list')
    if request.method == 'POST':
        form = MailingForm(request.POST, instance=mailing)
        if form.is_valid():
            form.save()
            messages.success(request, 'Рассылка обновлена.')
            return redirect('mailing:mailing_list')
    else:
        form = MailingForm(instance=mailing)
    return render(request, 'mailing/mailing_form.html', {'form': form, 'title': 'Редактировать рассылку'})

@login_required
def mailing_delete(request, pk):
    mailing = get_object_or_404(Mailing, pk=pk)
    if not can_access_mailing(request, mailing):
        raise Http404("У вас нет прав на удаление этой рассылки.")
    if request.method == 'POST':
        mailing.delete()
        messages.success(request, 'Рассылка удалена.')
        return redirect('mailing:mailing_list')
    return render(request, 'mailing/mailing_confirm_delete.html', {'mailing': mailing})

@login_required
def mailing_send_now(request, pk):
    mailing = get_object_or_404(Mailing, pk=pk)
    if not can_access_mailing(request, mailing):
        raise Http404("У вас нет прав на отправку этой рассылки.")
    send_mailing(mailing.id)
    messages.success(request, f'Рассылка #{mailing.id} отправлена.')
    return redirect('mailing:mailing_list')

@login_required
def mailing_detail(request, pk):
    mailing = get_object_or_404(Mailing, pk=pk)
    if not can_access_mailing(request, mailing):
        raise Http404("У вас нет прав на просмотр этой рассылки.")
    attempts = MailingAttempt.objects.filter(mailing=mailing).order_by('-attempt_time')
    return render(request, 'mailing/mailing_detail.html', {
        'mailing': mailing,
        'attempts': attempts
    })
