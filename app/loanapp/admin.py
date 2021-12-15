from django.contrib import admin

# Register your models here.
from .models import Loan, CashFlow

admin.site.register(Loan)
admin.site.register(CashFlow)
