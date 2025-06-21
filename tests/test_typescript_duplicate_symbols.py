from kit.tree_sitter_symbol_extractor import TreeSitterSymbolExtractor


def test_typescript_duplicate_symbols():
    """Ensure that exported TypeScript constructs are not duplicated in symbol extraction."""
    code = """
export class MyClass {
  public value: number;

  constructor(value: number) {
    this.value = value;
  }
}

export interface MyInterface {
  id: string;
  name: string;
}
        """

    symbols = TreeSitterSymbolExtractor.extract_symbols(".ts", code)

    # Build a uniqueness key identical to the deduplication logic
    def _key(sym: dict[str, object]):
        return (sym.get("name"), sym.get("type"), sym.get("start_line"), sym.get("end_line"))

    keys = [_key(s) for s in symbols]

    # Assert no duplicates
    assert len(keys) == len(set(keys)), "Duplicate symbols should have been removed by extractor-dedup logic"

    # Ensure the key symbols are present; we may also have methods etc.
    names = {s["name"] for s in symbols}
    assert {"MyClass", "MyInterface"}.issubset(names)
