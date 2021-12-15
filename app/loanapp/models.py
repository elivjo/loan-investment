from django.db import models
from datetime import datetime, timezone


# Create your models here.

class Loan(models.Model):

    identifier = models.CharField(max_length=100, unique=True)
    issue_date = models.DateField()
    total_amount = models.FloatField()
    rating = models.IntegerField()
    maturity_date = models.DateField()
    total_expected_interest_amount = models.FloatField()
    invested_amount = models.FloatField(null=True, blank=True)
    investment_date = models.DateField(null=True, blank=True)
    expected_interest_amount = models.FloatField(null=True, blank=True)
    is_closed = models.BooleanField(null=True, blank=True)
    expected_irr = models.FloatField(null=True, blank=True)
    realized_irr = models.FloatField(null=True, blank=True)


    def __str__(self):
        return self.identifier



class CashFlow(models.Model):

    FLOWTYPE = (
        ('Funding', 'Funding'),
        ('Repayment', 'Repayment'),
    )

    loan = models.ForeignKey('Loan', on_delete=models.CASCADE)
    reference_date = models.DateField()
    type = models.CharField(max_length=100, choices=FLOWTYPE)
    amount = models.FloatField()

    def __str__(self):
        return self.type
