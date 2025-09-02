from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from .models import Client, Message, Mailing, MailingAttempt
from .forms import ClientForm, MessageForm, MailingForm
from .utils import send_mailing

def dashboard(request):
    total_mailings = Mailing.objects.count()
    active_mailings = Mailing.objects.filter(status='started').count()
    unique_clients = Client.objects.count()

    context = {
        'total_mailings': total_mailings,
        'active_mailings': active_mailings,
        'unique_clients': unique_clients,
    }
    return render(request, 'mailing/dashboard.html', context)


def client_list(request):
    clients = Client.objects.all().order_by('name')
    return render(request, 'mailing/client_list.html', {'clients': clients})

def client_create(request):
    if request.method == 'POST':
        form = ClientForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Получатель успешно добавлен.')
            return redirect('client_list')
    else:
        form = ClientForm()
    return render(request, 'mailing/client_form.html', {'form': form, 'title': 'Добавить получателя'})

def client_edit(request, pk):
    client = get_object_or_404(Client, pk=pk)
    if request.method == 'POST':
        form = ClientForm(request.POST, instance=client)
        if form.is_valid():
            form.save()
            messages.success(request, 'Получатель обновлён.')
            return redirect('client_list')
    else:
        form = ClientForm(instance=client)
    return render(request, 'mailing/client_form.html', {'form': form, 'title': 'Редактировать получателя'})

def client_delete(request, pk):
    client = get_object_or_404(Client, pk=pk)
    if request.method == 'POST':
        client.delete()
        messages.success(request, 'Получатель удалён.')
        return redirect('client_list')
    return render(request, 'mailing/client_confirm_delete.html', {'client': client})


# --- Сообщения ---
def message_list(request):
    messages = Message.objects.all().order_by('-created_at')
    return render(request, 'mailing/message_list.html', {'messages': messages})

def message_create(request):
    if request.method == 'POST':
        form = MessageForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Сообщение создано.')
            return redirect('message_list')
    else:
        form = MessageForm()
    return render(request, 'mailing/message_form.html', {'form': form, 'title': 'Создать сообщение'})

def message_edit(request, pk):
    message = get_object_or_404(Message, pk=pk)
    if request.method == 'POST':
        form = MessageForm(request.POST, instance=message)
        if form.is_valid():
            form.save()
            messages.success(request, 'Сообщение обновлено.')
            return redirect('message_list')
    else:
        form = MessageForm(instance=message)
    return render(request, 'mailing/message_form.html', {'form': form, 'title': 'Редактировать сообщение'})

def message_delete(request, pk):
    message = get_object_or_404(Message, pk=pk)
    if request.method == 'POST':
        message.delete()
        messages.success(request, 'Сообщение удалено.')
        return redirect('message_list')
    return render(request, 'mailing/message_confirm_delete.html', {'message': message})


# --- Рассылки ---
def mailing_list(request):
    mailings = Mailing.objects.all().order_by('-first_send')
    return render(request, 'mailing/mailing_list.html', {'mailings': mailings})

def mailing_create(request):
    if request.method == 'POST':
        form = MailingForm(request.POST)
        if form.is_valid():
            mailing = form.save()
            messages.success(request, 'Рассылка создана.')
            return redirect('mailing_list')
    else:
        form = MailingForm()
    return render(request, 'mailing/mailing_form.html', {'form': form, 'title': 'Создать рассылку'})

def mailing_edit(request, pk):
    mailing = get_object_or_404(Mailing, pk=pk)
    if mailing.status != 'created':
        messages.warning(request, 'Редактировать можно только рассылки со статусом "Создана".')
        return redirect('mailing_list')

    if request.method == 'POST':
        form = MailingForm(request.POST, instance=mailing)
        if form.is_valid():
            form.save()
            messages.success(request, 'Рассылка обновлена.')
            return redirect('mailing_list')
    else:
        form = MailingForm(instance=mailing)
    return render(request, 'mailing/mailing_form.html', {'form': form, 'title': 'Редактировать рассылку'})

def mailing_delete(request, pk):
    mailing = get_object_or_404(Mailing, pk=pk)
    if request.method == 'POST':
        mailing.delete()
        messages.success(request, 'Рассылка удалена.')
        return redirect('mailing_list')
    return render(request, 'mailing/mailing_confirm_delete.html', {'mailing': mailing})

def mailing_send_now(request, pk):
    mailing = get_object_or_404(Mailing, pk=pk)
    send_mailing(mailing.id)
    messages.success(request, f'Рассылка #{mailing.id} отправлена.')
    return redirect('mailing_list')

def mailing_detail(request, pk):
    mailing = get_object_or_404(Mailing, pk=pk)
    attempts = MailingAttempt.objects.filter(mailing=mailing).order_by('-attempt_time')
    return render(request, 'mailing/mailing_detail.html', {
        'mailing': mailing,
        'attempts': attempts
    })
