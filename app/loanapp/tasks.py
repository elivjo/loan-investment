from __future__ import absolute_import, unicode_literals

import csv
import io
import pandas as pd
from celery import shared_task
from .services import FileServices


# asynchronously files
@shared_task
def processing_files(cashflow_df, loan_df, portfolio_id):

    FileServices.upload_files(cashflow_df, loan_df, portfolio_id)
