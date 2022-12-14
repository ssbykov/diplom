import pytest

from rest_framework.test import APIClient
from model_bakery import baker

from backend.models import Category, Contact, Shop
from django.contrib.auth import get_user_model
from rest_framework.authtoken.models import Token

user_shop = {
    'username': 'shop',
    'email': 'shop@mail.ru',
    'type': 'shop',
    'is_active': True
}

user_buyer = {
    'username': 'buyer',
    'email': 'buyer@mail.ru',
    'type': 'buyer',
    'is_active': True
}


@pytest.fixture
@pytest.mark.django_db
def client_shop(client_log):
    return client_log(**user_shop)


@pytest.fixture
def client_not_log():
    return APIClient()


@pytest.fixture
def client_log(user, client_not_log):
    def make_client(**kwargs):
        if kwargs:
            usr = user(**kwargs)
            token, _ = Token.objects.get_or_create(user=usr)
            client = APIClient()
            client.credentials(HTTP_AUTHORIZATION='Token ' + token.key)
            return client
        else:
            return client_not_log

    return make_client


@pytest.fixture
def user_model():
    return get_user_model()


@pytest.fixture
def user(user_model):
    def make_user(**kwargs):
        return user_model.objects.get_or_create(**kwargs)[0]

    return make_user


@pytest.fixture
def contact_factory():
    def factory(*args, **kwargs):
        return baker.make(Contact, *args, **kwargs)

    return factory


@pytest.fixture
def shop_factory():
    def factory(*args, **kwargs):
        return baker.make(Shop, *args, **kwargs)

    return factory


@pytest.fixture
def category_factory():
    def factory(*args, **kwargs):
        return baker.make(Category, *args, **kwargs)

    return factory

# @pytest.fixture(scope='session')
# def celery_config():
#     return {
#         'broker_url': 'amqp://',
#         'result_backend': 'redis://'
#     }
