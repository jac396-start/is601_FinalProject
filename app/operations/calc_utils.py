# app/operations/calc_utils.py
from typing import List

def compute_result(calc_type: str, inputs: List[float]) -> float:
    if not isinstance(inputs, list) or len(inputs) < 2:
        raise ValueError("Inputs must be a list with at least two numbers.")
    t = calc_type.lower()
    if t == 'addition':
        return sum(inputs)
    if t == 'subtraction':
        result = inputs[0]
        for v in inputs[1:]:
            result -= v
        return result
    if t == 'multiplication':
        result = 1
        for v in inputs:
            result *= v
        return result
    if t == 'division':
        result = inputs[0]
        for v in inputs[1:]:
            if v == 0:
                raise ValueError("Cannot divide by zero.")
            result /= v
        return result
    raise ValueError(f"Unsupported calculation type: {calc_type}")

