from django.urls import path, include
from django.contrib import admin
from rest_framework.routers import DefaultRouter
from .views import DealsListViewSet
from django.urls import path

router = DefaultRouter()
router.register(r'deals', DealsListViewSet, basename='deals')

urlpatterns = [
    path('api/', include(router.urls)),
]
