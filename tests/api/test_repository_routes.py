import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock

# Import the main FastAPI app instance that 'kit serve' would run.
# This assumes your main app is accessible. 
# If cli.py initializes it directly, we might need to import that app or replicate its setup.
# For now, let's assume `kit.api.app` is where the main app is defined and routers are mounted.
from kit.api import app as main_fastapi_app # This is imported by cli.py
from kit.repository import Repository
from kit.api.repository_routes import router as repository_api_router

# Fixture to provide a TestClient with a mocked Repository
@pytest.fixture
def client_with_mock_repo():
    mock_repo = MagicMock(spec=Repository)
    
    # Configure the app state with the mock repository for this test client
    main_fastapi_app.state.repository = mock_repo
    
    # Ensure the repository router is included if it's not already part of the main_fastapi_app definition globally
    # (cli.py adds it conditionally, so for testing we might need to ensure it's there)
    # However, if main_fastapi_app is the actual app instance from kit.api.app, 
    # and cli.py modifies *that instance*, then the router might already be included 
    # if a previous test run (or the app structure) caused it to be.
    # For robustness in tests, explicitly include it if it might not be there.
    # A better way would be to have a factory function for the app in tests.
    # For now, let's assume we test against the app as configured by cli.py (implicitly)
    # or we explicitly add it here if testing routes in isolation.

    # If repository_api_router is not always included by default in main_fastapi_app:
    if not any(route.path_format == "/repository/file_tree" for route in main_fastapi_app.routes):
         # This check is a bit naive, better to check if router is in app.routers
         # A cleaner test setup might involve creating a fresh app instance for tests
         # and adding routers to it, rather than using a potentially shared main_fastapi_app.
         try:
             main_fastapi_app.include_router(repository_api_router)
         except Exception as e:
             # It might already be included, which can cause issues if added again.
             # FastAPI routers don't have a simple "is_included" check.
             # print(f"Note: Router might already be included or error during inclusion: {e}")
             pass # Assuming it might be already included by another test or app setup

    with TestClient(main_fastapi_app) as client:
        yield client, mock_repo
    
    # Clean up app state after test if necessary
    if hasattr(main_fastapi_app.state, 'repository'):
        del main_fastapi_app.state.repository


def test_get_file_tree_success(client_with_mock_repo):
    client, mock_repo = client_with_mock_repo
    
    expected_file_tree = [
        {"path": "src", "is_dir": True, "size": 0},
        {"path": "src/main.py", "is_dir": False, "size": 1024}
    ]
    mock_repo.get_file_tree.return_value = expected_file_tree
    
    response = client.get("/repository/file_tree")
    
    assert response.status_code == 200
    assert response.json() == expected_file_tree
    mock_repo.get_file_tree.assert_called_once()

def test_get_file_tree_repo_not_configured(client_with_mock_repo):
    client, mock_repo = client_with_mock_repo
    
    # Simulate repository not being in app.state for this specific client call
    # This is a bit tricky because client_with_mock_repo fixture sets it up.
    # A more direct way would be to use a client where app.state.repository is explicitly None.
    # For now, let's test the HTTPException by temporarily removing it from the actual app used by the client.
    # This assumes client uses the same app instance.
    
    original_repo_state = None
    if hasattr(main_fastapi_app.state, 'repository'):
        original_repo_state = main_fastapi_app.state.repository
        del main_fastapi_app.state.repository

    response = client.get("/repository/file_tree")
    
    assert response.status_code == 503
    assert "Repository not configured or available" in response.json()["detail"]
    
    # Restore state for other tests
    if original_repo_state is not None:
        main_fastapi_app.state.repository = original_repo_state
    else: # If it wasn't there to begin with for some reason, ensure it's not there after
        if hasattr(main_fastapi_app.state, 'repository'):
            del main_fastapi_app.state.repository

def test_get_file_tree_repository_error(client_with_mock_repo):
    client, mock_repo = client_with_mock_repo
    
    mock_repo.get_file_tree.side_effect = Exception("Test repo internal error")
    
    response = client.get("/repository/file_tree")
    
    assert response.status_code == 500
    assert "Error fetching file tree: Test repo internal error" in response.json()["detail"]
    mock_repo.get_file_tree.assert_called_once()

# Basic placeholder tests for other endpoints (to be expanded)

def test_get_file_content_success(client_with_mock_repo):
    client, mock_repo = client_with_mock_repo
    mock_repo.get_file_content.return_value = "print('hello')"
    response = client.get("/repository/file_content?path=test.py")
    assert response.status_code == 200
    assert response.text == "print('hello')"
    mock_repo.get_file_content.assert_called_once_with("test.py")

def test_get_file_content_not_found(client_with_mock_repo):
    client, mock_repo = client_with_mock_repo
    mock_repo.get_file_content.side_effect = FileNotFoundError("File not here")
    response = client.get("/repository/file_content?path=nonexistent.py")
    assert response.status_code == 404
    assert "File not found: nonexistent.py" in response.json()["detail"]

def test_get_file_content_missing_param(client_with_mock_repo):
    client, _ = client_with_mock_repo
    response = client.get("/repository/file_content") # Missing 'path'
    # FastAPI typically returns 422 for validation errors with missing query params if not Optional
    # Our handler raises 400 if path is empty, but FastAPI handles missing required query params before that.
    assert response.status_code == 422 # FastAPI default for missing required query param


# --- Tests for /symbols --- 

def test_get_symbols_success(client_with_mock_repo):
    client, mock_repo = client_with_mock_repo
    expected_symbols = [
        {"name": "my_func", "type": "function", "file": "test.py", "start_line": 1, "end_line": 3},
        {"name": "MyClass", "type": "class", "file": "test.py", "start_line": 5, "end_line": 10}
    ]
    mock_repo.extract_symbols.return_value = expected_symbols
    
    response = client.get("/repository/symbols?file_path=test.py")
    
    assert response.status_code == 200
    assert response.json() == expected_symbols
    mock_repo.extract_symbols.assert_called_once_with("test.py")

def test_get_symbols_file_not_found(client_with_mock_repo):
    client, mock_repo = client_with_mock_repo
    mock_repo.extract_symbols.side_effect = FileNotFoundError("Symbols file not found")
    # Assuming extract_symbols raises FileNotFoundError, which our handler catches
    
    response = client.get("/repository/symbols?file_path=nonexistent.py")
    
    assert response.status_code == 404
    assert "File not found for symbol extraction: nonexistent.py" in response.json()["detail"]
    mock_repo.extract_symbols.assert_called_once_with("nonexistent.py")

def test_get_symbols_missing_param(client_with_mock_repo):
    client, _ = client_with_mock_repo
    response = client.get("/repository/symbols") # Missing 'file_path'
    assert response.status_code == 422 # FastAPI default for missing required query param

def test_get_symbols_repository_error(client_with_mock_repo):
    client, mock_repo = client_with_mock_repo
    mock_repo.extract_symbols.side_effect = Exception("Symbols internal error")
    
    response = client.get("/repository/symbols?file_path=error.py")
    
    assert response.status_code == 500
    assert "Error extracting symbols for error.py: Symbols internal error" in response.json()["detail"]
    mock_repo.extract_symbols.assert_called_once_with("error.py")


# --- Tests for /search_text --- 

def test_search_text_success_no_pattern(client_with_mock_repo):
    client, mock_repo = client_with_mock_repo
    expected_results = [
        {"file": "test.py", "line_number": 5, "line_content": "  # search_query found here"}
    ]
    mock_repo.search_text.return_value = expected_results
    
    response = client.get("/repository/search_text?query=search_query")
    
    assert response.status_code == 200
    assert response.json() == expected_results
    mock_repo.search_text.assert_called_once_with(query="search_query", file_pattern=None)

def test_search_text_success_with_pattern(client_with_mock_repo):
    client, mock_repo = client_with_mock_repo
    expected_results = [
        {"file": "src/main.py", "line_number": 10, "line_content": "relevant_text = True"}
    ]
    mock_repo.search_text.return_value = expected_results
    
    response = client.get("/repository/search_text?query=relevant_text&file_pattern=*.py")
    
    assert response.status_code == 200
    assert response.json() == expected_results
    mock_repo.search_text.assert_called_once_with(query="relevant_text", file_pattern="*.py")

def test_search_text_no_results(client_with_mock_repo):
    client, mock_repo = client_with_mock_repo
    mock_repo.search_text.return_value = [] # Empty list for no results
    
    response = client.get("/repository/search_text?query=non_existent_term")
    
    assert response.status_code == 200
    assert response.json() == []
    mock_repo.search_text.assert_called_once_with(query="non_existent_term", file_pattern=None)

def test_search_text_missing_query_param(client_with_mock_repo):
    client, _ = client_with_mock_repo
    response = client.get("/repository/search_text") # Missing 'query'
    assert response.status_code == 422 # FastAPI default for missing required query param

def test_search_text_repository_error(client_with_mock_repo):
    client, mock_repo = client_with_mock_repo
    mock_repo.search_text.side_effect = Exception("Search internal error")
    
    response = client.get("/repository/search_text?query=anything")
    
    assert response.status_code == 500
    assert "Error during text search: Search internal error" in response.json()["detail"]
    mock_repo.search_text.assert_called_once_with(query="anything", file_pattern=None)


# TODO: Add tests for /symbols and /search_text endpoints
# - Success cases
# - Error cases (file not found for symbols, missing params, internal errors)
# - Edge cases for search_text (empty query, no results, etc.) 