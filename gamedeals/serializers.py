from rest_framework import serializers
from .models import DealsList, SyncLog

class DealsListSerializer(serializers.ModelSerializer):
    
    class Meta:
        model = DealsList
        fields = '__all__'
        
class SyncLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = SyncLog
        fields = '__all__'