from allauth.socialaccount.signals import pre_social_login
from django.dispatch import receiver


@receiver(pre_social_login)
def pre_social_login(**kwargs):
    kwargs['sociallogin'].user.is_active = True
    return kwargs

