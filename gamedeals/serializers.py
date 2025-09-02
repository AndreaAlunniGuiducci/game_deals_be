from rest_framework import serializers
from .models import DealsList, SyncLog, StoreInfo
from django.contrib.auth.models import User
from django.contrib.auth.hashers import make_password

class StoreInfoSerializer(serializers.ModelSerializer):
    class Meta:
        model = StoreInfo
        fields = '__all__'
class DealsListSerializer(serializers.ModelSerializer):
    
    class Meta:
        model = DealsList
        fields = '__all__'
        
class SyncLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = SyncLog
        fields = '__all__'
        
class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ('id', 'username', 'password')

    def create(self, validated_data):
        user = User(
            username=validated_data['username'],
        )
        user.password = make_password(validated_data['password'])
        user.save()
        return user
