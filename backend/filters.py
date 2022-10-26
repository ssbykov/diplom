import django_filters

from backend.models import ProductInfo


class ProductFilterPrice(django_filters.FilterSet):
    price__gt = django_filters.NumberFilter(field_name='price', lookup_expr='gt')
    price__lt = django_filters.NumberFilter(field_name='price', lookup_expr='lt')
    class Meta:
        model = ProductInfo
        fields = ['shop']
