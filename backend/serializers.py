from rest_framework import serializers
from rest_framework.fields import CurrentUserDefault

from backend.models import Category, Shop, Product, ProductParameter, ProductInfo, Contact, Order, OrderItem


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ('id', 'name',)
        read_only_fields = ('id',)


class ShopSerializer(serializers.ModelSerializer):
    class Meta:
        model = Shop
        fields = ('id', 'name', 'state')
        read_only_fields = ('id',)


class ProductSerializer(serializers.ModelSerializer):
    category = serializers.StringRelatedField()

    class Meta:
        model = Product
        fields = ('name', 'category',)


class ProductParameterSerializer(serializers.ModelSerializer):
    parameter = serializers.StringRelatedField()

    class Meta:
        model = ProductParameter
        fields = ('parameter', 'value',)


class ProductInfoSerializer(serializers.ModelSerializer):
    product = ProductSerializer(read_only=True)
    product_parameters = ProductParameterSerializer(read_only=True, many=True)

    class Meta:
        model = ProductInfo
        fields = ('id', 'model', 'product', 'shop', 'quantity', 'price', 'price_rrc', 'product_parameters',)
        read_only_fields = ('id',)


class ContactSerializer(serializers.ModelSerializer):
    user = serializers.HiddenField(default=CurrentUserDefault())

    class Meta:
        model = Contact
        fields = ('id', 'city', 'street', 'house', 'structure', 'building', 'apartment', 'user', 'phone')
        read_only_fields = ('id',)
        extra_kwargs = {
            'user': {'write_only': True}
        }


class OrderItemCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItem
        fields = ('id', 'product_info', 'quantity', 'order',)
        read_only_fields = ('id', 'order')
        # extra_kwargs = {
        #     'order': {'write_only': True}
        # }

    def create(self, validated_data):
        order = OrderItem(
            quantity=validated_data['quantity'],
            order=self.context['order'],
            product_info=validated_data['product_info']
        )
        order.save()
        return order


class OrdersListSerializer(serializers.ModelSerializer):
    total_sum = serializers.IntegerField()
    contact = ContactSerializer(read_only=True)

    class Meta:
        model = Order
        fields = ('id', 'ordered_items', 'state', 'dt', 'total_sum', 'contact',)
        read_only_fields = ('id',)


class OrderItemSerializer(OrderItemCreateSerializer):
    product_info = ProductInfoSerializer(read_only=True)


class OrderSerializer(OrdersListSerializer):
    ordered_items = OrderItemSerializer(read_only=True, many=True)


class OrderNewSerializer(serializers.ModelSerializer):
    class Meta:
        model = Order
        fields = ('id', 'contact',)
        read_only_fields = ('id',)

    def update(self, instance, validated_data):
        instance.state = 'new'
        instance.save()
        return instance
