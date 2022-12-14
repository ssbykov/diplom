import pytest
from django.urls import reverse_lazy

from tests.backend.conftest import user_shop


class TestPartnerState:
    URL = reverse_lazy('backend:partner-state')

    # тест получания, изменения статуса магазина
    @pytest.mark.django_db
    def test_get_contacts(self, client_log, client_not_log, shop_factory, user):
        usr = user(**user_shop)
        client = client_log(**user_shop)
        shop = shop_factory(_quantity=1, user=usr)
        response = client.get(self.URL)
        assert response.status_code == 200
        data = response.json()
        assert data['name'] == shop[0].name
        assert data['state'] == shop[0].state
        response = client_not_log.get(self.URL)
        assert response.status_code == 401
        data = client.patch(self.URL, data={'state': False}).json()
        assert data['state'] == False
