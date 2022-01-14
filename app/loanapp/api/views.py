from django.db import transaction
from django.db.models import Sum, Count, F
from rest_framework.response import Response
from rest_framework.views import APIView

from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.authtoken.models import Token
from rest_framework.permissions import IsAuthenticated

from ..models import Loan, CashFlow
from .serializer import LoanSerializer, CashFlowSerializer, FileUploadSerializer, AuthTokenSerializer
import io, csv, pandas as pd
from rest_framework import generics, status
from rest_framework.generics import ListCreateAPIView
from .permissions import UserPermission
from ..services import FileServices, ViewServices, StatService
from django.core.cache import cache

from ..tasks import processing_files
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.settings import api_settings
import json
from django.core import serializers
from django.forms.models import model_to_dict


class CreateToken(ObtainAuthToken):
    serializer_class = AuthTokenSerializer
    renderer_classes = api_settings.DEFAULT_RENDERER_CLASSES

    def options(self, request):
        return Response(status=status.HTTP_201_CREATED)


class UploadFileView(generics.CreateAPIView):
    serializer_class = FileUploadSerializer
    permission_classes = (UserPermission, IsAuthenticated,)

    def post(self, request, *args, **kwargs):
        with transaction.atomic():
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid()
            portfolio_id = serializer.validated_data['portfolio'].id
            loan_file = serializer.validated_data['loan_file']
            loan_df = pd.read_csv(loan_file)
            cashflow_file = serializer.validated_data['cashflow_file']
            cashflow_df = pd.read_csv(cashflow_file)

            processing_files.delay(cashflow_df.to_json(), loan_df.to_json(), portfolio_id)

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
                ViewServices.create_new_cashflow(loan_id, amount_cashflow, cashflow_type)

                return Response(serializer.data, status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class StatisticsView(APIView):
    permission_classes = (UserPermission, IsAuthenticated,)

    def get(self, request, format=None):
        total_invested_amount = StatService.get_total_invested_amount()
        total_loans = StatService.get_total_loans()
        current_invested_amount = StatService.get_current_invested_amount()
        total_repaid_amount = StatService.get_total_repaid_amount()
        avg_realized_irr = StatService.get_avg_realized_irr()

        data = {
            "total_loans": total_loans,
            "total_invested_amount": total_invested_amount,
            "current_invested_amount": current_invested_amount,
            "total_repaid_amount": total_repaid_amount,
            "avg_realized_irr": avg_realized_irr
        }

        return Response(data)
