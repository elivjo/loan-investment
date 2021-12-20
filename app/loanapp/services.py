from datetime import datetime

from django.db.models import Sum

from .models import CashFlow, Loan
from pyxirr import xirr, irr
from django.core.cache import cache



class FileServices:
    """Calculating functions for uploading files"""
    @staticmethod
    def calculate_investment_amount(cashflow):
        return int(cashflow['amount'].values)

    @staticmethod
    def calculate_investment_date(cashflow):
        return cashflow["reference_date"].iloc[0]

    @staticmethod
    def calculate_expected_interest_amount(loan, invested_amount):
        total_expected_interest_amount = loan.get('total_expected_interest_amount')
        invested_amount = abs(invested_amount)
        total_amount = loan.get('total_amount')
        return int(total_expected_interest_amount * (invested_amount / total_amount))

    @staticmethod
    def loan_is_closed(cashflow, invested_amount ,expected_interest_amount):
        total_repaid = cashflow['amount'].values
        expected_amount = invested_amount + expected_interest_amount
        if total_repaid >= expected_amount:
            return True
        return False

    @staticmethod
    def calculate_expected_irr(loan, cashflow_type_funding, cashflow_type_repayment, expexted_interest_amount):
        if cashflow_type_repayment['amount'].values != None:
            reference_date = cashflow_type_funding['reference_date'].iloc[0]
            convert_rf_date = datetime.strptime(reference_date, '%Y-%m-%d')
            maturity_date = loan['maturity_date']
            conveert_m_date = datetime.strptime(maturity_date, '%Y-%m-%d')
            amount = cashflow_type_repayment['amount'].values + expexted_interest_amount
            invested_amount_funding = cashflow_type_funding['amount'].values
            date_list = [conveert_m_date, convert_rf_date]
            amount_list = [amount,invested_amount_funding]
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
            return xirr(date_list, amount_list)     # the xirr function cause should consider
        return 0                                    # also dates but the real function is 'irr(amount_list)'


class ViewServices:
    """Calculating functions for app view"""
    @staticmethod
    def calculate_investment_amount(loan):
        cashflow = CashFlow.objects.filter(loan=loan).filter(type='Funding').first()
        invested_amount = getattr(cashflow, 'amount')
        return invested_amount

    @staticmethod
    def calculate_investment_date(loan):
        cashflow = CashFlow.objects.filter(loan=loan).filter(type='Funding').first()
        invested_date = getattr(cashflow, 'reference_date')
        return invested_date

    @staticmethod
    def calculate_expected_interest_amount(loan):
        cashflow = CashFlow.objects.filter(loan=loan).filter(type='Funding').first()
        cashflow_invested_amount = getattr(cashflow, 'amount')
        return abs(loan.total_expected_interest_amount * (cashflow_invested_amount / loan.total_amount))


    @staticmethod
    def loan_is_closed(total_repaid, loan ,expected_interest_amount, cashflow_type):
        cashflow = CashFlow.objects.filter(loan=loan).filter(type='Funding').first()
        amount_funding = getattr(cashflow, 'amount')
        if cashflow_type == 'Repayment':
            expected_amount = abs(amount_funding) + expected_interest_amount
            if total_repaid >= expected_amount:
                return True
            return False

    @staticmethod
    def calculate_xirr(loan, cashflow_type):
        if cashflow_type == 'Repayment':
            loan_obj = Loan.objects.filter(identifier=loan).first()
            invested_amount = ViewServices.calculate_investment_amount(loan)
            expected_interest_amount = ViewServices.calculate_expected_interest_amount(loan)
            amount = abs(invested_amount + expected_interest_amount)
            maturity_date = getattr(loan_obj, 'maturity_date')
            investment_date = ViewServices.calculate_investment_date(loan)
            date_list_xirr = [maturity_date, investment_date]
            amount_list_xirr = [invested_amount, amount]
            return xirr(date_list_xirr, amount_list_xirr)

    @staticmethod
    def calculate_irr(loan):

        cf_funding = CashFlow.objects.filter(loan=loan).filter(type='Funding').first()
        cf_repayment = CashFlow.objects.filter(loan=loan).filter(type='Repayment').first()
        cf_funding_date = getattr(cf_funding, 'reference_date')
        cf_funding_amount = getattr(cf_funding, 'amount')
        cf_repayment_date = getattr(cf_repayment, 'reference_date')
        cf_repayment_amount = getattr(cf_repayment, 'amount')
        amt = abs(cf_funding_amount) + loan.expected_interest_amount
        if cf_repayment_amount > amt:

            amount_list = [cf_funding_amount, cf_repayment_amount]
            date_list = [cf_funding_date, cf_repayment_date]
            return xirr(date_list, amount_list)


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
        total_loans_db = Loan.objects.count()
        cache.set('total_loans', total_loans_db)
        total_loans = cache.get('total_loans', 0)
        return total_loans

    @staticmethod
    def get_current_invested_amount():
        current_invested_amount_db = Loan.objects.filter(is_closed=False).aggregate(Sum('invested_amount'))['invested_amount__sum']
        cache.set('current_invested_amount', current_invested_amount_db)
        current_invested_amount = cache.get('current_invested_amount', 0)
        return current_invested_amount

    @staticmethod
    def get_total_repaid_amount(self):
        total_repaid_amount_db = CashFlow.objects.filter(type='Repayment').aggregate(Sum('amount'))['amount__sum']
        cache.set('total_repaid_amount', total_repaid_amount_db)
        total_repaid_amount = cache.get('total_repaid_amount', 0)
        return total_repaid_amount

