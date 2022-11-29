import requests
from django.db.models import Q, Sum, F
from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django_filters.rest_framework import DjangoFilterBackend
from drf_yasg.utils import swagger_auto_schema
from rest_framework import permissions, viewsets, status, mixins
from rest_framework.generics import ListAPIView, get_object_or_404
from rest_framework.viewsets import GenericViewSet
from django.http import Http404
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import filters
from rest_framework.decorators import action

from backend.filters import ProductFilterPrice
from backend.models import Category, Shop, ProductInfo, Contact, Order, OrderItem
from backend.permissions import IsOwnerOrReadOnly, IsBuyer
from backend.serializers import ShopSerializer, CategorySerializer, ProductInfoSerializer, ContactSerializer, \
    OrderItemSerializer, OrdersListSerializer, OrderNewSerializer, OrderSerializer, OrderItemCreateSerializer
from backend.tasks import do_import, sand_mail


class UserActivationView(APIView):
    def get(self, request, uid, token):
        protocol = 'https://' if request.is_secure() else 'http://'
        web_url = protocol + request.get_host()
        post_url = web_url + "/api/v1/auth/users/activation/"
        post_data = {'uid': uid, 'token': token}
        result = requests.post(post_url, data=post_data)
        content = result.text
        return Response(content)


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
    queryset = Shop.objects.all()
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

        filename = request.data.get('filename')
        if filename:
            do_import.delay(filename, request.user.id)
            return JsonResponse({'Status': True})
        else:
            return JsonResponse({'Status': False, 'Errors': 'Не указаны все необходимые аргументы'})


class ProductInfoView(viewsets.ModelViewSet):
    """
    Класс для просмотра информации о товаре
    """
    serializer_class = ProductInfoSerializer
    queryset = ProductInfo.objects.all()
    filter_backends = (DjangoFilterBackend, filters.SearchFilter,)
    filterset_class = ProductFilterPrice
    search_fields = ['model', 'product__name', 'product__category__name']


class ContactView(viewsets.ModelViewSet):
    """
    Класс для работы с контактами покупателей
    """

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


class PartnerState(mixins.RetrieveModelMixin,
                   mixins.UpdateModelMixin,
                   GenericViewSet):
    """
    Класс для работы со статусом поставщика
    """
    serializer_class = ShopSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrReadOnly]

    def get_object(self):
        queryset = Shop.objects.filter(user_id=self.request.user.id)
        obj = get_object_or_404(queryset)
        if obj.user_id != self.request.user.id:
            raise Http404
        return obj


@method_decorator(name='update_new', decorator=swagger_auto_schema(
    operation_description="Подтверждение заказа с указанием контакта",
))
@method_decorator(name='create', decorator=swagger_auto_schema(
    operation_description="Добавление или редактирование товара в корзине",
))
@method_decorator(name='retrieve', decorator=swagger_auto_schema(
    operation_description="Промотр данных по товару в корзине",
))
class BasketView(mixins.CreateModelMixin,
                 mixins.RetrieveModelMixin,
                 mixins.DestroyModelMixin,
                 mixins.ListModelMixin,
                 GenericViewSet):
    """
    Класс для работы с корзиной пользователя
    """
    permission_classes = [permissions.IsAuthenticated, IsBuyer]

    def create(self, request, *args, **kwargs):
        basket, _ = Order.objects.get_or_create(user_id=self.request.user.id, state='basket')
        product_info = self.request.data.get('product_info')
        if not ProductInfo.objects.filter(id=product_info).first():
            return JsonResponse({'Status': 'Данные по товару отсутствуют'})
        if not ProductInfo.objects.get(id=product_info).shop.state:
            return JsonResponse({'Status': 'Данный товар недоступен для заказа'})
        instance = OrderItem.objects.filter(product_info=product_info, order_id=basket.id).first()
        serializer = OrderItemCreateSerializer(data=request.data, context={'order': basket}, instance=instance)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    @action(methods=['patch'], detail=False)
    def update_new(self, request, *args, **kwargs):
        is_updated = Order.objects.filter(user_id=self.request.user.id, state='basket').first()
        if is_updated:
            serializer = OrderNewSerializer(instance=is_updated, data=self.request.data)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            sand_mail.delay(
                request.user.id,
                f"'Заказ №{is_updated.pk} сформирован'",
                'Обновление статуса заказа')
            return JsonResponse({'Status': 'Заказ сформирован'})
        return JsonResponse({'Status': 'Неправильные данные по заказу'})

    def list(self, request):
        queryset = Order.objects.filter(user_id=self.request.user.id, state='basket').annotate(
            total_sum=Sum(F('ordered_items__quantity') * F('ordered_items__product_info__price'))).distinct()
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    def get_object(self):
        basket = Order.objects.filter(user_id=self.request.user.id, state='basket')
        if basket and 'pk' in self.kwargs:
            query = Q() | Q(order_id=basket.first().id, id=self.kwargs['pk'])
            queryset = OrderItem.objects.filter(query)
            return get_object_or_404(queryset)
        elif basket:
            return get_object_or_404(basket)

        raise Http404

    def get_serializer(self, *args, **kwargs):
        if self.action == 'list':
            return OrderSerializer(*args, **kwargs)
        elif self.action == 'retrieve':
            return OrderItemSerializer(*args, **kwargs)
        elif self.action == 'update_new':
            return OrderNewSerializer(*args, **kwargs)
        return OrderItemCreateSerializer(*args, **kwargs)

    def get_queryset(self):
        queryset = Order.objects.filter(user_id=self.request.user.id, state='basket')
        return queryset


class OrderView(viewsets.ReadOnlyModelViewSet):
    """
    Класс для получения информации по заказам пользователя
    """

    permission_classes = [permissions.IsAuthenticated, IsBuyer]

    def list(self, queryset):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        if serializer.data:
            return Response(serializer.data)
        return JsonResponse({'Status': 'Нет активных заказов'})

    def get_serializer(self, *args, **kwargs):
        if self.action == 'list':
            return OrdersListSerializer(*args, **kwargs)
        return OrderSerializer(*args, **kwargs)

    def get_queryset(self):
        queryset = Order.objects.filter(
            user_id=self.request.user.id).exclude(state='basket').prefetch_related(
            'ordered_items__product_info__product__category',
            'ordered_items__product_info__product_parameters__parameter').select_related('contact').annotate(
            total_sum=Sum(F('ordered_items__quantity') * F('ordered_items__product_info__price'))).distinct()
        return queryset
