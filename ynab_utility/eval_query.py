import ast
from typing import Dict, Any
import operator


def eval_expression(node: ast.Expression, vars: Dict[str, Any]) -> float:
    return eval_node(node.body, vars)

def eval_constant(node: ast.Constant, vars: Dict[str, Any]) -> float:
    try:
        return node.value.replace('||','\\b')
    except AttributeError:
        return node.value

def eval_name(node: ast.Name, vars: Dict[str, Any]) -> float:
    try:
        return vars[node.id].fillna('')
    except AttributeError:
        return node.value

def eval_binop(node: ast.BinOp, vars: Dict[str, Any]) -> float:
    OPERATIONS = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.BitOr: operator.or_,
        ast.BitAnd: operator.and_,
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
        ast.In: lambda a,b: b.str.contains(a, regex=True, case=False)
    }

    results = []
    for op, right_value in zip(node.ops, node.comparators):
        left_value = eval_node(node.left, vars)
        right_value = eval_node(right_value, vars)
        apply = OPERATIONS[type(op)]
        results.append(apply(left_value, right_value))
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

def eval_query(query, vars: Dict[str, Any]):
    eval_node(ast.parse(query, "<string>", mode="eval"), vars)

    
#matches = eval_node(ast.parse('(import_payee_name=="pcc") | (import_payee_name=="safeway")', '<string>', mode='eval'), df_filtered)
#display(df_filtered[matches])


