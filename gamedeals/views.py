from django.shortcuts import render
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db import transaction
from rest_framework import generics
from django.contrib.auth.models import User
from rest_framework.permissions import AllowAny
from rest_framework_simplejwt.views import TokenObtainPairView
from .serializers import DealsListSerializer, UserSerializer
from .models import DealsList, StoreInfo
from .services import DealListService, StoreListService

class DealsListViewSet(viewsets.ModelViewSet):
    queryset = DealsList.objects.all()
    serializer_class = DealsListSerializer
    
    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        
        if not request.user.is_authenticated:
            queryset = queryset[:3]
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
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
                for store in store_data:
                    store_obj, created = StoreInfo.objects.update_or_create(
                        store_id=str(store.get('storeID', '')),
                        defaults={
                            'store_name': store.get('storeName', 'Nome non disponibile')
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
        
        games_data = DealListService.fetch_games()
                    
        if not games_data:
            return Response(
                {"error": "Impossibile recuperare i giochi dall'API CheapShark"}, 
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )
        
        created_count = 0
        updated_count = 0
        
        with transaction.atomic():
            
            store_id = game.get('storeID', '')
            
            store_obj = None
            if store_id:
                try:
                    store_obj = StoreInfo.objects.get(store_id=store_id)
                except StoreInfo.DoesNotExist:
                    # Se lo store non esiste, crealo con dati base
                    store_obj = StoreInfo.objects.create(
                        store_id=store_id,
                        store_name=f"Store {store_id}"
                    )
            
            for game in games_data:
                deals_data = {
                    'external_id': game.get('dealID', ''),
                    'store': store_obj,
                    'game_name': game.get('title', 'Nome non disponibile'),
                    'image_url': game.get('thumb', ''),
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

        return Response({
            "message": "Sincronizzazione completata",
            "created": created_count,
            "updated": updated_count
        })
    
    # @action(detail=False, methods=['get'])
    # def fetch_live_deals(self, request):
    #     games_data = DealListService.fetch_games()
        
    #     if not games_data:
    #         return Response(
    #             {"error": "Impossibile recuperare i giochi dall'API CheapShark"}, 
    #             status=status.HTTP_503_SERVICE_UNAVAILABLE
    #         )
        
    #     formatted_deals = []
    #     for game in games_data:
    #         formatted_deals.append({
    #             'external_id': game.get('dealID', ''),
    #             'game_name': game.get('title', 'Nome non disponibile'),
    #             'image_url': game.get('thumb', ''),
    #             'sale_price': float(game.get('salePrice', 0)),
    #             'normal_price': float(game.get('normalPrice', 0)),
    #             'deal_rating': float(game.get('dealRating', 0))
    #         })
        
    #     return Response({
    #         "count": len(formatted_deals),
    #         "deals": formatted_deals
    #     })

    @action(detail=False, methods=['delete'])
    def delete_local_deals(self, request, pk=None):
        try:
            count = DealsList.objects.count()
            DealsList.objects.all().delete()
            return Response({
                "message": f"Eliminati {count} deals"
            })
        except DealsList.DoesNotExist:
            return Response({"error": "Offerta non trovata."}, status=status.HTTP_404_NOT_FOUND)

class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    permission_classes = [AllowAny]
    serializer_class = UserSerializer

class LoginView(TokenObtainPairView):
    permission_classes = [AllowAny]
