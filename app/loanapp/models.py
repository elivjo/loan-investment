from datetime import datetime, timezone
from django.conf import settings
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from rest_framework.authtoken.models import Token


# Create your models here.

class Loan(models.Model):
    identifier = models.CharField(max_length=100)
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
    portfolio = models.ForeignKey('Portfolio', on_delete=models.CASCADE, related_name='portfolios')

    class Meta:
        unique_together = ('portfolio', 'identifier')

    def __str__(self):
        return self.identifier


class CashFlow(models.Model):
    FLOWTYPE = (
        ('Funding', 'Funding'),
        ('Interest', 'Interest Repayment'),
        ('Principal', 'Principal Repayment'),
    )

    loan = models.ForeignKey('Loan', on_delete=models.CASCADE)
    reference_date = models.DateField()
    type = models.CharField(max_length=100, choices=FLOWTYPE)
    amount = models.FloatField()

    def __str__(self):
        return self.type


class Portfolio(models.Model):

    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name


# @receiver(post_save, sender=settings.AUTH_USER_MODEL)
# def create_auth_token(sender, instance=None, created=False, **kwargs):
#     if created:
#         Token.objects.create(user=instance)
