import logging
import traceback
from importlib.resources import files
from pathlib import Path
from typing import Any, ClassVar, Dict, List, Optional, cast

from tree_sitter_language_pack import get_language, get_parser

# Set up module-level logger
logger = logging.getLogger(__name__)

# Map file extensions to tree-sitter-languages names
LANGUAGES: dict[str, str] = {
    ".py": "python",
    ".js": "javascript",
    ".go": "go",
    ".rs": "rust",
    ".hcl": "hcl",
    ".tf": "hcl",
    ".ts": "typescript",
    ".tsx": "tsx",
    ".c": "c",
    ".rb": "ruby",
    ".java": "java",
    ".dart": "dart",
    ".kt": "kotlin",
    ".kts": "kotlin",
    ".cpp": "cpp",
    ".cc": "cpp",
    ".cxx": "cpp",
    ".hpp": "cpp",
    ".hxx": "cpp",
}


class LanguagePlugin:
    """Represents a language plugin with query files and configuration."""

    def __init__(
        self, name: str, extensions: List[str], query_files: List[str], query_dirs: Optional[List[str]] = None
    ):
        self.name = name
        self.extensions = extensions
        self.query_files = query_files  # List of .scm files to load
        self.query_dirs = query_dirs or []  # Additional directories to search for queries


class TreeSitterSymbolExtractor:
    """
    Multi-language symbol extractor using tree-sitter queries with plugin support.

    Supports:
    - Extending existing languages with additional query files
    - Registering completely new languages
    - Loading multiple .scm files per language
    """

    LANGUAGES = set(LANGUAGES.keys())
    _parsers: ClassVar[dict[str, Any]] = {}
    _queries: ClassVar[dict[str, Any]] = {}
    _custom_languages: ClassVar[dict[str, LanguagePlugin]] = {}
    _language_extensions: ClassVar[dict[str, List[str]]] = {}  # lang_name -> list of additional .scm files

    @classmethod
    def register_language(
        cls, name: str, extensions: List[str], query_files: List[str], query_dirs: Optional[List[str]] = None
    ) -> None:
        """Register a completely new language.

        Args:
            name: Language name (should match tree-sitter-language-pack name)
            extensions: List of file extensions (e.g., ['.kt', '.kts'])
            query_files: List of .scm query files to load
            query_dirs: Optional additional directories to search for queries
        """
        plugin = LanguagePlugin(name, extensions, query_files, query_dirs)
        cls._custom_languages[name] = plugin

        # Update LANGUAGES mapping
        for ext in extensions:
            LANGUAGES[ext] = name
            cls.LANGUAGES.add(ext)

        # Clear cached parsers and queries for this language
        for ext in extensions:
            cls._parsers.pop(ext, None)
            cls._queries.pop(ext, None)

        logger.info(f"Registered new language: {name} with extensions {extensions}")

    @classmethod
    def extend_language(cls, language: str, query_file: str) -> None:
        """Extend an existing language with additional query patterns.

        Args:
            language: Language name (e.g., 'python', 'javascript')
            query_file: Path to additional .scm file (relative to queries dir or absolute)
        """
        if language not in cls._language_extensions:
            cls._language_extensions[language] = []
        cls._language_extensions[language].append(query_file)

        # Clear cached queries for this language
        extensions_to_clear = [ext for ext, lang in LANGUAGES.items() if lang == language]
        for ext in extensions_to_clear:
            cls._queries.pop(ext, None)

        logger.info(f"Extended language {language} with query file: {query_file}")

    @classmethod
    def get_parser(cls, ext: str) -> Optional[Any]:
        if ext not in LANGUAGES:
            return None
        if ext not in cls._parsers:
            lang_name = LANGUAGES[ext]
            parser = get_parser(cast(Any, lang_name))  # type: ignore[arg-type]
            cls._parsers[ext] = parser
        return cls._parsers[ext]

    @classmethod
    def _load_query_files(cls, lang_name: str) -> str:
        """Load and combine all query files for a language."""
        query_contents = []

        # Check if this is a custom language
        if lang_name in cls._custom_languages:
            plugin = cls._custom_languages[lang_name]

            # Load files from custom plugin
            for query_file in plugin.query_files:
                try:
                    # Check if it's an absolute path
                    if Path(query_file).is_absolute():
                        with open(query_file, "r", encoding="utf-8") as f:
                            content = f.read()
                    else:
                        # Search in plugin directories first, then built-in
                        content = None
                        for query_dir in plugin.query_dirs:
                            try:
                                query_path = Path(query_dir) / query_file
                                if query_path.exists():
                                    with open(query_path, "r", encoding="utf-8") as f:
                                        content = f.read()
                                    break
                            except (FileNotFoundError, OSError):
                                continue

                        # Fallback to built-in queries directory
                        if content is None:
                            try:
                                package_files = files("kit.queries").joinpath(lang_name)
                                query_traversable = package_files.joinpath(query_file)
                                content = query_traversable.read_text(encoding="utf-8")
                            except (FileNotFoundError, OSError):
                                logger.warning(f"Could not find query file {query_file} for language {lang_name}")
                                continue

                    if content:
                        query_contents.append(content)
                        logger.debug(f"Loaded query file: {query_file}")

                except Exception as e:
                    logger.warning(f"Error loading query file {query_file}: {e}")
                    continue
        else:
            # Load built-in language queries
            try:
                # First try to load all .scm files in the language directory
                package_files = files("kit.queries").joinpath(lang_name)

                # Try to load tags.scm first (backward compatibility)
                try:
                    tags_traversable = package_files.joinpath("tags.scm")
                    tags_content = tags_traversable.read_text(encoding="utf-8")
                    query_contents.append(tags_content)
                    logger.debug(f"Loaded base tags.scm for {lang_name}")
                except (FileNotFoundError, OSError) as e:
                    if lang_name == "tsx":
                        # Fallback to TypeScript query definitions
                        logger.debug("TSX queries not found, falling back to TypeScript queries")
                        ts_tags_traversable = files("kit.queries").joinpath("typescript").joinpath("tags.scm")
                        tags_content = ts_tags_traversable.read_text(encoding="utf-8")
                        query_contents.append(tags_content)
                        logger.debug("Loaded TypeScript fallback tags.scm for tsx")
                    else:
                        logger.warning(f"No base tags.scm found for {lang_name}: {e}")

                # Load any additional .scm files in the directory
                try:
                    if hasattr(package_files, "iterdir"):
                        for query_file_traversable in package_files.iterdir():
                            if (
                                query_file_traversable.name.endswith(".scm")
                                and query_file_traversable.name != "tags.scm"
                            ):
                                try:
                                    content = query_file_traversable.read_text(encoding="utf-8")
                                    query_contents.append(content)
                                    logger.debug(f"Loaded additional query file: {query_file_traversable.name}")
                                except Exception as e:
                                    logger.warning(f"Error loading {query_file_traversable.name}: {e}")
                except (AttributeError, FileNotFoundError, OSError):
                    # AttributeError: package_files doesn't support iterdir
                    # FileNotFoundError/OSError: directory doesn't exist or access issues
                    if lang_name == "tsx":
                        # For TSX, try to load additional TypeScript files as fallback
                        try:
                            ts_package_files = files("kit.queries").joinpath("typescript")
                            if hasattr(ts_package_files, "iterdir"):
                                for query_file_traversable in ts_package_files.iterdir():
                                    if (
                                        query_file_traversable.name.endswith(".scm")
                                        and query_file_traversable.name != "tags.scm"
                                    ):
                                        try:
                                            content = query_file_traversable.read_text(encoding="utf-8")
                                            query_contents.append(content)
                                            logger.debug(
                                                f"Loaded additional TypeScript query file for tsx: {query_file_traversable.name}"
                                            )
                                        except (FileNotFoundError, OSError, UnicodeDecodeError) as file_error:
                                            # Only catch specific file-related errors, let other exceptions bubble up
                                            logger.warning(
                                                f"Error loading TypeScript query file {query_file_traversable.name}: {file_error}"
                                            )
                        except (AttributeError, FileNotFoundError, OSError) as ts_error:
                            # TypeScript directory access failed - log but don't fail completely
                            logger.debug(f"Could not access TypeScript queries for TSX fallback: {ts_error}")
                    # For non-TSX languages, silently skip additional files if directory access fails

            except Exception as e:
                logger.warning(f"Error loading built-in queries for {lang_name}: {e}")

        # Load language extensions
        if lang_name in cls._language_extensions:
            for extension_file in cls._language_extensions[lang_name]:
                try:
                    # Check if it's an absolute path
                    if Path(extension_file).is_absolute():
                        with open(extension_file, "r", encoding="utf-8") as f:
                            content = f.read()
                            query_contents.append(content)
                            logger.debug(f"Loaded extension file: {extension_file}")
                    else:
                        # Try to load from built-in queries directory
                        try:
                            package_files = files("kit.queries").joinpath(lang_name)
                            extension_traversable = package_files.joinpath(extension_file)
                            content = extension_traversable.read_text(encoding="utf-8")
                            query_contents.append(content)
                            logger.debug(f"Loaded extension file: {extension_file}")
                        except (FileNotFoundError, OSError):
                            logger.warning(f"Could not find extension file {extension_file} for language {lang_name}")

                except Exception as e:
                    logger.warning(f"Error loading extension file {extension_file}: {e}")

        # Combine all query contents
        combined_query = "\n\n".join(query_contents)
        if not combined_query.strip():
            logger.warning(f"No query content loaded for language {lang_name}")
            return ""

        logger.debug(f"Combined {len(query_contents)} query files for {lang_name}")
        return combined_query

    @classmethod
    def get_query(cls, ext: str) -> Optional[Any]:
        if ext not in LANGUAGES:
            logger.debug(f"get_query: Extension {ext} not supported.")
            return None
        if ext in cls._queries:
            logger.debug(f"get_query: query cached for ext {ext}")
            return cls._queries[ext]

        lang_name = LANGUAGES[ext]
        logger.debug(f"get_query: lang={lang_name}")

        try:
            # Load and combine all query files for this language
            combined_query_content = cls._load_query_files(lang_name)

            if not combined_query_content.strip():
                logger.warning(f"No query content available for language {lang_name}")
                return None

            language = get_language(cast(Any, lang_name))  # type: ignore[arg-type]
            query = language.query(combined_query_content)
            cls._queries[ext] = query
            logger.debug(f"get_query: Query loaded successfully for ext {ext}")
            return query

        except Exception as e:
            logger.error(f"get_query: Query compile error for ext {ext}: {e}")
            logger.error(traceback.format_exc())
            return None

    @classmethod
    def list_supported_languages(cls) -> Dict[str, List[str]]:
        """Return a mapping of language names to their supported extensions."""
        lang_to_extensions: Dict[str, List[str]] = {}
        for ext, lang in LANGUAGES.items():
            if lang not in lang_to_extensions:
                lang_to_extensions[lang] = []
            lang_to_extensions[lang].append(ext)
        return lang_to_extensions

    @classmethod
    def reset_plugins(cls) -> None:
        """Reset all custom languages and extensions. Useful for testing."""
        cls._custom_languages.clear()
        cls._language_extensions.clear()
        cls._queries.clear()
        cls._parsers.clear()

        # Reset LANGUAGES to original state
        global LANGUAGES
        original_languages = {
            ".py": "python",
            ".js": "javascript",
            ".go": "go",
            ".rs": "rust",
            ".hcl": "hcl",
            ".tf": "hcl",
            ".ts": "typescript",
            ".tsx": "tsx",
            ".c": "c",
            ".rb": "ruby",
            ".java": "java",
            ".dart": "dart",
            ".kt": "kotlin",
            ".kts": "kotlin",
            ".cpp": "cpp",
            ".cc": "cpp",
            ".cxx": "cpp",
            ".hpp": "cpp",
            ".hxx": "cpp",
        }
        LANGUAGES.clear()
        LANGUAGES.update(original_languages)
        cls.LANGUAGES = set(LANGUAGES.keys())

    @staticmethod
    def extract_symbols(ext: str, source_code: str) -> List[Dict[str, Any]]:
        """Extracts symbols from source code using tree-sitter queries."""
        logger.debug(f"[EXTRACT] Attempting to extract symbols for ext: {ext}")
        symbols: List[Dict[str, Any]] = []
        query = TreeSitterSymbolExtractor.get_query(ext)
        parser = TreeSitterSymbolExtractor.get_parser(ext)

        if not query or not parser:
            logger.warning(f"[EXTRACT] No query or parser available for extension: {ext}")
            return []

        try:
            tree = parser.parse(bytes(source_code, "utf8"))
            root = tree.root_node

            # tree-sitter compatibility
            if hasattr(query, "matches"):
                raw_matches = query.matches(root)  # type: ignore[attr-defined]
                logger.debug(f"[EXTRACT] Found {len(raw_matches)} matches via Query.matches().")
                # Convert to unified (pattern_index, captures) structure expected below
                match_tuples = list(raw_matches)  # already in correct format
            else:
                # Newer API – build a single pseudo-match dictionary grouping all captures
                captures_dict: Dict[str, List[Any]] = {}
                for capture_name, node in query.captures(root):  # type: ignore[attr-defined]
                    captures_dict.setdefault(capture_name, []).append(node)
                match_tuples = [(0, captures_dict)]
                logger.debug(
                    f"[EXTRACT] Found {sum(len(v) for v in captures_dict.values())} captures via Query.captures()."
                )

            # Now process matches
            for pattern_index, captures in match_tuples:
                logger.debug(f"[MATCH pattern={pattern_index}] Processing match with captures: {list(captures.keys())}")

                # Determine symbol name: prefer @name, fallback to @type for blocks like terraform/locals
                node_candidate = None
                if "name" in captures:
                    node_candidate = captures["name"]
                elif "type" in captures:
                    node_candidate = captures["type"]
                else:
                    # Fallback: take the first capture node
                    first_capture_node = next(iter(captures.values()), None)
                    if not first_capture_node:
                        continue
                    node_candidate = first_capture_node

                # Handle list of nodes (tree-sitter may return a list)
                if isinstance(node_candidate, list):
                    if not node_candidate:
                        continue  # skip empty list
                    actual_name_node = node_candidate[0]
                else:
                    actual_name_node = node_candidate

                # Now extract symbol name as before
                symbol_name = (
                    actual_name_node.text.decode() if hasattr(actual_name_node, "text") else str(actual_name_node)
                )
                # HCL: Strip quotes from string literals
                if ext == ".tf" and hasattr(actual_name_node, "type") and actual_name_node.type == "string_lit":
                    if len(symbol_name) >= 2 and symbol_name.startswith('"') and symbol_name.endswith('"'):
                        symbol_name = symbol_name[1:-1]

                definition_capture = next(
                    ((name, node) for name, node in captures.items() if name.startswith("definition.")), None
                )
                subtype = None
                if definition_capture:
                    definition_capture_name, definition_node = definition_capture
                    symbol_type = definition_capture_name.split(".")[-1]
                    # HCL: For resource/data, combine type and name, and set subtype to the specific resource/data type
                    if ext == ".tf" and symbol_type in ["resource", "data"]:
                        type_node = captures.get("type")
                        if type_node:
                            if isinstance(type_node, list):
                                type_node = type_node[0] if type_node else None
                            if type_node and hasattr(type_node, "text"):
                                type_name = type_node.text.decode()
                                if hasattr(type_node, "type") and type_node.type == "string_lit":
                                    if len(type_name) >= 2 and type_name.startswith('"') and type_name.endswith('"'):
                                        type_name = type_name[1:-1]
                                symbol_name = f"{type_name}.{symbol_name}"
                                subtype = type_name
                else:
                    # Fallback: infer symbol type from first capture label (e.g., 'function', 'class')
                    fallback_label = next(iter(captures.keys()), "symbol")
                    symbol_type = fallback_label.removeprefix("definition.").removeprefix("@")

                # Determine the node for the full symbol body, its span, and its code content.
                # Default to actual_name_node if no specific body capture is found.
                node_for_body_span_and_code = actual_name_node
                if definition_capture:
                    _, captured_body_node = definition_capture  # This is the node from @definition.foo
                    temp_body_node = None
                    if isinstance(captured_body_node, list):
                        temp_body_node = captured_body_node[0] if captured_body_node else None
                    else:
                        temp_body_node = captured_body_node

                    if temp_body_node:  # If a valid body node was found from definition_capture
                        node_for_body_span_and_code = temp_body_node

                # Extract start_line, end_line, and code content from node_for_body_span_and_code
                symbol_start_line = node_for_body_span_and_code.start_point[0]
                symbol_end_line = node_for_body_span_and_code.end_point[0]

                if hasattr(node_for_body_span_and_code, "text") and isinstance(node_for_body_span_and_code.text, bytes):
                    symbol_code_content = node_for_body_span_and_code.text.decode("utf-8", errors="ignore")
                elif hasattr(node_for_body_span_and_code, "start_byte") and hasattr(
                    node_for_body_span_and_code, "end_byte"
                ):
                    # Fallback for nodes where .text might not be the full desired content or not directly available as decodable bytes
                    symbol_code_content = source_code[
                        node_for_body_span_and_code.start_byte : node_for_body_span_and_code.end_byte
                    ]
                else:
                    # Last resort, if node_for_body_span_and_code is unusual and lacks .text (bytes) or start/end_byte
                    symbol_code_content = symbol_name  # Fallback to just the name string

                symbol = {
                    "name": symbol_name,  # symbol_name is from actual_name_node, potentially modified by HCL logic
                    "type": symbol_type,
                    "start_line": symbol_start_line,
                    "end_line": symbol_end_line,
                    "code": symbol_code_content,
                }
                if subtype:
                    symbol["subtype"] = subtype
                symbols.append(symbol)
                continue

        except Exception as e:
            logger.error(f"[EXTRACT] Error parsing or processing file with ext {ext}: {e}")
            logger.error(traceback.format_exc())
            return []  # Return empty list on error

        logger.debug(f"[EXTRACT] Finished extraction for ext {ext}. Found {len(symbols)} symbols.")

        # Deduplicate symbols that may be captured by multiple query
        # patterns (e.g., both a generic class capture and an exported
        # class capture in TypeScript).  We consider a symbol duplicate
        # if its *name*, *type*, and *start/end* lines are identical.
        unique_symbols: list[dict[str, Any]] = []
        seen: set[tuple[Any, ...]] = set()
        for sym in symbols:
            key = (sym.get("name"), sym.get("type"), sym.get("start_line"), sym.get("end_line"))
            if key in seen:
                logger.debug(f"[EXTRACT] Removing duplicate symbol: {key}")
                continue
            seen.add(key)
            unique_symbols.append(sym)

        if len(unique_symbols) < len(symbols):
            logger.debug(f"[EXTRACT] Deduplicated symbols list: {len(symbols)} -> {len(unique_symbols)} for ext {ext}")

        return unique_symbols
