#!/usr/bin/env python
# coding: utf-8

import os
from pprint import pprint
import urllib3
import json
import pandas as pd
from ynab_utility.eval_query import eval_query, eval_node
import ast
import numpy as np
pd.set_option('display.max_rows', 500)

ynab_token = os.environ.get('YNAB_TOKEN')
budget_id  = os.environ.get('YNAB_BUDGETID') # str | The ID of the Budget.
account_id = os.environ.get('YNAB_ACCOUNTID') # str | The ID of the Account.

http = urllib3.PoolManager()
r = http.request('GET',
                 f'https://api.youneedabudget.com/v1/budgets/{budget_id}/transactions',
                 headers={'Authorization': f'Bearer {ynab_token}'})

result_transactions = json.loads(r.data)
df_transactions = pd.DataFrame(result_transactions['data']['transactions'])


r = http.request('GET',
                 f'https://api.youneedabudget.com/v1/budgets/{budget_id}/categories',
                 headers={'Authorization': f'Bearer {ynab_token}'})
result_categories = json.loads(r.data)


df_categories = pd.DataFrame([category 
                              for category_group in result_categories['data']['category_groups'] \
                              for category in category_group['categories']])

assert(len(set(df_categories.name)) == len(df_categories.name))
category_lookup = {nm:id for nm, id in zip(df_categories.name, df_categories.id)}
for nm, id in sorted(list(category_lookup.items())):
    print(f"    {'`'+nm+'`':<33s}:{id}")


df_todo = df_transactions[~df_transactions.approved]
df_todo.assign(amount_usd=lambda df: df.amount / 1000.)[["date","amount_usd","import_payee_name"]]


with open("config.json") as f:
    rules = json.loads(''.join(f.readlines()))

df_transactions['autocat'] = np.nan
df_transactions['autoid']  = np.nan
todo_mask = (
    (df_transactions.approved == False)
)

for this_cat, this_rule in rules['custom']:
    if not this_cat in category_lookup:
        print(f"Did not find `{this_cat}` in categories, skipping")
        continue    
    this_cat_id = category_lookup[this_cat]
    print(f'{this_cat:<20s}: {this_cat_id} {this_rule}')
    match_mask = eval_node(ast.parse(this_rule, '<string>', mode='eval'), df_todo) & todo_mask
    df_transactions.loc[match_mask, 'autocat'] = this_cat
    df_transactions.loc[match_mask, 'autoid']  = this_cat_id


for this_cat in rules:
    if not this_cat in category_lookup:
        print(f"Did not find `{this_cat}` in categories, skipping")
        continue
    this_cat_id = category_lookup[this_cat]
    print(this_cat_id)
    for this_field in rules[this_cat]:
        for this_term in rules[this_cat][this_field]:
            search_str = f"'||{this_term}||' in {this_field}"
            print(f'{this_cat:>40s}: {search_str}')
            match_mask = eval_node(ast.parse(search_str, '<string>', mode='eval'), df_todo) & todo_mask
            df_transactions.loc[match_mask, 'autocat'] = this_cat
            df_transactions.loc[match_mask, 'autoid']  = this_cat_id


df_transactions['amount_usd'] = df_transactions.amount / 1000
cols=['id','date','amount_usd','approved','account_name','category_name',
      'autocat', 'autoid', 'import_payee_name', 'import_payee_name_original']
# display(df_transactions.loc[~df_transactions.autocat.isna(), cols])

df_leftover = df_transactions[todo_mask & df_transactions.autocat.isna()]
display(df_leftover[cols])


## INSPECT RESULTS
from datetime import datetime

df_matched = df_transactions[todo_mask & ~df_transactions.autocat.isna()].copy()
df_matched.to_csv(f"~/Downloads/{datetime.now().strftime('%Y-%m-%dT%H-%M-%S')}-transaction_matched_log.csv")

for cat in df_matched.autocat.unique():
    print("\n\n\n" + cat)
    display(df_matched.loc[df_matched.autocat == cat, ["date", "amount_usd", "import_payee_name", "account_name"]])


import os

## Remove already-processed records
ynab_path = os.path.join(os.getenv('HOME'), '.ynab')
df_processed = pd.concat([pd.read_csv(os.path.join(ynab_path, f))
                          for f in os.listdir(ynab_path)
                          if f.endswith('updated_transactions.csv')])
df_outer = df_matched.merge(df_processed[["id"]], on="id", how="outer", indicator=True)
df_remaining = df_outer[(df_outer._merge == 'left_only')].drop('_merge', axis=1)
display(df_remaining)

dict_remaining = df_remaining.to_dict(orient='records')


import time
from datetime import datetime

outcome = []
for record in dict_remaining:
    # print(record)
    transaction_id = record['id']
    
    request_data =  {
        'category_id': record['autoid'],
        'memo': f'Categorized programmatically, original category: {record["category_name"]}',
        'approved': True
    }
    this_request = {'transaction': request_data}
    r = http.request('PUT',
                     f'https://api.youneedabudget.com/v1/budgets/{budget_id}/transactions/{transaction_id}',
                     headers={'Authorization': f'Bearer {ynab_token}',
                              'Content-Type':'application/json'},
                     body=json.dumps(this_request))
    outcome.append(r.data)
    print(r.data)
    time.sleep(.01)
    
df_written = pd.DataFrame([json.loads(out)['data']['transaction'] for out in outcome])
df_written.to_csv(os.path.join(ynab_path,f"{datetime.now().strftime('%Y-%m-%dT%H-%M-%S')}-updated_transactions.csv"))




