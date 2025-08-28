from django.db import models

class DealsList(models.Model):
    external_id = models.CharField(max_length=100, unique=True)
    game_name = models.CharField(max_length=200)
    image_url = models.URLField(max_length=500)
    sale_price = models.DecimalField(max_digits=6, decimal_places=2)
    normal_price = models.DecimalField(max_digits=6, decimal_places=2)
    deal_rating = models.CharField(max_length=50, blank=True)
    def __str__(self):
        return self.game_name
    
class GameDetails(models.Model):
    game_name = models.CharField(max_length=200)
    game_rating = models.CharField(max_length=50)
    release_date = models.IntegerField()
    def __str__(self):
        return self.game_name
    
class StoreInfo(models.Model):
    store_id = models.IntegerField()
    store_name = models.CharField(max_length=100)
    def __str__(self):
        return self.store_name
    
class SyncLog(models.Model):
    SYNC_TYPES = [
        ('manual', 'Manuale'),
        ('automatic', 'Automatica'),
        ('scheduled', 'Programmata'),
    ]
    
    STATUS_CHOICES = [
        ('success', 'Successo'),
        ('failed', 'Fallita'),
        ('partial', 'Parziale'),
    ]
    
    sync_type = models.CharField(max_length=20, choices=SYNC_TYPES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    deals_created = models.IntegerField(default=0)
    deals_updated = models.IntegerField(default=0)
    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.sync_type} - {self.status} - {self.created_at}"
    

    
