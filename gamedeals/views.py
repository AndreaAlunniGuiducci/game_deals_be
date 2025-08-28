from django.shortcuts import render
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db import transaction
from .serializers import DealsListSerializer
from .models import DealsList
from .services import DealListService

class DealsListViewSet(viewsets.ModelViewSet):
    queryset = DealsList.objects.all()
    serializer_class = DealsListSerializer
    
    def list(self, request):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['post'])
    def sync_from_cheapshark(self, request):
        games_data = DealListService.fetch_games()
        
        if not games_data:
            return Response(
                {"error": "Impossibile recuperare i giochi dall'API CheapShark"}, 
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )
        
        created_count = 0
        updated_count = 0
        
        with transaction.atomic():
            for game in games_data:
                print("GAME RECUPERATO",game)
                deals_data = {
                    'external_id': game.get('dealID', ''),
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
    
    @action(detail=False, methods=['get'])
    def fetch_live_deals(self, request):
        games_data = DealListService.fetch_games()
        
        if not games_data:
            return Response(
                {"error": "Impossibile recuperare i giochi dall'API CheapShark"}, 
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )
        
        formatted_deals = []
        for game in games_data:
            formatted_deals.append({
                'external_id': game.get('dealID', ''),
                'game_name': game.get('title', 'Nome non disponibile'),
                'image_url': game.get('thumb', ''),
                'sale_price': float(game.get('salePrice', 0)),
                'normal_price': float(game.get('normalPrice', 0)),
                'deal_rating': float(game.get('dealRating', 0))
            })
        
        return Response({
            "count": len(formatted_deals),
            "deals": formatted_deals
        })
