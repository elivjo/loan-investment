from django.contrib import admin

# Register your models here.
from .models import Loan, CashFlow, Portfolio

admin.site.register(Loan)
admin.site.register(CashFlow)
admin.site.register(Portfolio)
