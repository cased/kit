import os
import tempfile

from kit import Repository


# Helper to run extraction
def run_extraction(tmpdir, filename, content):
    path = os.path.join(tmpdir, filename)
    with open(path, "w") as f:
        f.write(content)
    repository = Repository(tmpdir)
    return repository.extract_symbols(filename)


def test_python_imports_extraction():
    """Test extraction of various Python import patterns."""
    with tempfile.TemporaryDirectory() as tmpdir:
        content = '''
import os
import sys, json
import numpy as np
from collections import defaultdict
from typing import List as ListType, Dict
from . import local_module
from ..parent import parent_module
from math import *

# Some code to ensure imports are at the top
def some_function():
    pass
'''
        symbols = run_extraction(tmpdir, "test_imports.py", content)
        names_types = {(s["name"], s["type"]) for s in symbols}

        # Check for import statements
        assert ("os", "import") in names_types
        assert ("sys", "import") in names_types
        assert ("json", "import") in names_types
        assert ("numpy", "import") in names_types
        assert ("np", "import_alias") in names_types
        assert ("collections", "import") in names_types
        assert ("typing", "import") in names_types
        assert ("ListType", "import_alias") in names_types
        assert (".", "import") in names_types
        assert ("..parent", "import") in names_types
        assert ("math", "import") in names_types

        # Also check that function is still captured
        assert ("some_function", "function") in names_types


def test_python_function_calls_extraction():
    """Test extraction of various Python function call patterns with full expressions."""
    with tempfile.TemporaryDirectory() as tmpdir:
        content = '''
import os
import math

# Simple function calls with arguments
print("Hello, world!")
len([1, 2, 3, 4, 5])
max(10, 20, 30)

class MyClass:
    def __init__(self, value):
        self.value = value

    def add(self, x, y):
        return x + y

    def process(self, data, reverse=False):
        return data

# Method calls with arguments
obj = MyClass(42)
result = obj.add(10, 20)
processed = obj.process("data", reverse=True)

# Module function calls
file_path = os.path.join("dir", "file.txt")
sqrt_val = math.sqrt(16)

# Chained method calls
text = "hello world"
result = text.upper().strip().replace(" ", "_")

# Constructor calls
new_obj = MyClass(100)
my_dict = dict(a=1, b=2)

# Complex arguments
def handler(func, items):
    return func(items)

result = handler(lambda x: x * 2, [1, 2, 3])

# Multi-line call
long_result = handler(
    lambda x: x.upper(),
    ["hello", "world"]
)
'''
        symbols = run_extraction(tmpdir, "test_calls.py", content)
        call_symbols = [s for s in symbols if s["type"] == "call"]
        calls_by_name = {s["name"]: s for s in call_symbols}

        # Verify function calls are captured with full expressions
        assert "print" in calls_by_name
        assert 'print("Hello, world!")' == calls_by_name["print"]["code"]

        assert "len" in calls_by_name
        assert "len([1, 2, 3, 4, 5])" == calls_by_name["len"]["code"]

        assert "max" in calls_by_name
        assert "max(10, 20, 30)" == calls_by_name["max"]["code"]

        # Method calls
        assert "add" in calls_by_name
        assert "obj.add(10, 20)" == calls_by_name["add"]["code"]

        assert "process" in calls_by_name
        assert 'obj.process("data", reverse=True)' == calls_by_name["process"]["code"]

        # Module function calls
        assert "join" in calls_by_name
        assert 'os.path.join("dir", "file.txt")' == calls_by_name["join"]["code"]

        assert "sqrt" in calls_by_name
        assert "math.sqrt(16)" == calls_by_name["sqrt"]["code"]

        # Chained method calls - should capture each method in the chain
        call_names = [s["name"] for s in call_symbols]
        assert "upper" in call_names
        assert "strip" in call_names
        assert "replace" in call_names

        # Constructor calls
        assert "MyClass" in calls_by_name
        assert "dict" in calls_by_name
        assert "dict(a=1, b=2)" == calls_by_name["dict"]["code"]

        # Verify line numbers are captured
        assert all("start_line" in s and "end_line" in s for s in call_symbols)

        # Multi-line call should span multiple lines
        handler_calls = [s for s in call_symbols if s["name"] == "handler"]
        if handler_calls:
            multiline_call = [s for s in handler_calls if s["start_line"] != s["end_line"]]
            assert len(multiline_call) > 0, "Should capture multi-line calls"

        # Verify we still capture functions and classes
        all_symbols = {(s["name"], s["type"]) for s in symbols}
        assert ("MyClass", "class") in all_symbols
        assert ("add", "method") in all_symbols
        assert ("handler", "function") in all_symbols


def test_typescript_symbol_extraction():
    with tempfile.TemporaryDirectory() as tmpdir:
        os.path.join(tmpdir, "golden_typescript.ts")
        # Read content from the actual golden file
        golden_content = open(os.path.join(os.path.dirname(__file__), "golden_typescript.ts")).read()
        symbols = run_extraction(tmpdir, "golden_typescript.ts", golden_content)
        names_types = {(s["name"], s["type"]) for s in symbols}

        assert ("MyClass", "class") in names_types
        assert ("MyInterface", "interface") in names_types
        assert ("MyEnum", "enum") in names_types
        assert ("helper", "function") in names_types


def test_python_symbol_extraction():
    with tempfile.TemporaryDirectory() as tmpdir:
        os.path.join(tmpdir, "golden_python.py")
        # Read content from the actual golden file
        golden_content = open(os.path.join(os.path.dirname(__file__), "golden_python.py")).read()
        symbols = run_extraction(tmpdir, "golden_python.py", golden_content)
        # Convert to set of tuples for easier assertion.
        # Note: The current basic query likely won't capture methods or async correctly.
        names_types = {(s["name"], s["type"]) for s in symbols}

        # Expected symbols based on the *improved* query
        expected = {
            ("top_level_function", "function"),
            ("MyClass", "class"),
            ("__init__", "method"),
            ("method_one", "method"),
            ("async_function", "function"),
            ("asyncio", "import"),  # Import statement
            ("sleep", "call"),  # asyncio.sleep(1) call
        }

        # We'll refine the assertions as we improve the query
        assert ("top_level_function", "function") in names_types
        assert ("MyClass", "class") in names_types
        assert ("method_one", "method") in names_types
        assert ("async_function", "function") in names_types

        # Example of more precise assertion (use once query is improved)
        assert names_types == expected


# --- Complex Tests ---
def test_python_complex_symbol_extraction():
    with tempfile.TemporaryDirectory() as tmpdir:
        golden_content = open(os.path.join(os.path.dirname(__file__), "golden_python_complex.py")).read()
        symbols = run_extraction(tmpdir, "golden_python_complex.py", golden_content)
        names_types = {(s["name"], s["type"]) for s in symbols}

        # Expected symbols based on current Python query
        # NOTE: Current query doesn't capture decorators well, nested functions, lambdas, or generators explicitly
        expected = {
            ("decorator", "function"),  # Decorator function itself
            ("decorated_function", "function"),  # The decorated function
            ("OuterClass", "class"),
            ("outer_method", "method"),
            ("InnerClass", "class"),  # Nested class
            ("__init__", "method"),  # Inner class method
            ("inner_method", "method"),  # Inner class method
            ("static_inner", "method"),  # Inner class static method
            ("nested_function_in_method", "method"),  # Method containing nested func
            # ("deeply_nested", "function"),   # NOT CAPTURED - function defined inside method
            ("generator_function", "function"),  # Generator (captured as function)
            ("async_generator", "function"),  # Async Generator (captured as function)
            ("lambda_func", "function"),  # Now captured by the improved extraction
            ("another_top_level", "function"),
            # Function calls now captured
            ("print", "call"),  # print() calls
            ("func", "call"),  # func(*args, **kwargs) in decorator
            ("deeply_nested", "call"),  # deeply_nested() call
        }

        # Assert individual expected symbols exist
        for item in expected:
            assert item in names_types, f"Expected symbol {item} not found in {names_types}"

        # Assert the exact set matches (allows for debugging extra captures)
        assert names_types == expected, f"Mismatch: Got {names_types}, Expected {expected}"


def test_typescript_complex_symbol_extraction():
    with tempfile.TemporaryDirectory() as tmpdir:
        golden_content = open(os.path.join(os.path.dirname(__file__), "golden_typescript_complex.ts")).read()
        symbols = run_extraction(tmpdir, "golden_typescript_complex.ts", golden_content)
        names_types = {(s["name"], s["type"]) for s in symbols}

        # Expected symbols based on current TypeScript query
        # NOTE: Current query might not capture all nuances (e.g. arrow funcs, namespaces well)
        expected = {
            ("UserProfile", "interface"),
            ("Status", "enum"),
            ("Utilities", "namespace"),  # Namespace itself
            ("log", "function"),  # Function inside namespace
            ("StringHelper", "class"),  # Class inside namespace
            ("capitalize", "method"),  # Static method inside namespace class
            ("identity", "function"),  # Generic function
            ("GenericRepo", "class"),  # Generic class
            ("add", "method"),  # Method in generic class
            ("getAll", "method"),  # Method in generic class
            ("constructor", "method"),  # Constructor is captured by method query
            # ("addNumbers", "function"),    # NOT CAPTURED - Arrow function assigned to const
            ("DecoratedClass", "class"),
            ("greet", "method"),
            ("calculateArea", "function"),  # Exported function
            ("fetchData", "function"),  # Async function
            ("SimpleLogger", "class"),
            ("log", "method"),  # Method in SimpleLogger (duplicate name, diff class)
        }

        # Assert individual expected symbols exist
        for item in expected:
            assert item in names_types, f"Expected symbol {item} not found in {names_types}"

        # Assert the exact set matches (allows for debugging extra captures)
        assert names_types == expected, f"Mismatch: Got {names_types}, Expected {expected}"


# --- HCL Test ---
def test_hcl_symbol_extraction():
    with tempfile.TemporaryDirectory() as tmpdir:
        golden_content = open(os.path.join(os.path.dirname(__file__), "golden_hcl.tf")).read()
        symbols = run_extraction(tmpdir, "golden_hcl.tf", golden_content)
        names_types = {(s["name"], s["type"]) for s in symbols}

        # Expected symbols based on HCL query and updated extractor logic
        expected = {
            ("aws", "provider"),  # provider "aws"
            ("aws_instance.web_server", "resource"),  # resource "aws_instance" "web_server"
            ("aws_s3_bucket.data_bucket", "resource"),  # resource "aws_s3_bucket" "data_bucket"
            ("aws_ami.ubuntu", "data"),  # data "aws_ami" "ubuntu"
            ("server_port", "variable"),  # variable "server_port"
            ("instance_ip_addr", "output"),  # output "instance_ip_addr"
            ("vpc", "module"),  # module "vpc"
            ("locals", "locals"),  # locals block
            ("terraform", "terraform"),  # terraform block
        }

        # Assert individual expected symbols exist
        for item in expected:
            assert item in names_types, f"Expected symbol {item} not found in {names_types}"

        # Assert the exact set matches
        assert names_types == expected, f"Mismatch: Got {names_types}, Expected {expected}"


# --- Go Test ---
def test_go_symbol_extraction():
    with tempfile.TemporaryDirectory() as tmpdir:
        golden_content = open(os.path.join(os.path.dirname(__file__), "golden_go.go")).read()
        symbols = run_extraction(tmpdir, "golden_go.go", golden_content)
        names_types = {(s["name"], s["type"]) for s in symbols}

        # Expected symbols based on Go query
        expected = {
            ("User", "struct"),  # type User struct {...}
            ("Greeter", "interface"),  # type Greeter interface {...}
            ("Greet", "method"),  # func (u User) Greet() string {...}
            ("Add", "function"),  # func Add(a, b int) int {...}
            ("HelperFunction", "function"),  # func HelperFunction() {...}
            ("main", "function"),  # func main() {...}
        }

        # Assert individual expected symbols exist
        for item in expected:
            assert item in names_types, f"Expected symbol {item} not found in {names_types}"

        # Assert the exact set matches
        assert names_types == expected, f"Mismatch: Got {names_types}, Expected {expected}"
