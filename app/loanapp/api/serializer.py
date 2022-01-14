from django.contrib.auth import authenticate
from rest_framework import serializers

from ..models import Loan, CashFlow, Portfolio


class AuthTokenSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(
        style={'input_type': 'password'},
        trim_whitespace=False
    )

    def validate(self, attrs):
        username = attrs.get('username')
        password = attrs.get('password')

        user = authenticate(
            request=self.context.get('request'),
            username=username,
            password=password
        )

        if not user:
            msg = _('Unable to authenticate with provided credentials')
            raise serializers.ValidationError(msg, code='authentication')

        attrs['user'] = user
        return attrs

class PortfolioSerializer(serializers.ModelSerializer):
    class Meta:
        model = Portfolio
        fields = '__all__'


class FileUploadSerializer(serializers.Serializer):
    """Serializing files to upload in application"""
    portfolio = serializers.PrimaryKeyRelatedField(queryset=Portfolio.objects.all()) #many=true nqs duam te zgjedhim disa
    loan_file = serializers.FileField()
    cashflow_file = serializers.FileField()


class LoanSerializer(serializers.ModelSerializer):
    """Serializer Loan model """

    class Meta:
        model = Loan
        fields = '__all__'
        read_only_fields = ('invested_amount', 'investment_date', 'expected_interest_amount', 'is_closed',
                            'expected_irr', 'realized_irr')


class CashFlowSerializer(serializers.ModelSerializer):
    """Serializer CashFlow model"""

    # loan = serializers.CharField()
    class Meta:
        model = CashFlow
        fields = "__all__"

