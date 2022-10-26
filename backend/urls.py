from django.urls import path

from backend.views import CategoryView, PartnerUpdate, ShopView, ProductInfoView, ContactView, PartnerState

app_name = 'backend'
urlpatterns = [
    path('categories/', CategoryView.as_view(), name='categories'),
    path('shops/', ShopView.as_view(), name='shops'),
    path('products/', ProductInfoView.as_view({'get': 'list'}), name='products'),
    path('products/<int:pk>/', ProductInfoView.as_view({'get': 'retrieve'}), name='product'),
    path('user/contact/', ContactView.as_view({'get': 'list', 'post': 'create'}), name='contacts'),
    path('user/contact/<int:pk>/', ContactView.as_view({'delete': 'destroy', 'put': 'update'}), name='contact'),
    path('partner/update/', PartnerUpdate.as_view(), name='partner-update'),
    path('partner/state/', PartnerState.as_view({'get': 'list', 'patch': 'update'}), name='partner-state'),

]