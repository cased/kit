import logging
import traceback
from importlib.resources import files  # type: ignore[no-redef]
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
}


class TreeSitterSymbolExtractor:
    """
    Multi-language symbol extractor using tree-sitter queries (tags.scm).
    Register new languages by adding to LANGUAGES and providing a tags.scm.
    """

    LANGUAGES = set(LANGUAGES.keys())
    _parsers: ClassVar[dict[str, Any]] = {}
    _queries: ClassVar[dict[str, Any]] = {}

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
    def get_query(cls, ext: str) -> Optional[Any]:
        if ext not in LANGUAGES:
            logger.debug(f"get_query: Extension {ext} not supported.")
            return None
        if ext in cls._queries:
            logger.debug(f"get_query: query cached for ext {ext}")
            return cls._queries[ext]

        lang_name = LANGUAGES[ext]
        logger.debug(f"get_query: lang={lang_name}")
        resource_package = f"kit.queries.{lang_name}"
        try:
            language = get_language(cast(Any, lang_name))  # type: ignore[arg-type]

            # Prefer tags under the language's own directory (e.g., tsx/) but
            # gracefully fall back to TypeScript's tags if none are found.
            package_files = files("kit.queries").joinpath(lang_name)
            tags_path = package_files.joinpath("tags.scm")

            try:
                tags_content = tags_path.read_text(encoding="utf-8")
            except (FileNotFoundError, OSError) as e:
                if lang_name == "tsx":
                    # Fallback to TypeScript query definitions – they work for most TSX constructs.
                    tags_path = files("kit.queries").joinpath("typescript").joinpath("tags.scm")
                    tags_content = tags_path.read_text(encoding="utf-8")
                else:
                    raise e
            query = language.query(tags_content)
            cls._queries[ext] = query
            logger.debug(f"get_query: Query loaded successfully for ext {ext}")
            return query
        except (FileNotFoundError, ModuleNotFoundError) as e:
            logger.warning(f"get_query: tags.scm not found for {lang_name} in package {resource_package}: {e}")
            return None
        except Exception as e:
            logger.error(f"get_query: Query compile error for ext {ext}: {e}")
            logger.error(traceback.format_exc())  # Log stack trace
            return None

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

            matches = query.matches(root)
            logger.debug(f"[EXTRACT] Found {len(matches)} matches.")

            # matches is List[Tuple[int, Dict[str, Node]]]
            # Each tuple is (pattern_index, {capture_name: Node})
            for pattern_index, captures in matches:
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
                    symbol_type = fallback_label.lstrip("definition.").lstrip("@")

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
        return symbols
