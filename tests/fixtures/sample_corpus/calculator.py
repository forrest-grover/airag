"""A simple calculator module for arithmetic operations."""


class Calculator:
    """Performs basic arithmetic: add, subtract, multiply, divide."""

    def __init__(self, precision: int = 2):
        self.precision = precision
        self.history: list[tuple[str, float]] = []

    def add(self, a: float, b: float) -> float:
        result = round(a + b, self.precision)
        self.history.append(("add", result))
        return result

    def subtract(self, a: float, b: float) -> float:
        result = round(a - b, self.precision)
        self.history.append(("subtract", result))
        return result

    def multiply(self, a: float, b: float) -> float:
        result = round(a * b, self.precision)
        self.history.append(("multiply", result))
        return result

    def divide(self, a: float, b: float) -> float:
        if b == 0:
            raise ZeroDivisionError("Cannot divide by zero")
        result = round(a / b, self.precision)
        self.history.append(("divide", result))
        return result

    def clear_history(self) -> None:
        self.history.clear()


def fibonacci(n: int) -> list[int]:
    """Generate the first n Fibonacci numbers."""
    if n <= 0:
        return []
    if n == 1:
        return [0]
    sequence = [0, 1]
    for _ in range(2, n):
        sequence.append(sequence[-1] + sequence[-2])
    return sequence
