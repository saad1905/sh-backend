from django.contrib import admin
from django.urls import path, include
from rest_framework import routers, permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi
from market.views import UserViewSet,RentItemViewSet,SellItemViewSet,CartViewSet,PaymentViewSet
from django.conf import settings
from django.conf.urls.static import static
from market.views import get_csrf_token


schema_view = get_schema_view(
    openapi.Info(
        title="SH API (Simple Auth ViewSet)",
        default_version='v1',
        description="API simple pour vente et location de meubles (auth basique avec ViewSet)",
    ),
    public=True,
    permission_classes=[permissions.AllowAny],
)

router = routers.DefaultRouter()
router.register(r'users', UserViewSet, basename='user')
router.register(r'rent-items', RentItemViewSet, basename='rent-item')
router.register(r'sell-items', SellItemViewSet, basename='sell-item')
router.register(r'cart', CartViewSet, basename='cart')
router.register(r'payments', PaymentViewSet, basename='payments')  # ✅ <--- ici




urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include(router.urls)),
    path('api/csrf/', get_csrf_token),  # 👈 ajoute cette ligne
    

    # Swagger
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='swagger-ui'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
