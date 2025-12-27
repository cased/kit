# Tests for C# symbol extraction
import os

from kit import Repository


def _extract(tmpdir: str, filename: str, content: str):
    path = os.path.join(tmpdir, filename)
    with open(path, "w") as f:
        f.write(content)
    return Repository(tmpdir).extract_symbols(filename)


def test_csharp_class_and_methods(tmp_path):
    """Test basic class, constructor, and method extraction."""
    code = """
namespace MyApp
{
    public class Foo
    {
        public int X { get; set; }

        public Foo() {}

        public void Bar() {}

        private static void Helper() {}
    }
}
"""
    symbols = _extract(str(tmp_path), "Foo.cs", code)
    names = {s["name"] for s in symbols}
    assert {"MyApp", "Foo", "Bar", "Helper", "X"}.issubset(names)


def test_csharp_interface(tmp_path):
    """Test interface extraction."""
    code = """
public interface IService
{
    void Execute();
    string GetName();
}
"""
    symbols = _extract(str(tmp_path), "IService.cs", code)
    names = {s["name"] for s in symbols}
    types = {s["type"] for s in symbols}
    assert "IService" in names
    assert "interface" in types


def test_csharp_struct(tmp_path):
    """Test struct extraction."""
    code = """
public struct Point
{
    public int X;
    public int Y;

    public Point(int x, int y)
    {
        X = x;
        Y = y;
    }
}
"""
    symbols = _extract(str(tmp_path), "Point.cs", code)
    names = {s["name"] for s in symbols}
    types = {s["type"] for s in symbols}
    assert "Point" in names
    assert "struct" in types


def test_csharp_enum(tmp_path):
    """Test enum extraction."""
    code = """
public enum Color
{
    Red,
    Green,
    Blue
}
"""
    symbols = _extract(str(tmp_path), "Color.cs", code)
    names = {s["name"] for s in symbols}
    types = {s["type"] for s in symbols}
    assert "Color" in names
    assert "enum" in types


def test_csharp_record(tmp_path):
    """Test C# 9+ record extraction."""
    code = """
public record Person(string FirstName, string LastName);

public record Employee(string FirstName, string LastName, string Department) : Person(FirstName, LastName);
"""
    symbols = _extract(str(tmp_path), "Records.cs", code)
    names = {s["name"] for s in symbols}
    types = {s["type"] for s in symbols}
    assert "Person" in names
    assert "Employee" in names
    assert "record" in types


def test_csharp_delegate(tmp_path):
    """Test delegate extraction."""
    code = """
public delegate void EventHandler(object sender, EventArgs e);
public delegate int Calculator(int a, int b);
"""
    symbols = _extract(str(tmp_path), "Delegates.cs", code)
    names = {s["name"] for s in symbols}
    types = {s["type"] for s in symbols}
    assert "EventHandler" in names
    assert "Calculator" in names
    assert "delegate" in types


def test_csharp_properties(tmp_path):
    """Test property extraction."""
    code = """
public class Config
{
    public string Name { get; set; }
    public int Count { get; private set; }
    public bool IsEnabled => true;
}
"""
    symbols = _extract(str(tmp_path), "Config.cs", code)
    names = {s["name"] for s in symbols}
    types = {s["type"] for s in symbols}
    assert {"Config", "Name", "Count", "IsEnabled"}.issubset(names)
    assert "property" in types


def test_csharp_namespace_qualified(tmp_path):
    """Test qualified namespace extraction (e.g., Foo.Bar.Baz)."""
    code = """
namespace Foo.Bar.Baz
{
    public class Widget {}
}
"""
    symbols = _extract(str(tmp_path), "Widget.cs", code)
    names = {s["name"] for s in symbols}
    # Qualified name should be captured
    assert "Widget" in names
    # Check for namespace - could be "Foo.Bar.Baz" as text
    namespace_symbols = [s for s in symbols if s["type"] == "namespace"]
    assert len(namespace_symbols) >= 1


def test_csharp_complex_file(tmp_path):
    """Test a more complex C# file with multiple constructs."""
    code = """
using System;
using System.Collections.Generic;

namespace MyCompany.MyProduct.Core
{
    public interface IRepository<T>
    {
        T GetById(int id);
        void Save(T entity);
    }

    public class UserRepository : IRepository<User>
    {
        private readonly List<User> _users;

        public UserRepository()
        {
            _users = new List<User>();
        }

        public User GetById(int id)
        {
            return _users.Find(u => u.Id == id);
        }

        public void Save(User entity)
        {
            _users.Add(entity);
        }

        public IEnumerable<User> GetAll() => _users;
    }

    public record User(int Id, string Name, string Email);

    public struct UserId
    {
        public int Value { get; }
        public UserId(int value) => Value = value;
    }

    public enum UserStatus
    {
        Active,
        Inactive,
        Pending
    }

    public delegate void UserChangedHandler(User user);
}
"""
    symbols = _extract(str(tmp_path), "Repository.cs", code)
    names = {s["name"] for s in symbols}
    types = {s["type"] for s in symbols}

    # Check classes
    assert "UserRepository" in names

    # Check interfaces
    assert "IRepository" in names
    assert "interface" in types

    # Check records
    assert "User" in names
    assert "record" in types

    # Check structs
    assert "UserId" in names
    assert "struct" in types

    # Check enums
    assert "UserStatus" in names
    assert "enum" in types

    # Check delegates
    assert "UserChangedHandler" in names
    assert "delegate" in types

    # Check methods
    assert {"GetById", "Save", "GetAll"}.issubset(names)
    assert "method" in types

    # Check properties
    assert "Value" in names
    assert "property" in types

    # Check constructors
    assert "constructor" in types
