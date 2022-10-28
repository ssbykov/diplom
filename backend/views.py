import yaml
from django.db.models import Q, Sum, F
from django.http import JsonResponse
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import permissions, viewsets, status
from rest_framework.generics import ListAPIView, get_object_or_404
from django.http import Http404
from rest_framework.views import APIView
from yaml.loader import SafeLoader
from pathlib import Path
from rest_framework.response import Response
from rest_framework import filters

from backend.filters import ProductFilterPrice
from backend.models import Category, Shop, ProductInfo, Product, Parameter, ProductParameter, Contact, Order, OrderItem
from backend.permissions import IsOwnerOrReadOnly, IsBuyer, IsOwner
from backend.serializers import ShopSerializer, CategorySerializer, ProductInfoSerializer, ContactSerializer, \
    OrderItemSerializer, OrderSerializer


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

    def list(self, request):
        queryset = Contact.objects.filter(user_id=self.request.user.id)
        serializer = ContactSerializer(queryset, many=True)
        return Response(serializer.data)

    def get_permissions(self):
        if self.action in ["destroy", "update", "partial_update"]:
            return (IsOwnerOrReadOnly(),)
        else:
            return (permissions.IsAuthenticated(),)

    def get_serializer_context(self):
        self.request.data._mutable = True
        self.request.data.update({'user': self.request.user.id})
        serializer = ContactSerializer(data=self.request.data)
        return {
            'request': self.request,
            'format': self.format_kwarg,
            'view': self
        }


class PartnerState(viewsets.ModelViewSet):
    serializer_class = ShopSerializer
    permission_classes = [permissions.IsAuthenticated]

    def list(self, request):
        queryset = Shop.objects.filter(user_id=self.request.user.id)
        serializer = ShopSerializer(queryset, many=True)
        return Response(serializer.data)

    def get_object(self):
        queryset = Shop.objects.filter(user_id=self.request.user.id)
        self.request.data._mutable = True
        self.request.data.update({'name': queryset[0].name})
        obj = get_object_or_404(queryset)
        if obj.user_id != self.request.user.id:
            raise Http404
        return obj


class BasketView(viewsets.ModelViewSet):
    # queryset = Order.objects.all()

    def create(self, request, *args, **kwargs):
        basket, _ = Order.objects.get_or_create(user_id=self.request.user.id, state='basket')
        self.request.data._mutable = True
        self.request.data.update({'order': basket.id})
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    def list(self, request):
        queryset = Order.objects.filter(user_id=self.request.user.id).annotate(
            total_sum=Sum(F('ordered_items__quantity') * F('ordered_items__product_info__price'))).distinct()
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    def get_permissions(self):
        permission_classes = [permissions.IsAuthenticated(), IsBuyer()]
        if self.action != "create":
            permission_classes.append(IsOwner())
        return permission_classes

    def get_object(self):
        basket = Order.objects.get(user_id=self.request.user.id, state='basket')
        if basket:
            query = Q() | Q(order_id=basket.id, id=self.kwargs['pk'])
            queryset = OrderItem.objects.filter(query)
            obj = get_object_or_404(queryset)
            return obj

    def get_serializer(self, *args, **kwargs):
        if self.action == 'list':
            return OrderSerializer(*args, **kwargs)
        return OrderItemSerializer(*args, **kwargs)
