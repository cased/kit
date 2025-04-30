# /Users/tnm/kit/tests/golden_python.py

import asyncio # Need this for the async function example

def top_level_function(arg1, arg2):
    """A regular function."""
    pass

class MyClass:
    """A sample class."""
    def __init__(self, value):
        self.value = value

    def method_one(self, param):
        """A method within the class."""
        return self.value + param

async def async_function():
    """An asynchronous function."""
    await asyncio.sleep(1)

# A top-level variable (currently not expected to be captured by basic query)
CONSTANT_VALUE = 100
