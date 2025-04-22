import os
import logging
from pathlib import Path
from typing import List, Dict, Optional, Any, ClassVar
from tree_sitter_language_pack import get_parser, get_language

# Set up module-level logger
logger = logging.getLogger(__name__)

# Map file extensions to tree-sitter-languages names
LANGUAGES: dict[str, dict[str, str]] = {
    ".py": {"ts_name": "python", "query_dir": "python"},
    ".js": {"ts_name": "javascript", "query_dir": "javascript"},
    ".go": {"ts_name": "go", "query_dir": "go"},
    ".rs": {"ts_name": "rust", "query_dir": "rust"},
    ".hcl": {"ts_name": "hcl", "query_dir": "hcl"},
    ".tf": {"ts_name": "hcl", "query_dir": "hcl"},
    ".ts": {"ts_name": "typescript", "query_dir": "typescript"},
    ".tsx": {"ts_name": "tsx", "query_dir": "typescript"},
    ".c": {"ts_name": "c", "query_dir": "c"},
}

# Always use absolute path for queries root (one level higher)
QUERIES_ROOT: str = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../queries"))

class TreeSitterSymbolExtractor:
    """
    Multi-language symbol extractor using tree-sitter queries (tags.scm).
    Register new languages by adding to LANGUAGES and providing a tags.scm.
    """
    LANGUAGES = set(LANGUAGES.keys())
    _parsers: ClassVar[dict[str, Any]] = {}
    _languages: ClassVar[dict[str, Any]] = {}
    _queries: ClassVar[dict[str, Any]] = {}

    @classmethod
    def get_parser(cls, ext: str) -> Optional[Any]:
        if ext not in LANGUAGES:
            return None
        if ext not in cls._parsers:
            ts_name = LANGUAGES[ext]["ts_name"]
            parser = get_parser(ts_name)  # type: ignore[arg-type]
            lang = get_language(ts_name)  # type: ignore[arg-type]
            cls._parsers[ext] = parser
            cls._languages[ext] = lang
        return cls._parsers[ext]

    @classmethod
    def get_query(cls, ext: str) -> Optional[Any]:
        logger.debug(f"get_query: ext={ext}")
        if ext not in LANGUAGES:
            logger.debug(f"get_query: ext {ext} not in LANGUAGES")
            return None
        if ext in cls._queries:
            logger.debug(f"get_query: query cached for ext {ext}")
            return cls._queries[ext]
        lang = cls._languages.get(ext)
        logger.debug(f"get_query: lang={lang}")
        if not lang:
            logger.debug(f"get_query: lang not found for ext {ext}")
            return None
        query_dir: str = LANGUAGES[ext]["query_dir"]
        tags_path: str = os.path.join(QUERIES_ROOT, query_dir, "tags.scm")
        logger.debug(f"get_query: tags_path={tags_path} exists={os.path.exists(tags_path)}")
        if not os.path.exists(tags_path):
            logger.debug(f"get_query: tags_path does not exist for ext {ext}")
            return None
        from tree_sitter import Query
        with open(tags_path, "r") as f:
            query_text: str = f.read()
        try:
            query: Any = Query(lang, query_text)
        except Exception as e:
            logger.error(f"get_query: Query compile error for ext {ext}: {e}")
            return None
        cls._queries[ext] = query
        logger.debug(f"get_query: Query loaded successfully for ext {ext}")
        return query

    @classmethod
    def extract_symbols(cls, ext: str, code: str) -> List[Dict[str, Any]]:
        parser = cls.get_parser(ext)
        if not parser:
            return []
        tree = parser.parse(bytes(code, "utf8"))
        root = tree.root_node
        lang = cls._languages.get(ext)
        query = cls.get_query(ext)
        symbols: List[Dict[str, Any]] = []
        if query:
            logger.debug(f"[DEBUG] ext: {ext}")
            logger.debug(f"[DEBUG] Query loaded: {bool(query)}")
            try:
                captures_result = query.captures(root)
                logger.debug(f"[DEBUG] captures_result type: {type(captures_result)}")
                logger.debug(f"[DEBUG] captures_result repr: {repr(captures_result)}")
                # tree-sitter-language-pack returns a dict: {capture_name: [nodes]}
                if not isinstance(captures_result, dict):
                    logger.warning("extract_symbols: Unexpected captures_result type, expected dict!")
                    return []
                block_nodes = captures_result.get("definition.block", [])
                type_nodes = set(captures_result.get("type", []))
                name_nodes = set(captures_result.get("name", []))
                logger.debug(f"[DEBUG] Found {len(block_nodes)} block nodes")

                def descendants(node):
                    cursor = node.walk()
                    reached_root = False
                    while not reached_root:
                        if cursor.goto_first_child():
                            continue
                        if cursor.goto_next_sibling():
                            continue
                        # Go up until we can go to a next sibling, or hit root
                        while True:
                            if not cursor.goto_parent():
                                reached_root = True
                                break
                            if cursor.goto_next_sibling():
                                break
                        if not reached_root:
                            continue
                        break
                    # Collect all descendants
                    nodes = []
                    def collect(n):
                        for i in range(n.child_count):
                            c = n.children[i]
                            nodes.append(c)
                            collect(c)
                    collect(node)
                    return nodes

                for block in block_nodes:
                    # Find type and name among block's children
                    btype = None
                    bname = None
                    for child in getattr(block, 'children', []):
                        if child in type_nodes:
                            btype = child.text.decode()
                        if child in name_nodes:
                            bname = child.text.decode().strip('"')
                    # Fallback: look for type/name among descendants
                    if not btype or not bname:
                        for descendant in descendants(block):
                            if not btype and descendant in type_nodes:
                                btype = descendant.text.decode()
                            if not bname and descendant in name_nodes:
                                bname = descendant.text.decode().strip('"')
                    symbol = {"type": btype or "block"}
                    if bname:
                        symbol["name"] = bname
                    symbols.append(symbol)
                logger.debug(f"[DEBUG] Extracted symbols: {symbols}")
            except Exception as e:
                logger.error(f"[DEBUG] Query error: {e}")
                return []
        # fallback: hardcoded (for .py, etc)
        def walk(node: Any) -> None:
            # Python
            if ext == ".py":
                if node.type == "function_definition":
                    ident = node.child_by_field_name("name")
                    if ident:
                        symbols.append({
                            "name": ident.text.decode(),
                            "type": "function",
                            "code": node.text.decode() if hasattr(node, 'text') else None
                        })
                elif node.type == "class_definition":
                    ident = node.child_by_field_name("name")
                    if ident:
                        symbols.append({
                            "name": ident.text.decode(),
                            "type": "class",
                            "code": node.text.decode() if hasattr(node, 'text') else None
                        })
            # JS
            elif ext == ".js":
                if node.type == "function_declaration":
                    ident = node.child_by_field_name("name")
                    if ident:
                        symbols.append({
                            "name": ident.text.decode(),
                            "type": "function",
                            "code": node.text.decode() if hasattr(node, 'text') else None
                        })
                elif node.type == "class_declaration":
                    ident = node.child_by_field_name("name")
                    if ident:
                        symbols.append({
                            "name": ident.text.decode(),
                            "type": "class",
                            "code": node.text.decode() if hasattr(node, 'text') else None
                        })
            # Go
            elif ext == ".go":
                if node.type == "function_declaration":
                    ident = node.child_by_field_name("name")
                    if ident:
                        symbols.append({
                            "name": ident.text.decode(),
                            "type": "function",
                            "code": node.text.decode() if hasattr(node, 'text') else None
                        })
                elif node.type == "type_declaration":
                    ident = node.child_by_field_name("name")
                    if ident:
                        symbols.append({
                            "name": ident.text.decode(),
                            "type": "type",
                            "code": node.text.decode() if hasattr(node, 'text') else None
                        })
            # Rust
            elif ext == ".rs":
                if node.type == "function_item":
                    ident = node.child_by_field_name("name")
                    if ident:
                        symbols.append({
                            "name": ident.text.decode(),
                            "type": "function",
                            "code": node.text.decode() if hasattr(node, 'text') else None
                        })
                elif node.type == "struct_item":
                    ident = node.child_by_field_name("name")
                    if ident:
                        symbols.append({
                            "name": ident.text.decode(),
                            "type": "struct",
                            "code": node.text.decode() if hasattr(node, 'text') else None
                        })
            # HCL (Terraform)
            elif ext in {".hcl", ".tf"}:
                if node.type == "block":
                    label = node.child_by_field_name("label")
                    # Try both field name 'type' and fallback to first child
                    type_node = node.child_by_field_name("type")
                    if not type_node and len(node.children) > 0:
                        type_node = node.children[0]
                    block_type = type_node.text.decode() if type_node else "block"
                    if label:
                        symbols.append({
                            "name": label.text.decode(),
                            "type": block_type,
                            "code": node.text.decode() if hasattr(node, 'text') else None
                        })
            # TypeScript
            elif ext in {".ts", ".tsx"}:
                if node.type == "function_declaration":
                    ident = node.child_by_field_name("name")
                    if ident:
                        symbols.append({
                            "name": ident.text.decode(),
                            "type": "function",
                            "code": node.text.decode() if hasattr(node, 'text') else None
                        })
                elif node.type == "class_declaration":
                    ident = node.child_by_field_name("name")
                    if ident:
                        symbols.append({
                            "name": ident.text.decode(),
                            "type": "class",
                            "code": node.text.decode() if hasattr(node, 'text') else None
                        })
                elif node.type == "interface_declaration":
                    ident = node.child_by_field_name("name")
                    if ident:
                        symbols.append({
                            "name": ident.text.decode(),
                            "type": "interface",
                            "code": node.text.decode() if hasattr(node, 'text') else None
                        })
                elif node.type == "enum_declaration":
                    ident = node.child_by_field_name("name")
                    if ident:
                        symbols.append({
                            "name": ident.text.decode(),
                            "type": "enum",
                            "code": node.text.decode() if hasattr(node, 'text') else None
                        })
            # C
            elif ext == ".c":
                if node.type == "function_definition":
                    ident = node.child_by_field_name("declarator")
                    if ident:
                        symbols.append({
                            "name": ident.text.decode(),
                            "type": "function",
                            "code": node.text.decode() if hasattr(node, 'text') else None
                        })
            for child in node.children:
                walk(child)
        walk(root)
        return symbols
