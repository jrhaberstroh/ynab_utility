import os
import ynab
from ynab.rest import ApiException
from pprint import pprint
import urllib3

import ast
from typing import Dict, Any
import operator

def eval_expression(node: ast.Expression, vars: Dict[str, Any]) -> float:
    return eval_node(node.body, vars)

def eval_constant(node: ast.Constant, vars: Dict[str, Any]) -> float:
    return node.value

def eval_name(node: ast.Name, vars: Dict[str, Any]) -> float:
    return vars[node.id]

def eval_binop(node: ast.BinOp, vars: Dict[str, Any]) -> float:
    OPERATIONS = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.BitOr: operator.or_,
    }

    left_value = eval_node(node.left, vars)
    right_value = eval_node(node.right, vars)
    apply = OPERATIONS[type(node.op)]
    return apply(left_value, right_value)

def eval_unaryop(node: ast.UnaryOp, vars: Dict[str, Any]) -> float:
    OPERATIONS = {
        ast.USub: operator.neg,
    }

    operand_value = eval_node(node.operand, vars)
    apply = OPERATIONS[type(node.op)]
    return apply(operand_value)

def eval_compare(node: ast.BinOp, vars: Dict[str, Any]) -> float:
    OPERATIONS = {
        ast.Eq: operator.eq,
    }

    results = []
    for op, right_value in zip(node.ops, node.comparators):
        left_value = eval_node(node.left, vars)
        right_value = eval_node(right_value, vars)
        apply = OPERATIONS[type(op)] results.append(apply(left_value, right_value))
    if len(results) > 1:
        raise ValueError("Cannot use chained comparison operations")
    return results[0]

def eval_node(node: ast.AST, vars: Dict[str, Any]) -> float:
    EVALUATORS = {
        ast.Expression: eval_expression,
        ast.Constant: eval_constant,
        ast.Name: eval_name,
        ast.BinOp: eval_binop,
        ast.UnaryOp: eval_unaryop,
        ast.Compare: eval_compare,
    }

    for ast_type, evaluator in EVALUATORS.items():
        if isinstance(node, ast_type):
            return evaluator(node, vars)
    print(type(node))
    raise KeyError(node)


with open('.budget.txt') as f:
    budget_id = f.readline().strip()

# Configure API key authorization: bearer
configuration = ynab.Configuration()
ynab_token = os.environ.get('YNAB_TOKEN')
configuration.api_key['Authorization'] = ynab_token
# Uncomment below to setup prefix (e.g. Bearer) for API key, if needed
configuration.api_key_prefix['Authorization'] = 'Bearer'
# create an instance of the API class
api_instance = ynab.AccountsApi()

print(budget_id)



