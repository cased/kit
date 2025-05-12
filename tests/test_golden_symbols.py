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


# --- Basic Tests ---
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
