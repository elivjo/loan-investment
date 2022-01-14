from django.urls import path
from rest_framework.authtoken import views
from rest_framework.authtoken.views import obtain_auth_token

from .views import UploadFileView, LoanView, CashFlowView, StatisticsView, CreateToken

urlpatterns = [
    path('loan/', LoanView.as_view(), name='loan'),
    path('cashflow/', CashFlowView.as_view(), name='cashflow'),
    path('upload/', UploadFileView.as_view(), name='upload-file'),
    path('stats/', StatisticsView.as_view(), name='stats'),
    path('token/', CreateToken.as_view(), name='token'),

]
