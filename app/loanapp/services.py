import csv
import pandas as pd
from datetime import datetime
from django.core import serializers
from django.core.cache import cache
from django.db.models import Sum
from pyxirr import xirr, irr

from .models import CashFlow, Loan, Portfolio


class FileServices:
    """Calculating functions for uploading files"""

    @staticmethod
    def upload_files(cashflow_df, loan_df, portfolio_id):
        cashflow_df = pd.read_json(cashflow_df)
        loan_df = pd.read_json(loan_df)
    
        for _, loan in loan_df.iterrows():
            cashflows_df_filter = cashflow_df[cashflow_df['loan_identifier'] == loan.get('identifier')]
            cashflow_type_funding = cashflows_df_filter[cashflows_df_filter['type'] == 'Funding']
            cashflow_type_repayment = cashflows_df_filter[cashflows_df_filter['type'] == 'Principal'] #Repayment -> Principal
            cashflow_type_interest = cashflows_df_filter[cashflows_df_filter['type'] == 'Interest']
            invested_amount = FileServices.calculate_investment_amount(cashflow_type_funding)
            investment_date = FileServices.calculate_investment_date(cashflow_type_funding)
            expected_interest_amount = FileServices.calculate_expected_interest_amount(loan, invested_amount)
            is_closed = FileServices.loan_is_closed(cashflow_type_repayment,cashflow_type_interest ,invested_amount,
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
                realized_irr=realized_irr,
                portfolio_id=portfolio_id
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

    @staticmethod
    def calculate_investment_amount(cashflow):
        return float(cashflow['amount'].values)

    @staticmethod
    def calculate_investment_date(cashflow):
        return cashflow["reference_date"].iloc[0]

    @staticmethod
    def calculate_expected_interest_amount(loan, invested_amount):
        total_expected_interest_amount = loan.get('total_expected_interest_amount')
        invested_amount = abs(invested_amount)
        total_amount = loan.get('total_amount')
        return float(total_expected_interest_amount * (invested_amount / total_amount))

    @staticmethod
    def loan_is_closed(cashflow_principal,cashflow_interest, invested_amount, expected_interest_amount):
        principal_repaid = cashflow_principal['amount'].values
        interest_repaid = cashflow_interest['amount'].values
        if principal_repaid >= invested_amount and interest_repaid >= expected_interest_amount:
            return True
        return False

    @staticmethod
    def calculate_expected_irr(loan, cashflow_type_funding, cashflow_type_repayment, expected_interest_amount):
        if cashflow_type_repayment['amount'].values != None:
            reference_date = cashflow_type_funding['reference_date'].iloc[0]
            convert_rf_date = datetime.strptime(reference_date, '%Y-%m-%d')
            maturity_date = loan['maturity_date']
            convert_m_date = datetime.strptime(maturity_date, '%Y-%m-%d')
            amount = abs(cashflow_type_funding[
                             'amount'].values + expected_interest_amount)  #ASK: nqs duhet vetem amount ne abs jo e gjith shprehja
            invested_amount_funding = cashflow_type_funding['amount'].values
            date_list = [convert_m_date, convert_rf_date]
            amount_list = [invested_amount_funding, amount]
            return xirr(date_list, amount_list)
        return 0

    @staticmethod
    def calculate_realized_irr(loan, cashflow_type_funding, cashflow_type_repayment):
        if cashflow_type_repayment['amount'].values != None:
            date_ref_funding = cashflow_type_funding['reference_date'].iloc[0]
            convert_f_date = datetime.strptime(date_ref_funding, '%Y-%m-%d')
            date_ref_repayment = cashflow_type_repayment['reference_date'].iloc[0]
            convert_rf_date = datetime.strptime(date_ref_repayment, '%Y-%m-%d')
            amount_funding = cashflow_type_funding['amount'].values
            amount_repayment = cashflow_type_repayment['amount'].values
            date_list = [convert_f_date, convert_rf_date]
            amount_list = [amount_funding, amount_repayment]
            return xirr(date_list, amount_list)  # the xirr function cause should consider
        return 0  # also dates but the real function is 'irr(amount_list)'


class ViewServices:
    """Calculating functions for app view"""

    @staticmethod
    def create_new_cashflow(loan_id, amount_cashflow, cashflow_type):
        loan = Loan.objects.filter(id=loan_id).first()
        loan.invested_amount = ViewServices.calculate_investment_amount(loan)
        loan.expected_interest_amount = ViewServices.calculate_expected_interest_amount(loan)
        loan.investment_date = ViewServices.calculate_investment_date(loan)
        loan.is_closed = ViewServices.loan_is_closed(amount_cashflow, loan, loan.expected_interest_amount,
                                                     cashflow_type)
        loan.expected_irr = ViewServices.calculate_xirr(loan, cashflow_type, amount_cashflow)
        loan.realized_irr = ViewServices.calculate_irr(loan)

        loan.save()

    @staticmethod
    def calculate_investment_amount(loan):
        cashflow = CashFlow.objects.filter(loan=loan).filter(type='Funding').last()
        invested_amount = loan.invested_amount + cashflow.amount
        return invested_amount  # kthen vlere edhe per type te tjera sa her qe krijohet nje cashflow

    @staticmethod
    def calculate_investment_date(loan):
        cashflow = CashFlow.objects.filter(loan=loan).filter(type='Funding').order_by('reference_date').first()
        invested_date = cashflow.reference_date
        return invested_date

    @staticmethod
    def calculate_expected_interest_amount(loan):
        return abs(loan.total_expected_interest_amount * (loan.invested_amount / loan.total_amount))

    @staticmethod
    def loan_is_closed(total_repaid, loan, expected_interest_amount, cashflow_type):
        cf_principal_repayment = CashFlow.objects.filter(loan=loan).filter(type='Principal')
        principal_repaid = cf_principal_repayment.aggregate(Sum('amount'))['amount__sum'] if cf_principal_repayment else 0
        cf_interest_repayment = CashFlow.objects.filter(loan=loan).filter(type='Interest')
        interest_repaid = cf_interest_repayment.aggregate(Sum('amount'))['amount__sum'] if cf_interest_repayment else 0
        if principal_repaid >= loan.invested_amount and interest_repaid >= loan.expected_interest_amount:
            return True
        return False

    @staticmethod
    def calculate_xirr(loan, cashflow_type, funding_amount):
        loan_obj = Loan.objects.filter(identifier=loan).first()
        invested_amount = ViewServices.calculate_investment_amount(loan)
        expected_interest_amount = ViewServices.calculate_expected_interest_amount(loan)
        amount = abs(invested_amount + expected_interest_amount)
        maturity_date = loan_obj.maturity_date
        investment_date = ViewServices.calculate_investment_date(loan)
        date_list_xirr = [maturity_date, investment_date]
        amount_list_xirr = [invested_amount, amount]
        return xirr(date_list_xirr, amount_list_xirr)

    @staticmethod
    def calculate_irr(loan):
        cf_funding = CashFlow.objects.filter(loan=loan).filter(type='Funding').first()
        cf_repayment = CashFlow.objects.filter(loan=loan).filter(type='Principal').first()
        cf_funding_date = cf_funding.reference_date
        cf_funding_amount = cf_funding.amount
        cf_repayment_date = cf_repayment.reference_date
        cf_repayment_amount = cf_repayment.amount
        expected_amount = abs(cf_funding_amount) + loan.expected_interest_amount
        if cf_repayment_amount > expected_amount:
            amount_list = [cf_funding_amount, cf_repayment_amount]
            date_list = [cf_funding_date, cf_repayment_date]
            return xirr(date_list, amount_list)
        return 0


class StatService:
    """ Calculating functions for Stats APIView"""

    @staticmethod
    def calc_weighted_irr():
        total_inv = Loan.objects.filter(is_closed=True).aggregate(Sum('invested_amount'))['invested_amount__sum']
        loans = Loan.objects.filter(is_closed=True).values_list('invested_amount', 'realized_irr')
        avg = 0
        for loan in loans:
            avg += loan[0] * loan[1] / total_inv
        return avg / abs(total_inv)

    @staticmethod
    def get_total_invested_amount():
        if cache.get('total_invested_amount'):
            print('From CACHE')
            total_invested_amount = cache.get('total_invested_amount', 0)
        else:
            try:
                total_invested_amount = Loan.objects.aggregate(Sum('invested_amount'))['invested_amount__sum']
                cache.set('total_invested_amount', total_invested_amount)
                print('From DB')
            except:
                print('error')
        return total_invested_amount

    @staticmethod
    def get_total_loans():
        if cache.get('total_loans'):
            total_loans = cache.get('total_loans', 0)
        else:
            try:
                total_loans_db = Loan.objects.count()
                cache.set('total_loans', total_loans_db)
            except:
                print('error')
        return total_loans

    @staticmethod
    def get_current_invested_amount():
        if cache.get('current_invested_amount'):
            current_invested_amount = cache.get('current_invested_amount', 0)
        else:
            try:
                current_invested_amount = Loan.objects.filter(is_closed=False).aggregate(Sum('invested_amount'))[
                        'invested_amount__sum']
                cache.set('current_invested_amount', current_invested_amount)
            except:
                print('error')
        return current_invested_amount

    @staticmethod
    def get_total_repaid_amount():
        if cache.get('total_repaid_amount'):
            total_repaid_amount = cache.get('total_repaid_amount', 0)
        else:
            try:
                total_repaid_amount = CashFlow.objects.filter(type='Repayment').aggregate(Sum('amount'))['amount__sum']
                cache.set('total_repaid_amount', total_repaid_amount)
            except:
                print('error')
        return total_repaid_amount

    @staticmethod
    def get_avg_realized_irr():
        if cache.get('avg_realized_irr'):
            avg_realized_irr = cache.get('avg_realized_irr', 0)
        else:
            try:
                avg_realized_irr = StatService.calc_weighted_irr()
                cache.set('avg_realized_irr', avg_realized_irr)
            except:
                print('error')
        return avg_realized_irr

