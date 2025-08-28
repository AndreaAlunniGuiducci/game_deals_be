from django.shortcuts import render
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db import transaction
from decimal import Decimal, InvalidOperation
import logging
from .serializers import DealsListSerializer
from .models import DealsList
from .services import DealListService

logger = logging.getLogger(__name__)

class DealsListViewSet(viewsets.ModelViewSet):
    queryset = DealsList.objects.all()
    serializer_class = DealsListSerializer
    
    def list(self, request, *args, **kwargs):
        """Lista tutti i deals dal database locale"""
        queryset = self.get_queryset()
        print(f"🔍 DEBUG: Trovati {queryset.count()} deals nel database")
        
        # Debug: stampa i primi 3 deals
        for i, deal in enumerate(queryset[:3]):
            print(f"Deal {i}: ID={deal.id}, external_id='{deal.external_id}', name='{deal.game_name}', sale_price={deal.sale_price}")
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    def _safe_conversion(self, value, default=0.0):
        """Converte un valore in float gestendo gli errori"""
        if value is None or value == '' or value == 'null':
            return default
        try:
            return float(value)
        except (ValueError, TypeError):
            logger.warning(f"⚠️ Impossibile convertire '{value}' in float, uso default {default}")
            return default
    
    @action(detail=False, methods=['post'])
    def sync_from_cheapshark(self, request):
        """Sincronizza i deals dall'API CheapShark"""
        print("🔄 DEBUG: Inizio sync_from_cheapshark")
        
        # Prima prova con games, poi con deals se games è vuoto
        games_data = DealListService.fetch_games()
        data_source = "games"
        
        if not games_data:
            print("📦 DEBUG: Nessun dato da games, provo con deals...")
            games_data = DealListService.fetch_deals()
            data_source = "deals"
        
        if not games_data:
            return Response(
                {"error": "Impossibile recuperare i giochi dall'API CheapShark"}, 
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )
        
        print(f"📋 DEBUG: Ricevuti {len(games_data)} elementi da endpoint '{data_source}'")
        print(f"🔍 DEBUG: Primo elemento ricevuto: {games_data[0] if games_data else 'NESSUNO'}")
        
        created_count = 0
        updated_count = 0
        
        with transaction.atomic():
            for i, game in enumerate(games_data):
                try:
                    print(f"\n--- DEBUG ELEMENTO {i} ---")
                    print(f"Dati grezzi: {game}")
                    
                    # Gestisci i diversi formati di dati
                    if data_source == "games" or 'gameID' in game:
                        # Formato da /games endpoint
                        deals_data = {
                            'external_id': str(game.get('gameID', f'game_{i}')),
                            'game_name': game.get('external', f'Game {i}'),
                            'image_url': game.get('thumb', ''),
                            'sale_price': self._safe_conversion(game.get('cheapest', 0)),
                            'normal_price': self._safe_conversion(game.get('cheapest', 0)) * 1.5
                        }
                        print(f"🎮 DEBUG: Usato formato GAMES")
                    else:
                        # Formato da /deals endpoint  
                        deals_data = {
                            'external_id': str(game.get('dealID', f'deal_{i}')),
                            'game_name': game.get('title', f'Game {i}'),
                            'image_url': game.get('thumb', ''),
                            'sale_price': self._safe_conversion(game.get('salePrice', 0)),
                            'normal_price': self._safe_conversion(game.get('normalPrice', 0))
                        }
                        print(f"💰 DEBUG: Usato formato DEALS")
                    
                    print(f"📝 DEBUG: Dati preparati: {deals_data}")
                    
                    # Se normal_price è 0, usa sale_price
                    if deals_data['normal_price'] <= 0 and deals_data['sale_price'] > 0:
                        deals_data['normal_price'] = deals_data['sale_price']
                        print(f"🔧 DEBUG: Corretto normal_price a {deals_data['normal_price']}")
                    
                    # Tronca nome se troppo lungo
                    if len(deals_data['game_name']) > 200:
                        deals_data['game_name'] = deals_data['game_name'][:197] + '...'
                    
                    # Validazione base
                    if not deals_data['external_id'] or not deals_data['game_name']:
                        print(f"⚠️ DEBUG: Dati incompleti, saltato")
                        continue
                    
                    print(f"💾 DEBUG: Tentativo salvataggio con external_id='{deals_data['external_id']}'")
                    
                    # Crea o aggiorna
                    deal, created = DealsList.objects.update_or_create(
                        external_id=deals_data['external_id'],
                        defaults=deals_data
                    )
                    
                    print(f"✅ DEBUG: Salvato! ID={deal.id}, created={created}")
                    print(f"🔍 DEBUG: Deal salvato - name='{deal.game_name}', sale_price={deal.sale_price}")
                    
                    if created:
                        created_count += 1
                    else:
                        updated_count += 1
                    
                    # Ferma dopo 3 elementi per debug
                    if i >= 2:
                        print("🛑 DEBUG: Fermato dopo 3 elementi per debug")
                        break
                
                except Exception as e:
                    print(f"❌ DEBUG: Errore elemento {i}: {e}")
                    print(f"📋 DEBUG: Dati elemento con errore: {game}")
                    import traceback
                    traceback.print_exc()
                    continue
        
        print(f"✅ DEBUG: Sync completato - {created_count} creati, {updated_count} aggiornati")
        
        # Verifica cosa c'è ora nel database
        total_in_db = DealsList.objects.count()
        print(f"🔍 DEBUG: Totale deals nel database dopo sync: {total_in_db}")
        
        return Response({
            "message": "Sincronizzazione completata",
            "created": created_count,
            "updated": updated_count,
            "data_source": data_source,
            "total_in_db": total_in_db
        })
    
    @action(detail=False, methods=['get'])
    def fetch_live_deals(self, request):
        """Recupera deals direttamente dall'API senza salvarli"""
        print("🔄 DEBUG: Inizio fetch_live_deals")
        
        # Prima prova con games, poi con deals se games è vuoto
        games_data = DealListService.fetch_games()
        data_source = "games"
        
        if not games_data:
            games_data = DealListService.fetch_deals()
            data_source = "deals"
        
        if not games_data:
            return Response(
                {"error": "Impossibile recuperare i giochi dall'API CheapShark"}, 
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )
        
        print(f"📋 DEBUG: fetch_live_deals - Ricevuti {len(games_data)} elementi")
        print(f"🔍 DEBUG: fetch_live_deals - Primo elemento: {games_data[0] if games_data else 'NESSUNO'}")
        
        formatted_deals = []
        for i, game in enumerate(games_data):
            try:
                if data_source == "games" or 'gameID' in game:
                    # Formato da /games endpoint
                    formatted_deal = {
                        'external_id': str(game.get('gameID', f'game_{i}')),
                        'game_name': game.get('external', 'Nome non disponibile'),
                        'image_url': game.get('thumb', ''),
                        'sale_price': self._safe_conversion(game.get('cheapest', 0)),
                        'normal_price': self._safe_conversion(game.get('cheapest', 0)) * 1.5
                    }
                else:
                    # Formato da /deals endpoint
                    formatted_deal = {
                        'external_id': str(game.get('dealID', f'deal_{i}')),
                        'game_name': game.get('title', 'Nome non disponibile'),
                        'image_url': game.get('thumb', ''),
                        'sale_price': self._safe_conversion(game.get('salePrice', 0)),
                        'normal_price': self._safe_conversion(game.get('normalPrice', 0))
                    }
                
                formatted_deals.append(formatted_deal)
                
                # Debug primi 3 elementi
                if i < 3:
                    print(f"📝 DEBUG: fetch_live_deals elemento {i}: {formatted_deal}")
                
            except Exception as e:
                print(f"⚠️ DEBUG: fetch_live_deals errore elemento {i}: {e}")
                continue
        
        return Response({
            "count": len(formatted_deals),
            "deals": formatted_deals,
            "data_source": data_source
        })
    
    @action(detail=False, methods=['delete'])
    def clear_all_deals(self, request):
        """Elimina tutti i deals per debug"""
        count = DealsList.objects.count()
        DealsList.objects.all().delete()
        return Response({
            "message": f"Eliminati {count} deals"
        })
    
    @action(detail=False, methods=['get'])
    def debug_database(self, request):
        """Debug del contenuto del database"""
        total = DealsList.objects.count()
        deals = DealsList.objects.all()[:5]
        
        deals_info = []
        for deal in deals:
            deals_info.append({
                "id": deal.id,
                "external_id": deal.external_id,
                "game_name": deal.game_name,
                "sale_price": str(deal.sale_price),
                "normal_price": str(deal.normal_price),
                "image_url": deal.image_url
            })
        
        return Response({
            "total_deals": total,
            "first_5_deals": deals_info
        })