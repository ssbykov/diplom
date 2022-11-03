from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.db.models import Q, Sum, F

from .models import Shop, Category, Order, OrderItem, ProductInfo, User, ProductParameter, Contact


class OrderItemsInline(admin.TabularInline):
    model = OrderItem
    fields = ('product_info', 'quantity')
    extra = 1


class ProductParameterInline(admin.TabularInline):
    model = ProductParameter
    extra = 1


class ContactInline(admin.StackedInline):
    model = Contact
    extra = 1

    fieldsets = (
        ('Адрес', {'fields': (('city', 'street'), ('house', 'structure'), ('building', 'apartment'))}),
        (None, {'fields': ('phone',)}),
    )



@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('order_number', 'user', 'contact', 'dt', 'state', 'order_sum')
    fields = ('user', 'contact', 'state', 'dt', 'order_sum')
    readonly_fields = ('dt', 'order_sum')
    list_display_links = ('order_number', 'dt')
    list_filter = ('user', 'state')
    search_fields = ('user__first_name', 'user__last_name')
    inlines = [OrderItemsInline]

    def order_sum(self, obj):
        lst_items = obj.ordered_items.all().prefetch_related(
            'product_info__product__category',
            'product_info__product_parameters__parameter').annotate(
            total_sum=Sum(F('quantity') * F('product_info__price')))
        return f"{sum(x.total_sum for x in lst_items)} руб."

    def order_number(self, obj):
        return obj.id

    order_sum.short_description = 'Сумма'
    order_number.short_description = 'Заказ №'



@admin.register(ProductInfo)
class ProductInfoAdmin(admin.ModelAdmin):
    list_display = ('product', 'model', 'shop', 'price', 'price_rrc')
    ordering = ('product', 'price')
    list_filter = ('shop',)
    search_fields = ('product__name', 'model')
    inlines = [ProductParameterInline]


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    """
    Панель управления пользователями
    """
    model = User

    fieldsets = (
        (None, {'fields': ('email', 'password', 'type')}),
        ('Персональная информация', {'fields': ('first_name', 'last_name')}),
        ('Права', {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
        }),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )
    list_display = ('email', 'first_name', 'last_name', 'is_staff')
    inlines = [ContactInline]

admin.site.register(Shop)
admin.site.register(Category)
