import django_filters
import yaml
from django.core.validators import FileExtensionValidator
from django.http import JsonResponse
from django.shortcuts import render
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import mixins, permissions, viewsets
from rest_framework.generics import ListAPIView, get_object_or_404, RetrieveUpdateAPIView
from django.http import Http404
from rest_framework.mixins import CreateModelMixin, UpdateModelMixin
from rest_framework.views import APIView
from yaml.loader import SafeLoader
from pathlib import Path
from django.db.models import Q, Sum, F
from rest_framework.response import Response
from rest_framework import filters

from backend.filters import ProductFilterPrice
from backend.models import Category, Shop, ProductInfo, Product, Parameter, ProductParameter, Contact
from backend.permissions import IsOwnerOrReadOnly
from backend.serializers import ShopSerializer, CategorySerializer, ProductInfoSerializer, ContactSerializer


class CategoryView(ListAPIView):
    """
    Класс для просмотра категорий
    """
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [permissions.IsAuthenticated]


class ShopView(ListAPIView):
    """
    Класс для просмотра списка магазинов
    """
    queryset = Shop.objects.filter(state=True)
    serializer_class = ShopSerializer
    permission_classes = [permissions.IsAuthenticated]


class PartnerUpdate(APIView):
    """
    Класс для обновления прайса от поставщика
    """

    def post(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({'Status': False, 'Error': 'Log in required'}, status=403)

        if request.user.type != 'shop':
            return JsonResponse({'Status': False, 'Error': 'Только для магазинов'}, status=403)

        # url = request.data.get('url')
        # if url:
        #     validate_url = URLValidator()
        #     try:
        #         validate_url(url)
        #     except ValidationError as e:
        #         return JsonResponse({'Status': False, 'Error': str(e)})
        #     else:
        #         stream = get(url).content
        #
        #         data = load_yaml(stream, Loader=Loader)
        filename = request.data.get('filename')
        if filename:
            file_path = Path(__file__).parent.absolute()
            try:
                with open(str(file_path) + filename, encoding='UTF-8') as yml:
                    data = yaml.load(yml, Loader=SafeLoader)
            except FileNotFoundError as e:
                return JsonResponse({'Status': False, 'Error': str(e)})
            else:
                shop, _ = Shop.objects.get_or_create(name=data['shop'], user_id=request.user.id)
                for category in data['categories']:
                    category_object, _ = Category.objects.get_or_create(id=category['id'], name=category['name'])
                    category_object.shops.add(shop.id)
                    category_object.save()
                ProductInfo.objects.filter(shop_id=shop.id).delete()
                for item in data['goods']:
                    product, _ = Product.objects.get_or_create(name=item['name'], category_id=item['category'])

                    product_info = ProductInfo.objects.create(product_id=product.id,
                                                              model=item['model'],
                                                              price=item['price'],
                                                              price_rrc=item['price_rrc'],
                                                              quantity=item['quantity'],
                                                              shop_id=shop.id)
                    for name, value in item['parameters'].items():
                        parameter_object, _ = Parameter.objects.get_or_create(name=name)
                        ProductParameter.objects.create(product_info_id=product_info.id,
                                                        parameter_id=parameter_object.id,
                                                        value=value)

                return JsonResponse({'Status': True})

        return JsonResponse({'Status': False, 'Errors': 'Не указаны все необходимые аргументы'})


class ProductInfoView(viewsets.ModelViewSet):
    serializer_class = ProductInfoSerializer
    queryset = ProductInfo.objects.all()
    filter_backends = (DjangoFilterBackend, filters.SearchFilter,)
    filterset_class = ProductFilterPrice
    search_fields = ['model', 'product__name', 'product__category__name']


class ContactView(viewsets.ModelViewSet):
    serializer_class = ContactSerializer
    queryset = Contact.objects.all()
    permission_classes = [permissions.IsAuthenticated]

    def list(self, request):
        queryset = Contact.objects.filter(user_id=self.request.user.id)
        serializer = ContactSerializer(queryset, many=True)
        return Response(serializer.data)

    def get_permissions(self):
        if self.action in ["destroy", "update", "partial_update"]:
            return (IsOwnerOrReadOnly(),)
        return []

    def get_serializer_context(self):
        self.request.data._mutable = True
        self.request.data.update({'user': self.request.user.id})
        serializer = ContactSerializer(data=self.request.data)
        return {
            'request': self.request,
            'format': self.format_kwarg,
            'view': self
        }
    #
    # def get_object(self):
    #     queryset = self.get_queryset()
    #     lookup_url_kwarg = self.lookup_url_kwarg or self.lookup_field
    #     filter_kwargs = {self.lookup_field: self.kwargs[lookup_url_kwarg]}
    #     obj = get_object_or_404(queryset, **filter_kwargs)
    #     if obj.user_id != self.request.user.id:
    #         raise Http404
    #     return obj


class PartnerState(viewsets.ModelViewSet):
    serializer_class = ShopSerializer
    def list(self, request):
        queryset = Shop.objects.filter(user_id = self.request.user.id)
        serializer = ShopSerializer(queryset, many=True)
        return Response(serializer.data)

    def get_object(self):
        queryset = Shop.objects.filter(user_id = self.request.user.id)
        self.request.data._mutable = True
        self.request.data.update({'name': queryset[0].name})
        obj = get_object_or_404(queryset)
        if obj.user_id != self.request.user.id:
            raise Http404
        return obj

    def get_queryset(self):
        queryset = Shop.objects.filter(user_id = self.request.user.id)
        return queryset