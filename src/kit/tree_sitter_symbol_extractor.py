import os
import logging
import traceback
from pathlib import Path
from typing import List, Dict, Optional, Any, ClassVar
from tree_sitter_language_pack import get_parser, get_language

# Set up module-level logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG) # Force debug level for this logger

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
    _queries: ClassVar[dict[str, Any]] = {}

    @classmethod
    def get_parser(cls, ext: str) -> Optional[Any]:
        if ext not in LANGUAGES:
            return None
        if ext not in cls._parsers:
            lang_name = LANGUAGES[ext]
            parser = get_parser(lang_name)
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
        query_dir: str = lang_name 
        tags_path: str = os.path.join(QUERIES_ROOT, query_dir, "tags.scm")
        logger.debug(f"get_query: tags_path={tags_path} exists={os.path.exists(tags_path)}")
        if not os.path.exists(tags_path):
            logger.warning(f"get_query: tags.scm not found at {tags_path}")
            return None
        try:
            language = get_language(lang_name)
            with open(tags_path, 'r') as f:
                tags_content = f.read()
            query = language.query(tags_content)
            cls._queries[ext] = query
            logger.debug(f"get_query: Query loaded successfully for ext {ext}")
            return query
        except Exception as e:
            logger.error(f"get_query: Query compile error for ext {ext}: {e}")
            logger.error(traceback.format_exc()) # Log stack trace
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
            for pattern_index, captures_dict in matches:
                logger.debug(f"[MATCH pattern={pattern_index}] Processing match with captures: {list(captures_dict.keys())}")

                # Keys in captures_dict do NOT have the leading '@'
                name_node = captures_dict.get("name")
                definition_capture = next(((name, node) for name, node in captures_dict.items() if name.startswith("definition.")), None)
                type_node = captures_dict.get("type") # Get type node as potential fallback

                node_to_use_for_name = None
                symbol_name_source = None # Track if name came from 'name' or 'type'

                # Prioritize @name, fallback to @type if @name missing but @definition present
                if name_node:
                    node_to_use_for_name = name_node
                    symbol_name_source = 'name'
                elif type_node and definition_capture: # Fallback for blocks like locals/terraform
                    node_to_use_for_name = type_node
                    symbol_name_source = 'type'

                # Proceed if we have a definition and a node to derive the name from
                if node_to_use_for_name and definition_capture:
                    definition_capture_name, definition_node = definition_capture
                    symbol_type = definition_capture_name.split('.')[-1]
                    
                    # Handle potential list returns for captures
                    actual_name_node = node_to_use_for_name
                    if isinstance(node_to_use_for_name, list):
                        if node_to_use_for_name: # Check if list is not empty
                            actual_name_node = node_to_use_for_name[0]
                            logger.warning(f"[PROCESS]   Capture '{symbol_name_source}' returned a list for match {pattern_index}, using first node: {actual_name_node}. Captures: {list(captures_dict.keys())}")
                        else:
                             logger.warning(f"[PROCESS]   Capture '{symbol_name_source}' returned an empty list for match {pattern_index}. Skipping.")
                             continue # Skip this match if list is empty

                    # Ensure the node we are using is valid before accessing attributes
                    if not actual_name_node or not hasattr(actual_name_node, 'text') or not hasattr(actual_name_node, 'start_point'):
                        logger.warning(f"[PROCESS]   Invalid or incomplete node for '{symbol_name_source}' capture in match {pattern_index}: {actual_name_node}. Skipping.")
                        continue

                    try:
                        symbol_name = actual_name_node.text.decode('utf-8')
                        
                        # HCL Specific: Strip quotes from string literals
                        if (ext == '.tf') and hasattr(actual_name_node, 'type') and actual_name_node.type == 'string_lit': # Check node's type attribute
                            if len(symbol_name) >= 2 and symbol_name.startswith('"') and symbol_name.endswith('"'):
                                symbol_name = symbol_name[1:-1]
                        
                        # HCL Specific: Combine type and name for resource/data blocks
                        if (ext == '.tf') and symbol_type in ["resource", "data"] and symbol_name_source == 'name' and type_node:
                            if type_node:
                                actual_type_node = type_node
                                if isinstance(type_node, list):
                                    if type_node:
                                        actual_type_node = type_node[0]
                                    else:
                                        actual_type_node = None # Type capture was empty list
                                
                                if actual_type_node and hasattr(actual_type_node, 'text'):
                                    try:
                                        type_name = actual_type_node.text.decode('utf-8')
                                        # Strip quotes from type name too
                                        if hasattr(actual_type_node, 'type') and actual_type_node.type == 'string_lit':
                                            if len(type_name) >= 2 and type_name.startswith('"') and type_name.endswith('"'):
                                                type_name = type_name[1:-1]
                                        symbol_name = f"{type_name}.{symbol_name}"
                                    except UnicodeDecodeError:
                                        logger.warning(f"[PROCESS HCL TypeCombine] Could not decode HCL type name from bytes: {actual_type_node.text}")
                                    except AttributeError:
                                         logger.warning(f"[PROCESS HCL TypeCombine] Invalid node for HCL 'type' capture: {actual_type_node}")
                                else:
                                    logger.warning(f"[PROCESS HCL TypeCombine] Invalid or missing node for HCL 'type' capture: {type_node}")
                            else:
                                 logger.warning(f"[PROCESS HCL TypeCombine] Missing 'type' capture for HCL {symbol_type} symbol '{symbol_name}' (Needed for resource/data name combination)")
                        
                        logger.info(f"[PROCESS]   Extracted: Name='{symbol_name}', Type='{symbol_type}', Line: {actual_name_node.start_point[0]}") # Use info level for successful extraction
                        symbols.append({
                            "name": symbol_name,
                            "type": symbol_type,
                            # Use the name node's position for now
                            "start_line": actual_name_node.start_point[0],
                            "end_line": actual_name_node.end_point[0],
                        })
                    except UnicodeDecodeError:
                        logger.warning(f"[PROCESS]   Skipping match {pattern_index}: Could not decode symbol name from bytes: {actual_name_node.text}")
                    except AttributeError as ae:
                        logger.error(f"[PROCESS]   AttributeError processing node {actual_name_node} (type: {type(actual_name_node)}) in match {pattern_index}: {ae}")
                        logger.error(traceback.format_exc())
                    except Exception as inner_e:
                        logger.error(f"[PROCESS]   Error processing match {pattern_index}: {inner_e}")
                        logger.error(traceback.format_exc())
                else:
                    # Log reason for skipping
                    if not definition_capture:
                        logger.debug(f"[PROCESS]   Skipping match {pattern_index}: Missing 'definition.*' capture. Found: {list(captures_dict.keys())}")
                    elif not node_to_use_for_name: # Means neither @name nor @type (with @def) was found
                         logger.debug(f"[PROCESS]   Skipping match {pattern_index}: Missing suitable 'name' or 'type' capture. Found: {list(captures_dict.keys())}")

        except Exception as e:
            logger.error(f"[EXTRACT] Error parsing or processing file with ext {ext}: {e}")
            logger.error(traceback.format_exc())
            return [] # Return empty list on error

        logger.debug(f"[EXTRACT] Finished extraction for ext {ext}. Found {len(symbols)} symbols.")
        return symbols
