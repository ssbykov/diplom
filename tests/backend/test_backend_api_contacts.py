import pytest
from django.urls import reverse_lazy
from tests.backend.conftest import user_shop, user_buyer


class TestContacts:
    URL = reverse_lazy('backend:ContactView-list')
    testdata = [
        (None, None, None, (400, 400)),
        (None, 'street', None, (400, 400)),
        ('city', None, None, (400, 400)),
        ('city', 'street', None, (400, 400)),
        (None, 'street', 'phone', (400, 400)),
        ('city', None, 'phone', (400, 400)),
        (None, None, 'phone', (400, 400)),
        ('city', 'street', 'phone', (200, 201))
    ]

    user_shop = dict(user_shop)
    user_buyer = dict(user_buyer)

    @pytest.fixture
    @pytest.mark.django_db
    def contact_data(self, contact_factory, user):
        def make_contacts(**kwargs):
            usr = user(**kwargs)
            return contact_factory(_quantity=4, user=usr)

        return make_contacts

    @pytest.fixture
    @pytest.mark.django_db
    def contact_data_shop(self, contact_data):
        return contact_data(**self.user_shop)

    # тест получания контактов по пользователю (магазину)
    @pytest.mark.django_db
    def test_get_contacts(self, client_shop, client_not_log, contact_data_shop):
        response = client_shop.get(self.URL)
        assert response.status_code == 200
        data = response.json()
        assert len(data) == len(contact_data_shop)
        for i, contact in enumerate(data):
            for con in contact:
                assert contact[con] == contact_data_shop[i].__dict__[con]
        response = client_not_log.get(self.URL)
        assert response.status_code == 401

    # тест получания одного контакта по пользователю
    @pytest.mark.django_db
    @pytest.mark.parametrize(
        ('user_data', 'status'),
        ((user_buyer, 200),
         ({}, 401))
    )
    def test_get_contacts_retrieve(self, client_log, client_not_log, contact_data_shop, user_data, status):
        response = client_log(**user_data).get(f'{self.URL}{contact_data_shop[0].id}/')
        assert response.status_code == status
        if status == 200:
            data = response.json()
            assert data.get('city') == contact_data_shop[0].city

    # тест удаления контакта
    @pytest.mark.django_db
    @pytest.mark.parametrize(
        ('user_data', 'status', 'item'),
        ((user_shop, 204, 1),
         (user_buyer, 403, 0),
         ({}, 401, 0))
    )
    def test_delete_contacts(
            self, client_log,
            client_not_log,
            client_shop,
            contact_data_shop,
            user_data,
            status,
            item
    ):
        data = client_shop.get(self.URL).json()
        client = client_log(**user_data)
        response = client.delete(f"{self.URL}{data[0]['id']}/")
        assert response.status_code == status
        data = client_shop.get(self.URL).json()
        assert len(data) == len(contact_data_shop) - item

    # тест на изменение и добавление контакта
    @pytest.mark.django_db
    @pytest.mark.parametrize('city, street, phone, status_code', testdata)
    def test_patch_contacts(self, city, street, phone, status_code, client_shop, contact_data_shop):
        data = {
            'city': city,
            'street': street,
            'phone': phone
        }
        response = client_shop.patch(f'{self.URL}{contact_data_shop[0].id}/', data=data)
        assert response.status_code == status_code[0]
        response = client_shop.post(self.URL, data=data)
        assert response.status_code == status_code[1]

    # тест на проверку доступа изменения контакта
    @pytest.mark.django_db
    @pytest.mark.parametrize(
        ('user_data', 'status'),
        ((user_shop, 200),
         (user_buyer, 403),
         ({}, 401))
    )
    def test_patch_contact_permissions(self, client_log, contact_data_shop, user_data, status):
        data = {
            'city': 'city',
            'street': 'street',
            'phone': 'phone'
        }
        response = client_log(**user_data).patch(f'{self.URL}{contact_data_shop[0].id}/', data=data)
        assert response.status_code == status
