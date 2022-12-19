import pytest
from django.urls import reverse_lazy


class TestShop:
    URL = reverse_lazy('backend:shops')

    # тест получания списка категорий
    @pytest.mark.django_db
    def test_get_category(self, client_shop, client_not_log, shop_factory):
        shops = shop_factory(_quantity=5)
        response = client_shop.get(self.URL)
        assert response.status_code == 200
        data = response.json()
        assert data['count'] == len(shops)
        response = client_not_log.get(self.URL)
        assert response.status_code == 401
