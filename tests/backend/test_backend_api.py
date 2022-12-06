import pytest
from django.urls import reverse_lazy


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

    @pytest.fixture
    @pytest.mark.django_db
    def contact_data(self, contact_factory, user):
        return contact_factory(_quantity=4, user=user)

    @pytest.mark.django_db
    def test_get_logout(self, client_not_log):
        response = client_not_log.get(self.URL)
        assert response.status_code == 401

    #тест получания контактов по пользователю
    @pytest.mark.django_db
    def test_get_contacts(self, client_log, contact_data, user):
        response = client_log.get(self.URL)
        assert response.status_code == 200
        data = response.json()
        assert len(data) == len(contact_data)
        for i, contact in enumerate(data):
            for con in contact:
                assert contact[con] == contact_data[i].__dict__[con]

    #тест удаления контакта
    @pytest.mark.django_db
    def test_delete_contacts(self, client_log, contact_data, user):
        data = client_log.get(self.URL).json()
        response = client_log.delete(f"{self.URL}{data[0]['id']}/")
        assert response.status_code == 204
        data = client_log.get(self.URL).json()
        assert len(data) == len(contact_data) - 1

    #тест получания одного контакта по пользователю
    @pytest.mark.django_db
    def test_get_contacts_retrieve(self, client_log, contact_data):
        for contact in contact_data:
            response = client_log.get(f'{self.URL}{contact.id}/')
            assert response.status_code == 200
            data = response.json()
            assert data.get('city') == contact.city


    #тест на изменение и добавление контакта
    @pytest.mark.django_db
    @pytest.mark.parametrize('city, street, phone, status_code', testdata)
    def test_patch_contacts(self, city, street, phone, status_code, client_log, contact_data):
        data = {
            'city': city,
            'street': street,
            'phone': phone
        }
        response = client_log.patch(f'{self.URL}{contact_data[0].id}/', data=data)
        assert response.status_code == status_code[0]
        response = client_log.post(self.URL, data=data)
        assert response.status_code == status_code[1]
