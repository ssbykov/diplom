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
    path('partner/update/', PartnerUpdate.as_view(), name='partner-update'),
    path('partner/state/', PartnerState.as_view(), name='partner-state'),

]