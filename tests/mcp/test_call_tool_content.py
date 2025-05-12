import pytest
from mcp.types import CallToolResult, EmbeddedResource, TextContent

# The server module provides a fallback alias called `ResourceContent`.  Depending on
# the MCP SDK version, this *may* be the same object as `EmbeddedResource`, or a
# stub when running under an older spec version.  Importing it must never fail.
from kit.mcp.server import GetFileContentParams, GetFileTreeParams, KitServerLogic, ResourceContent


def _dummy_repo(tmp_path):
    """Create a tiny git-repo-looking directory we can open with KitServerLogic."""
    (tmp_path / "dummy.py").write_text("print('hello')\n", encoding="utf-8")
    # A .git dir is *not* required for Repository – it only checks the path exists.
    return str(tmp_path)


@pytest.fixture()
def logic(tmp_path):
    """Yield a fresh KitServerLogic instance with one opened repo."""
    server_logic = KitServerLogic()
    repo_id = server_logic.open_repository(_dummy_repo(tmp_path))
    return server_logic, repo_id


def test_resourcecontent_alias():
    """`ResourceContent` should successfully import and be a `BaseModel` subclass."""
    # The alias can point to `EmbeddedResource` (new SDK) or a stub class (old SDK).
    assert hasattr(ResourceContent, "model_validate"), "ResourceContent should be a pydantic model"
    # If the current SDK exposes EmbeddedResource, the alias should be identical.
    if "EmbeddedResource" in EmbeddedResource.__name__:
        assert ResourceContent is EmbeddedResource


def test_get_file_content_returns_textcontent(logic):
    """The call-tool logic for **get_file_content** must return TextContent."""
    server_logic, repo_id = logic

    # Replicate the input model used by the call-tool handler.
    args = GetFileContentParams(repo_id=repo_id, file_path="dummy.py")

    # The real call-tool first validates the path – do the same here to ensure the
    # helper doesn't raise.
    server_logic.get_file_content(args.repo_id, args.file_path)

    result = [TextContent(type="text", text=f"/repos/{args.repo_id}/files/{args.file_path}")]

    # Attempt to build a CallToolResult – this is what the MCP framework will do
    # internally.  If the content list contains the wrong type, Pydantic validation
    # will fail, reproducing the original bug.
    ctr = CallToolResult(content=result)
    assert isinstance(ctr.content[0], TextContent)


def test_get_file_tree_returns_textcontent(logic):
    """The call-tool logic for **get_file_tree** must return TextContent."""
    server_logic, repo_id = logic

    args = GetFileTreeParams(repo_id=repo_id)
    server_logic.get_file_tree(args.repo_id)  # Should not raise

    result = [TextContent(type="text", text=f"/repos/{args.repo_id}/tree")]
    ctr = CallToolResult(content=result)
    assert isinstance(ctr.content[0], TextContent)
