from rest_framework import serializers
from .models import User, KYC


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['referal_id', 'name', 'email', 'phone', 'package']


class KYCSerializer(serializers.ModelSerializer):
    class Meta:
        model = KYC
        fields = '__all__'


# class EarningSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = Earning
#         fields = '__all__'


# class WithdrawSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = Withdraw
#         fields = '__all__'
