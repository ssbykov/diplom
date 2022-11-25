import requests
from django.db.models import Q, Sum, F
from django.db import IntegrityError
from django.http import JsonResponse
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import permissions, viewsets, status
from rest_framework.generics import ListAPIView, get_object_or_404
from django.http import Http404
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import filters
from rest_framework.decorators import action

from backend.filters import ProductFilterPrice
from backend.models import Category, Shop, ProductInfo, Contact, Order, OrderItem
from backend.permissions import IsOwnerOrReadOnly, IsBuyer
from backend.serializers import ShopSerializer, CategorySerializer, ProductInfoSerializer, ContactSerializer, \
    OrderItemSerializer, OrdersListSerializer, OrderNewSerializer, OrderSerializer
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

    def get_serializer_context(self):
        if hasattr(self.request.data, '_mutable'):
            self.request.data._mutable = True
        self.request.data.update({'user': self.request.user.id})
        serializer = ContactSerializer(data=self.request.data)
        return {
            'request': self.request,
            'format': self.format_kwarg,
            'view': self
        }


class PartnerState(viewsets.ModelViewSet):
    """
    Класс для работы со статусом поставщика
    """

    serializer_class = ShopSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrReadOnly]

    def list(self, request):
        queryset = Shop.objects.filter(user_id=self.request.user.id)
        serializer = ShopSerializer(queryset, many=True)
        return Response(serializer.data)

    def get_object(self):
        queryset = Shop.objects.filter(user_id=self.request.user.id)
        if hasattr(self.request.data, '_mutable'):
            self.request.data._mutable = True
        self.request.data.update({'name': queryset[0].name})
        obj = get_object_or_404(queryset)
        if obj.user_id != self.request.user.id:
            raise Http404
        return obj


class BasketView(viewsets.ModelViewSet):
    """
    Класс для работы с корзиной пользователя
    """

    permission_classes = [permissions.IsAuthenticated, IsBuyer]

    def create(self, request, *args, **kwargs):
        basket, _ = Order.objects.get_or_create(user_id=self.request.user.id, state='basket')
        product_info = self.request.data.get('product_info')
        if ProductInfo.objects.filter(id=product_info).first():
            if hasattr(self.request.data, '_mutable'):
                self.request.data._mutable = True
            self.request.data.update({'order': basket.id})
        else:
            return JsonResponse({'Status': 'Данные по товару отсутствуют'})
        if not ProductInfo.objects.get(id=product_info).shop.state:
            return JsonResponse({'Status': 'Данный товар недоступен для заказа'})
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            self.perform_create(serializer)
        except IntegrityError as er:
            return JsonResponse({'Status': 'Данная позиция уже добавлена'})
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    @action(methods=['patch'], detail=False)
    def update_new(self, request, *args, **kwargs):
        is_updated = self.get_object()
        if is_updated:
            if hasattr(self.request.data, '_mutable'):
                self.request.data._mutable = True
            self.request.data.update({'state': 'new'})
            serializer = OrderNewSerializer(is_updated, data=self.request.data)
            serializer.is_valid(raise_exception=True)
            self.perform_update(serializer)
            sand_mail.delay(
                request.user.id,
                f"'Заказ №{is_updated.pk} сформирован'",
                'Обновление статуса заказа')
            return Response(serializer.data)
        return JsonResponse({'Status': 'Неправильные данные по заказу'})

    def list(self, request):
        queryset = Order.objects.filter(user_id=self.request.user.id, state='basket').annotate(
            total_sum=Sum(F('ordered_items__quantity') * F('ordered_items__product_info__price'))).distinct()
        serializer = self.get_serializer(queryset, many=True)
        if serializer.data:
            return Response(serializer.data)
        return JsonResponse({'Status': 'Нет оформляемых заказов'})

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
        return OrderItemSerializer(*args, **kwargs)


class OrderView(viewsets.ReadOnlyModelViewSet):
    """
    Класс для получения и размешения заказов пользователями
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
