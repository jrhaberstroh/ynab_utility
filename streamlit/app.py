import os
import signal
import datetime

from pprint import pprint
from pathlib import Path
import urllib3
import json
import pandas as pd
from ynab_utility.eval_query import eval_query, eval_node
import ast
import numpy as np
from appdirs import user_cache_dir
import streamlit as st

ynab_token = os.environ.get('YNAB_TOKEN')
budget_id  = os.environ.get('YNAB_BUDGETID') # str | The ID of the Budget.
account_id = os.environ.get('YNAB_ACCOUNTID') # str | The ID of the Account.
ynab_path  = user_cache_dir("ynab_utility")

def timeout_10(func):
    def timeout_func(*args, **kwargs):
        signal.alarm(10)
        result = func(*args, **kwargs)
        signal.alarm(0)
        return result
    return timeout_func

@st.cache_data
@timeout_10
def load_ynab_transactions():
    http = urllib3.PoolManager()
    r = http.request('GET',
                     f'https://api.youneedabudget.com/v1/budgets/{budget_id}/transactions',
                     headers={'Authorization': f'Bearer {ynab_token}'})
    
    result_transactions = json.loads(r.data)
    df_transactions = pd.DataFrame(result_transactions['data']['transactions'])
    print(f"Loaded {df_transactions.shape[0]} lines.")
    return df_transactions

try:
    df_transactions = load_ynab_transactions()
except TimeoutError:
    print("Timeout encountered. Using cache instead")
    df_transactions = pd.read_csv(os.path.join(ynab_path, 'transaction_cache.csv'))





df_tx = df_transactions.assign(amount_usd=lambda x: x.amount / 1000)

df=df_tx
df=df.assign(
    date=lambda x: pd.to_datetime(x['date']),
    week=lambda x: x['date'].dt.to_period('W'),
    month=lambda x: x['date'].dt.to_period('M'),
)

date = (datetime.datetime.now() - datetime.timedelta(weeks=3)).isoformat()
st.write(
    df.merge(df
             .groupby(['week', 'category_name'])
             .agg(amount=pd.NamedAgg(column='amount', aggfunc='min')),
        on=['week', 'category_name', 'amount'],
        how='inner',
    ).query("category_name in ['John', 'Kendall', 'Paul', 'Domestic Purchases '] | "
           "category_name.str.startswith('Amazon') | "            
            "category_name.str.startswith('Outings')")
    .query(f"date > '{date}'")
    [['week', 'category_name', 'amount_usd', 'import_payee_name', 'account_name']]
    .assign(
        week = lambda x: x.week.astype(str)
            .str.replace('/', ' to ')
            .str.replace('2023-','')
            .str.replace('-', '/'),
        expense = lambda x: '$' + x.amount_usd.abs().astype(str) + ' ' + x.import_payee_name
    )
    .pivot_table(index='week', columns='category_name', values='expense', aggfunc=lambda x:' '.join(x))
    .sort_values(['week'], ascending=False)
)





weeks_back = st.slider( "Num weeks lag", min_value=3, max_value=52, value=14,)
wks = st.slider( "Num weeks to hide", min_value=0, max_value=52, value=0,)
accts = st.multiselect("Budget Categories", options=df.category_name.unique(),)
df_filt = df[
    df.category_name.isin(accts) & 
    (df.date.dt.date >= datetime.date.today() - datetime.timedelta(weeks=weeks_back)) & 
    (df.date.dt.date <= datetime.date.today() - datetime.timedelta(weeks=wks))
]
df_filt.amount_usd = -df_filt.amount_usd
df_filt = df_filt.loc[:, ['category_name', 'date', 'amount_usd']]
df_pivot = (
    df_filt
    .groupby('category_name')
    .resample('M', on='date')
    .sum().reset_index()
    .pivot(index='date', columns='category_name', values='amount_usd')
)
if len(accts) > 0:
    st.bar_chart(df_pivot)
else:
    st.write("no data")

weeks_back = st.slider( "Num weeks lag (weeks)", min_value=3, max_value=52, value=14,)
wks = st.slider( "Num weeks to hide (weeks)", min_value=0, max_value=52, value=0,)
accts = st.multiselect("Budget Categories (weeks)", options=df.category_name.unique(),)
df_filt = df[
    df.category_name.isin(accts) & 
    (df.date.dt.date >= datetime.date.today() - datetime.timedelta(weeks=weeks_back)) & 
    (df.date.dt.date <= datetime.date.today() - datetime.timedelta(weeks=wks))
]
df_filt.amount_usd = -df_filt.amount_usd
df_filt = df_filt.loc[:, ['category_name', 'date', 'amount_usd']]
df_pivot = (
    df_filt
    .groupby('category_name')
    .resample('M', on='date')
    .sum().reset_index()
    .pivot(index='date', columns='category_name', values='amount_usd')
)
df_pivot = (
    df_filt
    .groupby('category_name')
    .resample('W-Mon', on='date')
    .sum().reset_index()
    .pivot(index='date', columns='category_name', values='amount_usd')
)
if len(accts) > 0:
    st.bar_chart(df_pivot)
else:
    st.write("no data")



