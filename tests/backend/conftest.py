import pytest

from rest_framework.test import APIClient
from model_bakery import baker

from backend.models import Category, Contact
from django.contrib.auth import get_user_model
from rest_framework.authtoken.models import Token


@pytest.fixture
def client_not_log():
    return APIClient()


@pytest.fixture
def client_log(user):
    token, _ = Token.objects.get_or_create(user=user)
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION='Token ' + token.key)
    return client


@pytest.fixture
def user():
    User = get_user_model()
    usr, _ = User.objects.get_or_create(email='mail@mail.ru')
    if _:
        usr.name = 'admin'
        usr.is_active = True
        usr.save()
    return usr


@pytest.fixture
def contact_factory():
    def factory(*args, **kwargs):
        return baker.make(Contact, *args, **kwargs)

    return factory
