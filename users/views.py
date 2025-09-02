from django.contrib.auth.decorators import user_passes_test
from django.shortcuts import get_object_or_404, redirect

from users.models import User


@user_passes_test(lambda u: u.is_manager)
def block_user(request, user_id):
    user = get_object_or_404(User, id=user_id)
    user.is_active = False
    user.save()
    return redirect('user_list')
