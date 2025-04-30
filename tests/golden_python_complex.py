# More complex Python examples for symbol extraction

import os

GLOBAL_VAR = 100

def decorator(func):
    def wrapper(*args, **kwargs):
        print("Before call")
        result = func(*args, **kwargs)
        print("After call")
        return result
    return wrapper

@decorator
def decorated_function(x: int) -> int:
    """A decorated function."""
    return x * 2

class OuterClass:
    OUTER_CONST = "outer"

    def outer_method(self):
        print("Outer method")

    class InnerClass:
        INNER_CONST = "inner"

        def __init__(self, name: str):
            self.name = name

        def inner_method(self):
            print(f"Inner method called by {self.name}")

        @staticmethod
        def static_inner():
            print("Static inner method")
            
        def nested_function_in_method(self):
            
            def deeply_nested():
                print("Deeply nested function")
            
            deeply_nested()
            return "nested_func_ran"

def generator_function(n):
    """A generator function."""
    i = 0
    while i < n:
        yield i
        i += 1

async def async_generator(n):
    i = 0
    while i < n:
        yield i
        i += 1

lambda_func = lambda x, y: x + y

# Top-level simple function again for baseline
def another_top_level():
    pass
