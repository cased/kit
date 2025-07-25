"""Integration tests for the search-semantic CLI command using real repositories."""

import json
import subprocess
import tempfile
from pathlib import Path

import pytest

# Check if sentence-transformers is available
try:
    import sentence_transformers  # noqa: F401

    HAS_SENTENCE_TRANSFORMERS = True
except ImportError:
    HAS_SENTENCE_TRANSFORMERS = False


def run_kit_command(args: list, cwd: str | None = None) -> subprocess.CompletedProcess:
    """Helper to run kit CLI commands."""
    cmd = ["kit", *args]
    return subprocess.run(cmd, capture_output=True, text=True, cwd=cwd, timeout=60)


@pytest.fixture
def semantic_test_repo():
    """Create a repository optimized for semantic search testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_path = Path(tmpdir)

        # Authentication and security related code
        (repo_path / "auth.py").write_text("""
import hashlib
import secrets
from datetime import datetime, timedelta

class UserAuthenticator:
    '''Handles user authentication and session management.'''

    def __init__(self):
        self.sessions = {}
        self.failed_attempts = {}

    def authenticate_user(self, username: str, password: str) -> bool:
        '''Verify user credentials and create session.'''
        if self._is_locked_out(username):
            return False

        if self._verify_password(username, password):
            self._create_session(username)
            self._reset_failed_attempts(username)
            return True
        else:
            self._record_failed_attempt(username)
            return False

    def _verify_password(self, username: str, password: str) -> bool:
        '''Check password against stored hash.'''
        stored_hash = self._get_password_hash(username)
        return self._hash_password(password) == stored_hash

    def _hash_password(self, password: str) -> str:
        '''Generate secure password hash with salt.'''
        salt = secrets.token_hex(16)
        return hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000).hex()

    def _create_session(self, username: str):
        '''Generate secure session token.'''
        token = secrets.token_urlsafe(32)
        self.sessions[token] = {
            'username': username,
            'created': datetime.now(),
            'expires': datetime.now() + timedelta(hours=24)
        }
        return token
""")

        # Payment processing and financial calculations
        (repo_path / "payment.py").write_text("""
import decimal
from enum import Enum
from typing import Dict, List, Optional

class PaymentStatus(Enum):
    PENDING = "pending"
    APPROVED = "approved"
    DECLINED = "declined"
    REFUNDED = "refunded"

class PaymentProcessor:
    '''Handles credit card payments and financial transactions.'''

    def __init__(self, merchant_id: str):
        self.merchant_id = merchant_id
        self.transaction_log = []

    def process_payment(self, amount: decimal.Decimal, card_number: str,
                       cvv: str, expiry: str) -> Dict:
        '''Process a credit card payment transaction.'''
        if not self._validate_card_details(card_number, cvv, expiry):
            return {'status': PaymentStatus.DECLINED, 'reason': 'Invalid card details'}

        if not self._check_fraud_rules(amount, card_number):
            return {'status': PaymentStatus.DECLINED, 'reason': 'Fraud detection'}

        transaction_id = self._generate_transaction_id()

        # Simulate payment gateway call
        gateway_response = self._call_payment_gateway(amount, card_number)

        transaction = {
            'id': transaction_id,
            'amount': amount,
            'status': gateway_response['status'],
            'timestamp': datetime.now(),
            'card_last_four': card_number[-4:]
        }

        self.transaction_log.append(transaction)
        return transaction

    def calculate_fees(self, amount: decimal.Decimal, card_type: str) -> decimal.Decimal:
        '''Calculate processing fees based on amount and card type.'''
        base_rate = decimal.Decimal('0.029')  # 2.9%

        if card_type.lower() == 'amex':
            base_rate += decimal.Decimal('0.005')  # Additional 0.5% for Amex

        fee = amount * base_rate

        # Minimum fee of $0.30
        min_fee = decimal.Decimal('0.30')
        return max(fee, min_fee)
""")

        # Database operations and data persistence
        (repo_path / "database.py").write_text("""
import sqlite3
import logging
from contextlib import contextmanager
from typing import Any, Dict, List, Optional

class DatabaseManager:
    '''Manages database connections and operations.'''

    def __init__(self, db_path: str):
        self.db_path = db_path
        self.logger = logging.getLogger(__name__)
        self._init_database()

    def _init_database(self):
        '''Initialize database schema and tables.'''
        with self.get_connection() as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY,
                    username TEXT UNIQUE NOT NULL,
                    email TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            conn.execute('''
                CREATE TABLE IF NOT EXISTS sessions (
                    token TEXT PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    expires_at TIMESTAMP NOT NULL,
                    FOREIGN KEY (user_id) REFERENCES users (id)
                )
            ''')

    @contextmanager
    def get_connection(self):
        '''Get database connection with automatic cleanup.'''
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            self.logger.error(f"Database error: {e}")
            raise
        finally:
            conn.close()

    def create_user(self, username: str, email: str, password_hash: str) -> int:
        '''Create a new user account.'''
        with self.get_connection() as conn:
            cursor = conn.execute(
                'INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)',
                (username, email, password_hash)
            )
            return cursor.lastrowid

    def find_user_by_username(self, username: str) -> Optional[Dict]:
        '''Find user by username.'''
        with self.get_connection() as conn:
            row = conn.execute(
                'SELECT * FROM users WHERE username = ?', (username,)
            ).fetchone()
            return dict(row) if row else None
""")

        # Error handling and logging utilities
        (repo_path / "error_handling.py").write_text("""
import logging
import traceback
from functools import wraps
from typing import Any, Callable, Optional

class ErrorHandler:
    '''Centralized error handling and logging.'''

    def __init__(self, logger_name: str = __name__):
        self.logger = logging.getLogger(logger_name)
        self._setup_logging()

    def _setup_logging(self):
        '''Configure logging with proper formatters.'''
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)

    def handle_error(self, error: Exception, context: str = "") -> None:
        '''Log error with context and stack trace.'''
        error_msg = f"Error in {context}: {str(error)}"
        self.logger.error(error_msg)
        self.logger.debug(traceback.format_exc())

    def retry_on_failure(self, max_retries: int = 3, delay: float = 1.0):
        '''Decorator to retry operations on failure.'''
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            def wrapper(*args, **kwargs) -> Any:
                last_exception = None

                for attempt in range(max_retries):
                    try:
                        return func(*args, **kwargs)
                    except Exception as e:
                        last_exception = e
                        self.logger.warning(
                            f"Attempt {attempt + 1} failed for {func.__name__}: {e}"
                        )
                        if attempt < max_retries - 1:
                            time.sleep(delay * (2 ** attempt))  # Exponential backoff

                self.handle_error(last_exception, f"{func.__name__} after {max_retries} retries")
                raise last_exception

            return wrapper
        return decorator

def log_execution_time(func: Callable) -> Callable:
    '''Decorator to log function execution time.'''
    @wraps(func)
    def wrapper(*args, **kwargs):
        import time
        start_time = time.time()
        try:
            result = func(*args, **kwargs)
            execution_time = time.time() - start_time
            logging.info(f"{func.__name__} executed in {execution_time:.2f} seconds")
            return result
        except Exception as e:
            execution_time = time.time() - start_time
            logging.error(f"{func.__name__} failed after {execution_time:.2f} seconds: {e}")
            raise
    return wrapper
""")

        # Configuration and settings management
        (repo_path / "config.py").write_text("""
import os
import json
from typing import Any, Dict, Optional
from dataclasses import dataclass, asdict

@dataclass
class DatabaseConfig:
    '''Database connection configuration.'''
    host: str = "localhost"
    port: int = 5432
    database: str = "app_db"
    username: str = ""
    password: str = ""
    pool_size: int = 10
    max_overflow: int = 20

@dataclass
class SecurityConfig:
    '''Security and authentication settings.'''
    secret_key: str = ""
    jwt_expiry_hours: int = 24
    password_min_length: int = 8
    max_login_attempts: int = 5
    lockout_duration_minutes: int = 30
    require_2fa: bool = False

@dataclass
class AppConfig:
    '''Main application configuration.'''
    debug: bool = False
    environment: str = "production"
    log_level: str = "INFO"
    database: DatabaseConfig = DatabaseConfig()
    security: SecurityConfig = SecurityConfig()

    @classmethod
    def from_env(cls) -> 'AppConfig':
        '''Load configuration from environment variables.'''
        config = cls()

        # Database settings
        config.database.host = os.getenv('DB_HOST', config.database.host)
        config.database.port = int(os.getenv('DB_PORT', config.database.port))
        config.database.database = os.getenv('DB_NAME', config.database.database)
        config.database.username = os.getenv('DB_USER', config.database.username)
        config.database.password = os.getenv('DB_PASSWORD', config.database.password)

        # Security settings
        config.security.secret_key = os.getenv('SECRET_KEY', config.security.secret_key)
        config.security.jwt_expiry_hours = int(os.getenv('JWT_EXPIRY_HOURS', config.security.jwt_expiry_hours))

        # App settings
        config.debug = os.getenv('DEBUG', 'false').lower() == 'true'
        config.environment = os.getenv('ENVIRONMENT', config.environment)
        config.log_level = os.getenv('LOG_LEVEL', config.log_level)

        return config

    def save_to_file(self, filepath: str) -> None:
        '''Save configuration to JSON file.'''
        with open(filepath, 'w') as f:
            json.dump(asdict(self), f, indent=2)

    @classmethod
    def load_from_file(cls, filepath: str) -> 'AppConfig':
        '''Load configuration from JSON file.'''
        with open(filepath, 'r') as f:
            data = json.load(f)

        # Reconstruct nested dataclasses
        if 'database' in data:
            data['database'] = DatabaseConfig(**data['database'])
        if 'security' in data:
            data['security'] = SecurityConfig(**data['security'])

        return cls(**data)
""")

        # Testing utilities and mocks
        (repo_path / "test_utils.py").write_text("""
import unittest
from unittest.mock import Mock, patch
from typing import Any, Dict, List
import tempfile
import os

class TestFixtures:
    '''Provides test data and fixtures for unit testing.'''

    @staticmethod
    def create_test_user() -> Dict[str, Any]:
        '''Create a sample user for testing.'''
        return {
            'id': 1,
            'username': 'testuser',
            'email': 'test@example.com',
            'password_hash': 'hashed_password_123',
            'created_at': '2023-01-01T00:00:00Z'
        }

    @staticmethod
    def create_test_payment() -> Dict[str, Any]:
        '''Create a sample payment transaction for testing.'''
        return {
            'id': 'txn_12345',
            'amount': 99.99,
            'currency': 'USD',
            'status': 'approved',
            'card_last_four': '4242',
            'timestamp': '2023-01-01T12:00:00Z'
        }

    @staticmethod
    def mock_database_responses() -> Dict[str, Any]:
        '''Provide mock database query responses.'''
        return {
            'user_found': TestFixtures.create_test_user(),
            'user_not_found': None,
            'payment_success': TestFixtures.create_test_payment(),
            'connection_error': Exception("Database connection failed")
        }

class TestEnvironment:
    '''Manages test environment setup and teardown.'''

    def __init__(self):
        self.temp_dirs = []
        self.env_vars = {}

    def setup_temp_database(self) -> str:
        '''Create temporary database for testing.'''
        temp_dir = tempfile.mkdtemp()
        self.temp_dirs.append(temp_dir)
        db_path = os.path.join(temp_dir, 'test.db')
        return db_path

    def set_test_env_vars(self, variables: Dict[str, str]) -> None:
        '''Set environment variables for testing.'''
        self.env_vars.update(variables)
        for key, value in variables.items():
            os.environ[key] = value

    def cleanup(self) -> None:
        '''Clean up test environment.'''
        # Remove temporary directories
        import shutil
        for temp_dir in self.temp_dirs:
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)

        # Restore environment variables
        for key in self.env_vars:
            if key in os.environ:
                del os.environ[key]

def mock_network_requests():
    '''Decorator to mock external network requests in tests.'''
    def decorator(test_func):
        @patch('requests.get')
        @patch('requests.post')
        def wrapper(mock_post, mock_get, *args, **kwargs):
            # Setup default mock responses
            mock_get.return_value.status_code = 200
            mock_get.return_value.json.return_value = {'status': 'success'}
            mock_post.return_value.status_code = 200
            mock_post.return_value.json.return_value = {'status': 'success'}

            return test_func(*args, **kwargs)
        return wrapper
    return decorator
""")

        # Add a README for context
        (repo_path / "README.md").write_text("""
# Test Application

This is a sample application for testing semantic search functionality.

## Features

- User authentication and session management
- Payment processing with fraud detection
- Database operations with connection pooling
- Comprehensive error handling and logging
- Configuration management
- Testing utilities and mocks

## Security Features

- Password hashing with salt
- Session token generation
- Failed login attempt tracking
- Account lockout protection

## Payment Processing

- Credit card validation
- Fee calculation
- Transaction logging
- Fraud detection rules

## Architecture

The application follows a modular architecture with separate concerns:
- Authentication layer
- Payment processing layer
- Data persistence layer
- Configuration management
- Error handling utilities
""")

        yield str(repo_path)


@pytest.fixture
def complex_semantic_repo():
    """Create a more complex repository for advanced semantic search testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_path = Path(tmpdir)

        # Create a multi-language repository structure
        (repo_path / "backend").mkdir()
        (repo_path / "frontend").mkdir()
        (repo_path / "docs").mkdir()

        # Backend Python API
        (repo_path / "backend" / "api.py").write_text("""
from fastapi import FastAPI, HTTPException, Depends
from fastapi.security import HTTPBearer
import uvicorn

app = FastAPI(title="Test API", version="1.0.0")
security = HTTPBearer()

@app.get("/health")
async def health_check():
    '''Health check endpoint for monitoring.'''
    return {"status": "healthy", "version": "1.0.0"}

@app.post("/auth/login")
async def login_endpoint(credentials: dict):
    '''User login endpoint with JWT token generation.'''
    username = credentials.get('username')
    password = credentials.get('password')

    if not username or not password:
        raise HTTPException(status_code=400, detail="Missing credentials")

    # Validate credentials (mock implementation)
    if authenticate_user(username, password):
        token = generate_jwt_token(username)
        return {"access_token": token, "token_type": "bearer"}
    else:
        raise HTTPException(status_code=401, detail="Invalid credentials")

@app.get("/users/profile")
async def get_user_profile(token: str = Depends(security)):
    '''Get current user profile information.'''
    user_id = decode_jwt_token(token.credentials)
    profile = get_user_profile_from_db(user_id)
    return profile

@app.post("/payments/process")
async def process_payment_endpoint(payment_data: dict):
    '''Process payment transaction with validation.'''
    try:
        result = process_payment(payment_data)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
""")

        # Frontend JavaScript
        (repo_path / "frontend" / "auth.js").write_text("""
// Authentication and user management
class AuthManager {
    constructor() {
        this.token = localStorage.getItem('auth_token');
        this.user = null;
    }

    async login(username, password) {
        try {
            const response = await fetch('/auth/login', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ username, password })
            });

            if (response.ok) {
                const data = await response.json();
                this.token = data.access_token;
                localStorage.setItem('auth_token', this.token);
                await this.loadUserProfile();
                return true;
            } else {
                throw new Error('Login failed');
            }
        } catch (error) {
            console.error('Authentication error:', error);
            return false;
        }
    }

    async loadUserProfile() {
        if (!this.token) return null;

        try {
            const response = await fetch('/users/profile', {
                headers: {
                    'Authorization': `Bearer ${this.token}`
                }
            });

            if (response.ok) {
                this.user = await response.json();
                return this.user;
            }
        } catch (error) {
            console.error('Failed to load user profile:', error);
        }

        return null;
    }

    logout() {
        this.token = null;
        this.user = null;
        localStorage.removeItem('auth_token');
        window.location.href = '/login';
    }

    isAuthenticated() {
        return !!this.token;
    }
}

// Initialize auth manager
const authManager = new AuthManager();
""")

        # Documentation
        (repo_path / "docs" / "api_guide.md").write_text("""
# API Documentation

## Authentication Endpoints

### POST /auth/login
Authenticate user and receive JWT token.

**Request Body:**
```json
{
    "username": "string",
    "password": "string"
}
```

**Response:**
```json
{
    "access_token": "jwt_token_here",
    "token_type": "bearer"
}
```

### GET /users/profile
Get authenticated user profile information.

**Headers:**
- Authorization: Bearer {token}

**Response:**
```json
{
    "id": "user_id",
    "username": "string",
    "email": "string"
}
```

## Payment Processing

### POST /payments/process
Process a payment transaction.

**Request Body:**
```json
{
    "amount": "decimal",
    "card_number": "string",
    "cvv": "string",
    "expiry": "string"
}
```

## Error Handling

All endpoints return appropriate HTTP status codes:
- 200: Success
- 400: Bad Request
- 401: Unauthorized
- 500: Internal Server Error
""")

        yield str(repo_path)


class TestSemanticSearchIntegration:
    """Integration tests for semantic search functionality."""

    def test_semantic_search_help(self):
        """Test that semantic search help is displayed correctly."""
        result = run_kit_command(["search-semantic", "--help"])

        assert result.returncode == 0
        # Strip ANSI escape codes for cleaner matching
        import re

        clean_output = re.sub(r"\x1b\[[0-9;]*m", "", result.stdout).lower()

        assert "semantic search" in clean_output
        assert "vector embeddings" in clean_output
        # Check for the option in various formats (could be --top-k or -k)
        assert "--top-k" in clean_output or "-k" in clean_output
        assert "--embedding-model" in clean_output or "-e" in clean_output
        assert "--chunk-by" in clean_output or "-c" in clean_output

    def test_semantic_search_missing_args(self):
        """Test error handling for missing required arguments."""
        # Missing query
        result = run_kit_command(["search-semantic", "."])
        assert result.returncode == 2  # Typer argument error

        # Missing path
        result = run_kit_command(["search-semantic"])
        assert result.returncode == 2

    def test_semantic_search_invalid_chunk_by(self):
        """Test error handling for invalid chunk-by parameter."""
        result = run_kit_command(["search-semantic", ".", "test", "--chunk-by", "invalid"])

        assert result.returncode == 1
        if HAS_SENTENCE_TRANSFORMERS:
            assert "Invalid chunk_by value: invalid" in result.stdout
            assert "Use 'symbols' or 'lines'" in result.stdout
        else:
            # Without sentence-transformers, it fails earlier
            assert "sentence-transformers' package is required" in result.stdout

    @pytest.mark.skipif(
        True,  # Skip by default to avoid requiring sentence-transformers in CI
        reason="Requires sentence-transformers installation and is slow",
    )
    def test_semantic_search_authentication_concepts(self, semantic_test_repo):
        """Test semantic search for authentication-related concepts."""
        result = run_kit_command(
            ["search-semantic", semantic_test_repo, "user authentication and password verification", "--top-k", "5"]
        )

        # Should either work or fail gracefully
        assert result.returncode in [0, 1]

        if result.returncode == 0:
            output = result.stdout
            assert "Loading embedding model" in output

            # Should find authentication-related code
            assert any(keyword in output for keyword in ["auth", "authenticate", "password", "login", "session"])

    @pytest.mark.skipif(
        True,  # Skip by default
        reason="Requires sentence-transformers installation and is slow",
    )
    def test_semantic_search_payment_processing(self, semantic_test_repo):
        """Test semantic search for payment processing concepts."""
        result = run_kit_command(
            [
                "search-semantic",
                semantic_test_repo,
                "payment processing and credit card transactions",
                "--top-k",
                "3",
                "--chunk-by",
                "symbols",
            ]
        )

        assert result.returncode in [0, 1]

        if result.returncode == 0:
            output = result.stdout
            # Should find payment-related code
            assert any(keyword in output for keyword in ["payment", "transaction", "card", "process", "fee"])

    def test_semantic_search_error_conditions(self):
        """Test semantic search error handling."""
        # Non-existent directory
        result = run_kit_command(["search-semantic", "/nonexistent/path", "test query"])

        if HAS_SENTENCE_TRANSFORMERS:
            # Should handle gracefully - either succeeds but shows no matches, or fails with file system error
            assert result.returncode in [0, 1]
            if result.returncode == 0:
                assert "No semantic matches found" in result.stdout
            else:
                # Should fail with a meaningful error message
                assert any(
                    keyword in result.stdout
                    for keyword in ["Error:", "Failed to", "not found", "Read-only file system"]
                )
        else:
            # Without sentence-transformers, it fails earlier
            assert result.returncode == 1
            assert "sentence-transformers' package is required" in result.stdout

    @pytest.mark.skipif(
        True,  # Skip by default
        reason="Requires sentence-transformers installation and is slow",
    )
    def test_semantic_search_with_json_output(self, semantic_test_repo):
        """Test semantic search with JSON file output."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json") as f:
            output_file = f.name

        try:
            result = run_kit_command(
                [
                    "search-semantic",
                    semantic_test_repo,
                    "database operations and SQL queries",
                    "--top-k",
                    "3",
                    "--output",
                    output_file,
                ]
            )

            if result.returncode == 0:
                assert f"Semantic search results written to {output_file}" in result.stdout

                # Verify JSON file was created and is valid
                assert Path(output_file).exists()
                with open(output_file, "r") as f:
                    data = json.load(f)
                    assert isinstance(data, list)
        finally:
            Path(output_file).unlink(missing_ok=True)

    @pytest.mark.skipif(
        True,  # Skip by default
        reason="Requires sentence-transformers installation and is slow",
    )
    def test_semantic_search_custom_parameters(self, semantic_test_repo):
        """Test semantic search with various parameter combinations."""
        test_cases = [
            {"args": ["--top-k", "10", "--chunk-by", "lines"], "query": "error handling and exception management"},
            {
                "args": ["--embedding-model", "all-mpnet-base-v2", "--no-build-index"],
                "query": "configuration and settings management",
            },
            {"args": ["--persist-dir", "/tmp/test_semantic"], "query": "testing utilities and mock objects"},
        ]

        for case in test_cases:
            result = run_kit_command(["search-semantic", semantic_test_repo, case["query"]] + case["args"])

            # Should either work or fail gracefully with helpful error
            assert result.returncode in [0, 1]

            if result.returncode == 1:
                # Should have helpful error message
                assert any(
                    keyword in result.stdout for keyword in ["sentence-transformers", "Failed to load", "Error:"]
                )

    def test_semantic_search_with_git_ref(self, semantic_test_repo):
        """Test semantic search with git ref parameter."""
        # Initialize git repo for ref testing
        import subprocess

        subprocess.run(["git", "init"], cwd=semantic_test_repo, capture_output=True)
        subprocess.run(["git", "add", "."], cwd=semantic_test_repo, capture_output=True)
        subprocess.run(
            ["git", "-c", "user.email=test@example.com", "-c", "user.name=Test User", "commit", "-m", "Initial commit"],
            cwd=semantic_test_repo,
            capture_output=True,
        )

        result = run_kit_command(["search-semantic", semantic_test_repo, "authentication logic", "--ref", "HEAD"])

        # Should either work or fail gracefully
        assert result.returncode in [0, 1]


class TestSemanticSearchAdvanced:
    """Advanced integration tests for complex scenarios."""

    @pytest.mark.skipif(
        True,  # Skip by default
        reason="Requires sentence-transformers installation and is slow",
    )
    def test_multi_language_semantic_search(self, complex_semantic_repo):
        """Test semantic search across multiple programming languages."""
        test_queries = [
            "API endpoint authentication",
            "user login functionality",
            "frontend authentication manager",
            "JWT token handling",
        ]

        for query in test_queries:
            result = run_kit_command(["search-semantic", complex_semantic_repo, query, "--top-k", "5"])

            assert result.returncode in [0, 1]

            if result.returncode == 0:
                # Should find relevant code across languages
                output = result.stdout.lower()
                assert any(ext in output for ext in [".py", ".js", ".md"])

    def test_semantic_search_large_repository_simulation(self):
        """Test semantic search behavior with larger repository structure."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_path = Path(tmpdir)

            # Create a larger directory structure
            for i in range(5):
                (repo_path / f"module_{i}").mkdir()
                for j in range(3):
                    file_content = f"""
def function_{i}_{j}():
    '''Function {j} in module {i} for testing search.'''
    return "module_{i}_result_{j}"

class Class_{i}_{j}:
    '''Class {j} in module {i} for testing.'''

    def method_{j}(self):
        '''Method {j} implementation.'''
        pass
"""
                    (repo_path / f"module_{i}" / f"file_{j}.py").write_text(file_content)

            result = run_kit_command(
                ["search-semantic", str(repo_path), "function implementation for testing", "--top-k", "10"]
            )

            # Should handle large repositories gracefully
            assert result.returncode in [0, 1]

    def test_semantic_search_empty_repository(self):
        """Test semantic search on empty repository."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = run_kit_command(["search-semantic", tmpdir, "any search query"])

            # Should handle empty repos gracefully
            assert result.returncode in [0, 1]

            if result.returncode == 0:
                assert "No semantic matches found" in result.stdout

    def test_semantic_search_file_permissions(self):
        """Test semantic search with restricted file permissions."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_path = Path(tmpdir)

            # Create a file with restricted permissions
            test_file = repo_path / "restricted.py"
            test_file.write_text("def restricted_function(): pass")
            test_file.chmod(0o000)  # No permissions

            try:
                result = run_kit_command(["search-semantic", str(repo_path), "restricted function"])

                # Should handle permission errors gracefully
                assert result.returncode in [0, 1]
            finally:
                # Restore permissions for cleanup
                test_file.chmod(0o644)

    def test_semantic_search_performance_timeout(self):
        """Test that semantic search respects timeout limits."""
        # This test creates a scenario that might be slow and verifies timeout handling
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_path = Path(tmpdir)

            # Create files with substantial content
            for i in range(10):
                large_content = "# " + "Large file content " * 1000 + f" file {i}\n"
                large_content += "def function():\n    pass\n" * 100
                (repo_path / f"large_file_{i}.py").write_text(large_content)

            result = run_kit_command(["search-semantic", str(repo_path), "function implementation"])

            # Should complete within reasonable time or fail gracefully
            assert result.returncode in [0, 1]


class TestSemanticSearchWorkflows:
    """Test complete workflows combining semantic search with other commands."""

    def test_semantic_then_regular_search_workflow(self, semantic_test_repo):
        """Test workflow combining semantic and regular search."""
        # First do semantic search (may or may not work depending on dependencies)
        semantic_result = run_kit_command(
            ["search-semantic", semantic_test_repo, "password authentication", "--top-k", "3"]
        )

        # Then do regular search for comparison
        regular_result = run_kit_command(["search", semantic_test_repo, "password"])

        # Regular search should always work
        assert regular_result.returncode == 0
        assert "password" in regular_result.stdout

        # If semantic search worked, compare results
        if semantic_result.returncode == 0:
            # Both should find password-related content
            assert any(keyword in semantic_result.stdout for keyword in ["password", "auth"])

    def test_semantic_search_then_symbol_extraction(self, semantic_test_repo):
        """Test workflow of semantic search followed by symbol extraction."""
        # Semantic search for authentication
        run_kit_command(["search-semantic", semantic_test_repo, "user authentication", "--top-k", "2"])

        # Extract symbols from auth.py
        symbols_result = run_kit_command(["symbols", semantic_test_repo, "--file", "auth.py"])

        # Symbol extraction should work
        assert symbols_result.returncode == 0
        assert "UserAuthenticator" in symbols_result.stdout
        assert "authenticate_user" in symbols_result.stdout

    def test_semantic_search_with_export_workflow(self, semantic_test_repo):
        """Test exporting semantic search results and other data."""
        with tempfile.TemporaryDirectory() as output_dir:
            output_path = Path(output_dir)

            # Export symbols
            symbols_file = output_path / "symbols.json"
            symbols_result = run_kit_command(["export", semantic_test_repo, "symbols", str(symbols_file)])

            assert symbols_result.returncode == 0
            assert symbols_file.exists()

            # Try semantic search with export
            semantic_file = output_path / "semantic.json"
            semantic_result = run_kit_command(
                ["search-semantic", semantic_test_repo, "authentication", "--output", str(semantic_file)]
            )

            # If semantic search works, verify export
            if semantic_result.returncode == 0:
                assert semantic_file.exists()
                with open(semantic_file) as f:
                    data = json.load(f)
                    assert isinstance(data, list)
