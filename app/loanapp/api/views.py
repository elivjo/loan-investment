from django.db import transaction
from django.db.models import Sum, Count, F
from rest_framework.response import Response
from rest_framework.views import APIView

from ..models import Loan, CashFlow
from .serializer import LoanSerializer, CashFlowSerializer, FileUploadSerializer
import io, csv, pandas as pd
from rest_framework import generics, status
from rest_framework.generics import ListCreateAPIView
from .permissions import UserPermission
from ..services import FileServices, ViewServices, StatService



class UploadFileView(generics.CreateAPIView):
    serializer_class = FileUploadSerializer

    def post(self, request, *args, **kwargs):
        with transaction.atomic():
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid()
            loan_file = serializer.validated_data['loan_file']
            cashflow_file = serializer.validated_data['cashflow_file']
            cashflow_df = pd.read_csv(cashflow_file)
            loan_df = pd.read_csv(loan_file)
            # merged_df = pd.merge(cashflow_df, loan_df, on="loan_identifier")
            for _, loan in loan_df.iterrows():
                cashflows_df_filter = cashflow_df[cashflow_df['loan_identifier'] == loan.get('identifier')]
                cashflow_type_funding = cashflows_df_filter[cashflows_df_filter['type'] == 'Funding']
                cashflow_type_repayment = cashflows_df_filter[cashflows_df_filter['type'] == 'Repayment']
                invested_amount = FileServices.calculate_investment_amount(cashflow_type_funding)
                investment_date = FileServices.calculate_investment_date(cashflow_type_funding)
                expected_interest_amount = FileServices.calculate_expected_interest_amount(loan, invested_amount)
                is_closed = FileServices.loan_is_closed(cashflow_type_repayment, invested_amount, expected_interest_amount)
                expected_irr = FileServices.calculate_expected_irr(loan, cashflow_type_funding, cashflow_type_repayment, expected_interest_amount)
                realized_irr = FileServices.calculate_realized_irr(loan, cashflow_type_funding, cashflow_type_repayment)

                new_loan = Loan(
                    identifier=loan['identifier'],
                    issue_date=loan['issue_date'],
                    total_amount=loan['total_amount'],
                    rating=loan['rating'],
                    maturity_date=loan['maturity_date'],
                    total_expected_interest_amount=loan['total_expected_interest_amount'],
                    invested_amount=invested_amount,
                    investment_date=investment_date,
                    expected_interest_amount=expected_interest_amount,
                    is_closed=is_closed,
                    expected_irr=expected_irr,
                    realized_irr=realized_irr
                )
                new_loan.save()

            for _, row in cashflow_df.iterrows():
                loan_cf = Loan.objects.get(identifier=row['loan_identifier'])
                new_cashflow = CashFlow(
                    loan=loan_cf,
                    reference_date=row['reference_date'],
                    type=row['type'],
                    amount=row['amount']
                )
                new_cashflow.save()

            return Response({'status': 'uploaded successfully'}, status.HTTP_201_CREATED)


class LoanView(APIView):
    serializer_class = LoanSerializer
    permission_classes = (UserPermission,)

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
    permission_classes = (UserPermission,)

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
                loan.is_closed = ViewServices.loan_is_closed(amount_cashflow, loan, loan.expected_interest_amount, cashflow_type)
                loan.expected_irr = ViewServices.calculate_xirr(loan, cashflow_type)
                loan.realized_irr = ViewServices.calculate_irr(loan)

                loan.save()

                return Response(serializer.data, status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class StatisticsView(APIView):

    permission_classes = (UserPermission,)

    def get(self, request, format=None):

        total_invested_amount = Loan.objects.aggregate(Sum('invested_amount'))['invested_amount__sum']
        total_loans = Loan.objects.count()
        current_invested_amount = Loan.objects.filter(is_closed=False).aggregate(Sum('invested_amount'))['invested_amount__sum']
        total_repaid_amount = CashFlow.objects.filter(type='Repayment').aggregate(Sum('amount'))['amount__sum']
        avg_realized_irr = StatService.calc_weighted_irr()

        data = {
            "total_loans": total_loans,
            "total_invested_amount": total_invested_amount,
            "current_invested_amount": current_invested_amount,
            "total_repaid_amount": total_repaid_amount,
            "avg_realized_irr": avg_realized_irr
        }
        return Response(data)