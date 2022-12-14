import pytest
from django.urls import reverse_lazy


class TestCategory:
    URL = reverse_lazy('backend:categories')

    # тест получания списка категорий
    @pytest.mark.django_db
    def test_get_category(self, client_shop, client_not_log, category_factory):
        categores = category_factory(_quantity=4)
        response = client_shop.get(self.URL)
        assert response.status_code == 200
        data = response.json()
        assert len(data) == len(categores)
        response = client_not_log.get(self.URL)
        assert response.status_code == 401
