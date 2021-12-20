
from __future__ import absolute_import, unicode_literals

from celery import shared_task

from .models import Loan, CashFlow
import io, csv, pandas as pd

from .api.permissions import UserPermission
from .services import FileServices, ViewServices, StatService


@shared_task
def processing_files(cashflow_df, loan_df):
    cashflow_df = pd.read_json(cashflow_df)
    loan_df = pd.read_json(loan_df)

    for _, loan in loan_df.iterrows():
        cashflows_df_filter = cashflow_df[cashflow_df['loan_identifier'] == loan.get('identifier')]
        cashflow_type_funding = cashflows_df_filter[cashflows_df_filter['type'] == 'Funding']
        cashflow_type_repayment = cashflows_df_filter[cashflows_df_filter['type'] == 'Repayment']
        invested_amount = FileServices.calculate_investment_amount(cashflow_type_funding)
        investment_date = FileServices.calculate_investment_date(cashflow_type_funding)
        expected_interest_amount = FileServices.calculate_expected_interest_amount(loan, invested_amount)
        is_closed = FileServices.loan_is_closed(cashflow_type_repayment, invested_amount,
                                                expected_interest_amount)
        expected_irr = FileServices.calculate_expected_irr(loan, cashflow_type_funding, cashflow_type_repayment,
                                                           expected_interest_amount)
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