from django.shortcuts import render
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db import transaction
from rest_framework import generics
from django.contrib.auth.models import User
from rest_framework.permissions import AllowAny
from rest_framework_simplejwt.views import TokenObtainPairView
from .serializers import DealsListSerializer, UserSerializer, StoreSerializer, CustomLoginSerializer
from .models import DealsList, StoreInfo
from .services import DealListService, StoreListService
from rest_framework.pagination import LimitOffsetPagination
from rest_framework import filters
from django_filters.rest_framework import DjangoFilterBackend
import logging
import random

logger = logging.getLogger(__name__)
allowed_store_ids = ['1', '7', '25']

class DealsListViewSet(viewsets.ModelViewSet):
    queryset = DealsList.objects.all()
    serializer_class = DealsListSerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter, filters.SearchFilter]
    filterset_fields = {
        'store__store_name': ['exact', 'icontains'],
        'sale_price': ['exact', 'gte', 'lte'],
        'deal_rating': ['exact', 'gte', 'lte'],
        'game_name': ['icontains', 'exact'],
    }
    ordering_fields = ['sale_price', 'deal_rating', 'game_name', 'saving']
    
    def list(self, request, *args, **kwargs):
        queryset =  self.filter_queryset(self.get_queryset())

        if not request.user.is_authenticated:
            all_store_ids = list(queryset.values_list("store_id", flat=True).distinct())
            
            if len(all_store_ids) == 0:
                return Response({"results": []})
            
            selected_store_ids = random.sample(all_store_ids, min(3, len(all_store_ids)))
            
            final_deals = []
            for store_id in selected_store_ids:
                deals = list(queryset.filter(store_id=store_id))
                if deals:
                    final_deals.append(random.choice(deals))
            
            serializer = self.get_serializer(final_deals, many=True)
            return Response({"results": serializer.data})
        
        paginator = LimitOffsetPagination()
        paginator.default_limit = 8
        result_page = paginator.paginate_queryset(queryset, request)
        serializer = self.get_serializer(result_page, many=True)
        
        
        return paginator.get_paginated_response(serializer.data)
    
    @action(detail=False, methods=['post'])
    def sync_stores(self, request):

        try:
            store_data = StoreListService.fetch_stores()
            
            if not store_data:
                return Response(
                    {"error": "Impossibile recuperare gli store dall'API CheapShark"}, 
                    status=status.HTTP_503_SERVICE_UNAVAILABLE
                )
            
            created_count = 0
            updated_count = 0
            
            with transaction.atomic():
                IMAGE_BASE_URL = "https://www.cheapshark.com"
                
                for store in store_data:
                    
                    store_id = str(store.get('storeID', ''))
                    if store_id not in allowed_store_ids:
                        continue
                    store_obj, created = StoreInfo.objects.update_or_create(
                        store_id=str(store.get('storeID', '')),
                        defaults={
                            'store_name': store.get('storeName', 'Nome non disponibile'),
                            "store_logo_url": IMAGE_BASE_URL + store.get("images", {}).get("logo", ""),
                            "store_banner_url": IMAGE_BASE_URL + store.get("images", {}).get("banner", ""),
                            "store_icon_url": IMAGE_BASE_URL + store.get("images", {}).get("icon", ""),
                        }
                    )
                    
                    if created:
                        created_count += 1
                    else:
                        updated_count += 1
            
            return Response({
                "message": "Sincronizzazione store completata",
                "created": created_count,
                "updated": updated_count
            })
            
        except Exception as e:
            return Response(
                {"error": f"Errore durante la sincronizzazione degli store: {str(e)}"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['post'])
    def sync_from_cheapshark(self, request):
        
        store_sync_response = self.sync_stores(request)
        if store_sync_response.status_code != 200:
            return store_sync_response
        
        target_store_ids = ['1', '7', '25']
        target_stores = {
            '1': 'Steam',
            '7': 'Humble Bundle', 
            '25': 'GOG'
        }
        
        try:
            all_selected_games = DealListService.fetch_games_by_stores(
                store_ids=target_store_ids, 
                base_games_per_store=5,
                total_target=16
            )
        except Exception as e:
            logger.error(f"Errore nel metodo fetch_games_by_stores: {e}")
            # Fallback al metodo originale
            games_data = DealListService.fetch_games()
            
            if not games_data:
                return Response(
                    {"error": "Impossibile recuperare i giochi dall'API CheapShark"}, 
                    status=status.HTTP_503_SERVICE_UNAVAILABLE
                )
            
            games_by_store = {store_id: [] for store_id in target_store_ids}
            
            for game in games_data:
                store_id = game.get('storeID', '')
                if store_id in target_store_ids:
                    games_by_store[store_id].append(game)
            
            all_selected_games = []
            max_games = 5 
            
            for i in range(max_games):
                for store_id in target_store_ids:
                    if len(games_by_store[store_id]) > i:
                        all_selected_games.append(games_by_store[store_id][i])
                        if len(all_selected_games) >= 16:
                            break
                if len(all_selected_games) >= 16:
                    break
        
        all_selected_games = all_selected_games[:16]
        
        if not all_selected_games:
            return Response(
                {"error": "Nessun gioco trovato per gli store selezionati"}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        created_count = 0
        updated_count = 0
        processed_count = 0
        store_counts = {store_id: 0 for store_id in target_store_ids}
        
        with transaction.atomic():
            
            for game in all_selected_games:
                store_id = game.get('storeID', '')
                
                store_obj = None
                if store_id:
                    try:
                        store_obj = StoreInfo.objects.get(store_id=store_id)
                    except StoreInfo.DoesNotExist:
                        store_obj = StoreInfo.objects.create(
                            store_id=store_id,
                            store_name=target_stores.get(store_id, f"Store {store_id}")
                        )
                        
                deals_data = {
                    'external_id': game.get('dealID', ''),
                    'store': store_obj,
                    'game_name': game.get('title', 'Nome non disponibile'),
                    'image_url': game.get('thumb', ''),
                    'saving': game.get("savings", 123),
                    'sale_price': float(game.get('salePrice', 0)),
                    'normal_price': float(game.get('normalPrice', 0)),
                    'deal_rating': float(game.get('dealRating', 0))
                }
                
                deal, created = DealsList.objects.update_or_create(
                    external_id=deals_data['external_id'],
                    defaults=deals_data
                )
                
                if created:
                    created_count += 1
                else:
                    updated_count += 1
                    
                processed_count += 1
                store_counts[store_id] += 1

        return Response({
            "message": "Sincronizzazione completata",
            "created": created_count,
            "updated": updated_count,
            "processed": processed_count,
            "distribution": {
                "Steam": store_counts.get('1', 0),
                "Humble Bundle": store_counts.get('7', 0),
                "GOG": store_counts.get('25', 0)
            },
            "filtered_stores": ["Steam", "Humble Bundle", "GOG"]
        })
    
    @action(detail=False, methods=['delete'])
    def delete_local_deals(self, request, pk=None):
        try:
            count = DealsList.objects.count()
            DealsList.objects.all().delete()
            StoreInfo.objects.all().delete()
            return Response({
                "message": f"Eliminati {count} deals"
            })
        except DealsList.DoesNotExist:
            return Response({"error": "Offerta non trovata."}, status=status.HTTP_404_NOT_FOUND)

class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    permission_classes = [AllowAny]
    serializer_class = UserSerializer
    
    def create(self, request, *args, **kwargs):
        username = request.data.get("username")
        if User.objects.filter(username=username).exists():
            return Response(
                {"error": "Username already exists."},
                status=status.HTTP_400_BAD_REQUEST
            )
        return super().create(request, *args, **kwargs)

class LoginView(TokenObtainPairView):
    permission_classes = [AllowAny]
    serializer_class = CustomLoginSerializer

class StoreView(viewsets.ReadOnlyModelViewSet):
    queryset = StoreInfo.objects.all()
    serializer_class = StoreSerializer

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)