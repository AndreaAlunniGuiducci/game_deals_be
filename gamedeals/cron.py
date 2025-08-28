import logging
from django.utils import timezone
from django.db import transaction
from .models import DealsList
from .services import DealListService

logger = logging.getLogger(__name__)

def sync_cheapshark_deals():
    logger.info("Avvio sincronizzazione automatica CheapShark")
    
    try:
        games_data = DealListService.fetch_games()
        if not games_data:
            games_data = DealListService.fetch_deals()
        
        if not games_data:
            logger.error("Nessun dato recuperato dall'API")
            return
        
        created_count = 0
        updated_count = 0
        
        with transaction.atomic():
            for i, game in enumerate(games_data):
                try:
                    if 'gameID' in game:
                        deals_data = {
                            'external_id': game.get('dealID', ''),
                            'game_name': game.get('title', 'Nome non disponibile'),
                            'image_url': game.get('thumb', ''),
                            'sale_price': float(game.get('salePrice', 0)),
                            'normal_price': float(game.get('normalPrice', 0)),
                            'deal_rating': float(game.get('dealRating', 0))
                            
                        }
                    else:
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
                
                except Exception as e:
                    logger.error(f"Errore elaborazione deal {i}: {e}")
                    continue
        
        logger.info(f"Sincronizzazione completata: {created_count} creati, {updated_count} aggiornati")
        
        SyncLog.objects.create(
            sync_type='automatic',
            deals_created=created_count,
            deals_updated=updated_count,
            status='success'
        )
        
    except Exception as e:
        logger.error(f"Errore durante sincronizzazione: {e}")
        SyncLog.objects.create(
            sync_type='automatic',
            status='failed',
            error_message=str(e)
        )

def daily_sync_deals():
    logger.info("Avvio sincronizzazione giornaliera")
    sync_cheapshark_deals()
    
    total_deals = DealsList.objects.count()
    recent_deals = DealsList.objects.filter(
        created_at__gte=timezone.now() - timezone.timedelta(days=1)
    ).count()
    
    logger.info(f"Totale deals: {total_deals}, Nuovi oggi: {recent_deals}")

def cleanup_old_deals():
    logger.info("Avvio pulizia deals vecchi")
    
    cutoff_date = timezone.now() - timezone.timedelta(days=30)
    deleted_count, _ = DealsList.objects.filter(created_at__lt=cutoff_date).delete()
    
    logger.info(f"Eliminati {deleted_count} deals vecchi")
