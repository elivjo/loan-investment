from  rest_framework import  serializers
from ..models import Loan, CashFlow


class FileUploadSerializer(serializers.Serializer):
    """Serializing file to upload in application"""
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
    #loan = serializers.CharField()
    class Meta:
        model = CashFlow
        fields = "__all__"
