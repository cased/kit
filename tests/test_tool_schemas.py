import kit


def test_get_tool_schemas_basic():
    """Ensure get_tool_schemas returns a non-empty list of JSON-serialisable dicts."""
    schemas = kit.get_tool_schemas()

    # Basic shape checks
    assert isinstance(schemas, list) and schemas, "Expected non-empty list"
    assert all(isinstance(s, dict) for s in schemas), "Every schema should be a dict"

    # Required top-level keys from MCP Tool (name + inputSchema at minimum)
    sample = schemas[0]
    assert "name" in sample and "inputSchema" in sample, "Schema missing expected keys"

    # Spot-check a few known tool names
    tool_names = {s["name"] for s in schemas}
    for expected in {"open_repository", "search_code", "get_file_tree", "get_file_content"}:
        assert expected in tool_names, f"{expected} should be part of tool schema list"
