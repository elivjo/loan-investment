from django.db import transaction
from django.db.models import Sum, Count, F
from rest_framework.response import Response
from rest_framework.views import APIView

from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.authtoken.models import Token
from rest_framework.permissions import IsAuthenticated

from ..models import Loan, CashFlow
from .serializer import LoanSerializer, CashFlowSerializer, FileUploadSerializer
import io, csv, pandas as pd
from rest_framework import generics, status
from rest_framework.generics import ListCreateAPIView
from .permissions import UserPermission
from ..services import FileServices, ViewServices, StatService
from django.core.cache import cache

from ..tasks import processing_files



class UploadFileView(generics.CreateAPIView):
    serializer_class = FileUploadSerializer
    permission_classes = (UserPermission, IsAuthenticated,)

    def post(self, request, *args, **kwargs):
        with transaction.atomic():
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid()
            loan_file = serializer.validated_data['loan_file']
            loan_df = pd.read_csv(loan_file)
            cashflow_file = serializer.validated_data['cashflow_file']
            cashflow_df = pd.read_csv(cashflow_file)

            processing_files.delay(cashflow_df.to_json(), loan_df.to_json())

            return Response({'status': 'uploaded successfully'}, status.HTTP_201_CREATED)


class LoanView(APIView):
    serializer_class = LoanSerializer
    permission_classes = (UserPermission, IsAuthenticated,)

    def get_queryset(self):
        queryset = Loan.objects.all()
        identifier = self.request.query_params.get('identifier', None)
        if identifier is not None:
            queryset = queryset.filter(identifier__istartswith=identifier)
        return queryset

    def get(self, request, format=None):
        queryset = self.get_queryset()
        serializer = LoanSerializer(queryset, many=True)
        return Response(serializer.data)

    # def post(self, request, format=None):
    #     serializer = LoanSerializer(data=request.data)
    #     if serializer.is_valid():
    #         serializer.save()
    #         return Response(serializer.data, status=status.HTTP_201_CREATED)
    #     return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class CashFlowView(APIView):
    serializer_class = CashFlowSerializer
    permission_classes = (UserPermission, IsAuthenticated,)

    def get_queryset(self):
        queryset = CashFlow.objects.all()
        type = self.request.query_params.get('type', None)
        if type is not None:
            queryset = queryset.filter(type__istartswith=type)
        return queryset

    def get(self, request, format=None):
        queryset = self.get_queryset()
        serializer = CashFlowSerializer(queryset, many=True)
        return Response(serializer.data)

    def post(self, request, format=None):
        with transaction.atomic():
            serializer = CashFlowSerializer(data=request.data)
            if serializer.is_valid():
                serializer.save()
                loan_id = request.data['loan']
                amount_cashflow = float(request.data['amount'])
                cashflow_type = request.data['type']

                loan = Loan.objects.filter(id=loan_id).first()
                loan.invested_amount = ViewServices.calculate_investment_amount(loan)
                loan.expected_interest_amount = ViewServices.calculate_expected_interest_amount(loan)
                loan.investment_date = ViewServices.calculate_investment_date(loan)
                loan.is_closed = ViewServices.loan_is_closed(amount_cashflow, loan, loan.expected_interest_amount,
                                                             cashflow_type)
                loan.expected_irr = ViewServices.calculate_xirr(loan, cashflow_type)
                loan.realized_irr = ViewServices.calculate_irr(loan)

                loan.save()

                return Response(serializer.data, status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class StatisticsView(APIView):
    permission_classes = (UserPermission, IsAuthenticated,)

    def get(self, request, format=None):

        total_invested_amount = StatService.get_total_invested_amount()
        total_loans = StatService.get_total_loans()
        current_invested_amount = StatService.get_current_invested_amount()
        total_repaid_amount = CashFlow.objects.filter(type='Repayment').aggregate(Sum('amount'))['amount__sum']
        get_avg_realized_irr = StatService.calc_weighted_irr()
        cache.set('avg_realized_irr', get_avg_realized_irr)
        avg_realized_irr = cache.get('avg_realized_irr', 0)

        data = {
            "total_loans": total_loans,
            "total_invested_amount": total_invested_amount,
            "current_invested_amount": current_invested_amount,
            "total_repaid_amount": total_repaid_amount,
            "avg_realized_irr": avg_realized_irr
        }

        return Response(data)