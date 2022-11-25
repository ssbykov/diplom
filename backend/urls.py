from django.urls import path, include
from rest_framework import routers

from backend.views import CategoryView, PartnerUpdate, ShopView, ProductInfoView, ContactView, PartnerState, BasketView, \
    OrderView


router = routers.DefaultRouter()
router.register(r'products', ProductInfoView)
router.register(r'order', OrderView, basename='OrderView')
router.register(r'user/contact', ContactView, basename='ContactView')
router.register(r'basket', BasketView, basename='BasketView')

app_name = 'backend'
urlpatterns = [
    path('categories/', CategoryView.as_view(), name='categories'),
    path('shops/', ShopView.as_view(), name='shops'),
    path('', include(router.urls)),
    # path('products/', ProductInfoView.as_view({'get': 'list'}), name='products'),
    # path('products/<int:pk>/', ProductInfoView.as_view({'get': 'retrieve'}), name='product'),
    # path('user/contact/', ContactView.as_view({'get': 'list', 'post': 'create'}), name='contacts'),
    # path('user/contact/<int:pk>/', ContactView.as_view({'delete': 'destroy', 'put': 'update'}), name='contact'),
    path('partner/update/', PartnerUpdate.as_view(), name='partner-update'),
    path('partner/state/', PartnerState.as_view({'get': 'list', 'patch': 'update'}), name='partner-state'),
    # path('basket/', BasketView.as_view({'get': 'list', 'post': 'create', 'delete': 'destroy','patch': 'update_new'}), name='basket'),
    # path('basket/<int:pk>/', BasketView.as_view({'delete': 'destroy', 'put': 'update'}), name='basket-item'),
    # path('order/', OrderView.as_view({'get': 'list'}), name='order'),
    # path('order/<int:pk>/', OrderView.as_view({'get': 'retrieve'}), name='order-new'),

]