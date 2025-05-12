import tempfile
from pathlib import Path

from kit import ContextExtractor


def test_chunk_file_by_lines():
    with tempfile.TemporaryDirectory() as tmpdir:
        fpath = f"{tmpdir}/test.py"
        with open(fpath, "w") as f:
            f.write(("def foo():\n    pass\ndef bar():\n    pass\n") * 10)
        extractor = ContextExtractor(tmpdir)
        chunks = extractor.chunk_file_by_lines("test.py", max_lines=3)
        assert len(chunks) > 0
        assert all(isinstance(chunk, str) for chunk in chunks)


def test_chunk_file_by_symbols():
    with tempfile.TemporaryDirectory() as tmpdir:
        fpath = f"{tmpdir}/test.py"
        with open(fpath, "w") as f:
            f.write("""class Foo:\n    def bar(self): pass\ndef baz(): pass\n""")
        extractor = ContextExtractor(tmpdir)
        chunks = extractor.chunk_file_by_symbols("test.py")
        names = {c["name"] for c in chunks}
        assert "Foo" in names
        assert "baz" in names
        types = {c["type"] for c in chunks}
        assert "class" in types
        assert "function" in types


def test_extract_context_around_line():
    with tempfile.TemporaryDirectory() as tmpdir_str:
        tmpdir = Path(tmpdir_str)
        extractor = ContextExtractor(tmpdir_str)

        # --- Test 1: Python file, line within a function (existing test, adapted) ---
        py_file_func = tmpdir / "py_func.py"
        py_file_func_content = """def foo():
    x = 1 # Target line for foo
    y = 2
    return x + y
"""
        with open(py_file_func, "w") as f:
            f.write(py_file_func_content)
        ctx_func = extractor.extract_context_around_line("py_func.py", 2)
        assert ctx_func is not None
        assert ctx_func["type"] == "function"
        assert ctx_func["name"] == "foo"
        assert ctx_func["code"] == py_file_func_content

        # --- Test 2: Python file, line within a class definition ---
        py_file_class = tmpdir / "py_class.py"
        py_file_class_content = """class MyClass:
    class_var = 10 # Target line for MyClass

    def __init__(self):
        self.instance_var = 20

def another_func():
    pass
"""
        with open(py_file_class, "w") as f:
            f.write(py_file_class_content)
        ctx_class = extractor.extract_context_around_line("py_class.py", 2)
        assert ctx_class is not None
        assert ctx_class["type"] == "class"
        assert ctx_class["name"] == "MyClass"
        assert "class_var = 10" in ctx_class["code"]
        assert "def __init__" in ctx_class["code"]
        assert "another_func" not in ctx_class["code"]  # Ensure it doesn't grab unrelated parts

        # --- Test 3: Python file, line is top-level (should use fallback) ---
        py_file_toplevel = tmpdir / "py_toplevel.py"
        py_file_toplevel_content = """import os
MY_GLOBAL = 100 # Target line for top-level
print(MY_GLOBAL)
def helper():
    pass
"""
        with open(py_file_toplevel, "w") as f:
            f.write(py_file_toplevel_content)
        ctx_toplevel = extractor.extract_context_around_line("py_toplevel.py", 2)
        assert ctx_toplevel is not None
        assert ctx_toplevel["type"] == "code_chunk"
        assert ctx_toplevel["name"] == "py_toplevel.py:2"
        assert "MY_GLOBAL = 100" in ctx_toplevel["code"]
        # Check if it captured the surrounding lines (default 10 up/down)
        # Since this file is short, it should capture most/all of it.
        assert "import os" in ctx_toplevel["code"]
        assert "print(MY_GLOBAL)" in ctx_toplevel["code"]

        # --- Test 4: Python file with syntax error (should use fallback) ---
        py_file_syntax_error = tmpdir / "py_syntax_error.py"
        py_file_syntax_error_content = """def valid_func():
    print("ok")
this_is_a_syntax_error x = # Target line for syntax error
def another_valid_func():
    print("still ok")
"""
        with open(py_file_syntax_error, "w") as f:
            f.write(py_file_syntax_error_content)
        ctx_syntax_error = extractor.extract_context_around_line("py_syntax_error.py", 3)
        assert ctx_syntax_error is not None
        assert ctx_syntax_error["type"] == "code_chunk"
        assert ctx_syntax_error["name"] == "py_syntax_error.py:3"
        assert "this_is_a_syntax_error x =" in ctx_syntax_error["code"]
        assert "def valid_func()" in ctx_syntax_error["code"]  # Part of the chunk
        assert "def another_valid_func()" in ctx_syntax_error["code"]  # Part of the chunk

        # --- Test 5: Non-Python file (e.g., .txt) ---
        txt_file = tmpdir / "test.txt"
        txt_file_lines = [f"Line {i + 1}\n" for i in range(30)]
        txt_file_content = "".join(txt_file_lines)
        with open(txt_file, "w") as f:
            f.write(txt_file_content)

        # Target line 15 (0-indexed 14)
        # Expect lines 5 to 25 (0-indexed 4 to 24)
        ctx_txt = extractor.extract_context_around_line("test.txt", 15)
        assert ctx_txt is not None
        assert ctx_txt["type"] == "code_chunk"
        assert ctx_txt["name"] == "test.txt:15"
        expected_txt_chunk_lines = txt_file_lines[15 - 1 - 10 : 15 - 1 + 10 + 1]
        assert ctx_txt["code"] == "".join(expected_txt_chunk_lines)
        assert "Line 5" in ctx_txt["code"]
        assert "Line 25" in ctx_txt["code"]
        assert "Line 4" not in ctx_txt["code"]
        assert "Line 26" not in ctx_txt["code"]

        # --- Test 6: Line-chunking, near start of file ---
        ctx_txt_start = extractor.extract_context_around_line("test.txt", 2)  # Target line 2
        assert ctx_txt_start is not None
        assert ctx_txt_start["type"] == "code_chunk"
        assert ctx_txt_start["name"] == "test.txt:2"
        # Expect lines 1 to 12 (0-indexed 0 to 11)
        expected_txt_start_chunk_lines = txt_file_lines[0 : 2 - 1 + 10 + 1]
        assert ctx_txt_start["code"] == "".join(expected_txt_start_chunk_lines)
        assert "Line 1" in ctx_txt_start["code"]
        assert "Line 12" in ctx_txt_start["code"]
        assert "Line 13" not in ctx_txt_start["code"]

        # --- Test 7: Line-chunking, near end of file ---
        ctx_txt_end = extractor.extract_context_around_line("test.txt", 29)  # Target line 29 in 30 line file
        assert ctx_txt_end is not None
        assert ctx_txt_end["type"] == "code_chunk"
        assert ctx_txt_end["name"] == "test.txt:29"
        # Expect lines 19 to 30 (0-indexed 18 to 29)
        expected_txt_end_chunk_lines = txt_file_lines[29 - 1 - 10 : 30]
        assert ctx_txt_end["code"] == "".join(expected_txt_end_chunk_lines)
        assert "Line 19" in ctx_txt_end["code"]
        assert "Line 30" in ctx_txt_end["code"]
        assert "Line 18" not in ctx_txt_end["code"]

        # --- Test 8: Line-chunking, target line out of bounds ---
        ctx_out_of_bounds_high = extractor.extract_context_around_line("test.txt", 50)
        assert ctx_out_of_bounds_high is None
        ctx_out_of_bounds_low = extractor.extract_context_around_line("test.txt", 0)
        assert ctx_out_of_bounds_low is None
        ctx_out_of_bounds_negative = extractor.extract_context_around_line("test.txt", -5)
        assert ctx_out_of_bounds_negative is None

        # --- Test 9: Line-chunking, file with fewer than context_delta * 2 + 1 lines ---
        short_txt_file = tmpdir / "short_test.txt"
        short_txt_content = "Line 1\nLine 2\nLine 3\n"
        with open(short_txt_file, "w") as f:
            f.write(short_txt_content)
        ctx_short_txt = extractor.extract_context_around_line("short_test.txt", 2)
        assert ctx_short_txt is not None
        assert ctx_short_txt["type"] == "code_chunk"
        assert ctx_short_txt["name"] == "short_test.txt:2"
        assert ctx_short_txt["code"] == short_txt_content  # Should be the whole file

        # --- Test 10: Python file, line in class method ---
        py_file_method = tmpdir / "py_method.py"
        py_method_content = """class AnotherClass:
    def a_method(self):
        print("inside method") # Target line
        return True
"""
        with open(py_file_method, "w") as f:
            f.write(py_method_content)
        ctx_method = extractor.extract_context_around_line("py_method.py", 3)
        assert ctx_method is not None
        assert ctx_method["type"] == "function"  # AST considers methods as FunctionDef
        assert ctx_method["name"] == "a_method"
        assert 'print("inside method")' in ctx_method["code"]
        assert "class AnotherClass:" not in ctx_method["code"]  # Should be just the method
