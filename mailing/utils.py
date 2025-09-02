from django.core.mail import send_mail
from .models import MailingAttempt, Mailing
from django.conf import settings
from django.utils import timezone

def send_mailing(mailing_id):
    """
    Отправка рассылки по ID.
    Вызывается вручную через интерфейс или команду.
    """
    try:
        mailing = Mailing.objects.get(id=mailing_id)
        recipients = [client.email for client in mailing.clients.all()]
        message = mailing.message

        if not recipients:
            MailingAttempt.objects.create(
                mailing=mailing,
                status=MailingAttempt.STATUS_FAILED,
                server_response="Нет получателей."
            )
            return

        # Отправка письма
        count = send_mail(
            subject=message.subject,
            message=message.body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=recipients,
            fail_silently=False,
        )

        # Успешная попытка
        MailingAttempt.objects.create(
            mailing=mailing,
            status=MailingAttempt.STATUS_SUCCESS,
            server_response=f"Отправлено {count} писем."
        )

        # Обновление статуса рассылки
        if mailing.status == 'created':
            mailing.status = 'started'
        mailing.last_send = timezone.now()
        mailing.save()

    except Exception as e:
        # Ошибка отправки
        MailingAttempt.objects.create(
            mailing=mailing,
            status=MailingAttempt.STATUS_FAILED,
            server_response=str(e)
        )
        mailing.status = 'failed'  # Можно добавить статус 'failed', но по ТЗ — только 3
        mailing.save()
