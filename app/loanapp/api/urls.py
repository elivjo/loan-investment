from django.urls import path
from .views import  UploadFileView, LoanView, CashFlowView, StatisticsView
from rest_framework.authtoken.views import obtain_auth_token
from rest_framework.authtoken import views

urlpatterns = [
    path('loan/', LoanView.as_view(), name='loan'),
    path('cashflow/', CashFlowView.as_view(), name='cashflow'),
    path('upload/', UploadFileView.as_view(), name='upload-file'),
    path('stats/', StatisticsView.as_view(), name='stats'),

]