from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import DealsListViewSet, RegisterView, LoginView

router = DefaultRouter()
router.register(r'deals', DealsListViewSet, basename='deals')

urlpatterns = [
    path('register/', RegisterView.as_view(), name="register"),
    path('login/', LoginView.as_view(), name="login"),
    path('', include(router.urls)),
]