from django.urls import path
from .views import  UploadFileView, LoanView, CashFlowView, StatisticsView


urlpatterns = [
    path('loan/', LoanView.as_view(), name='loan'),
    path('cashflow/', CashFlowView.as_view(), name='cashflow'),
    path('upload/', UploadFileView.as_view(), name='upload-file'),
    path('stats/', StatisticsView.as_view(), name='stats'),

]