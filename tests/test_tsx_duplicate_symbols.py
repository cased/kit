from kit.tree_sitter_symbol_extractor import TreeSitterSymbolExtractor


def test_tsx_duplicate_symbols():
    """Ensure TSX (using TypeScript fallback queries) does not return duplicate symbols."""
    code = """
import React from 'react';

export interface Props {
  title: string;
}

export class Header extends React.Component<Props> {
  render() {
    return <h1>{this.props.title}</h1>;
  }
}
        """

    symbols = TreeSitterSymbolExtractor.extract_symbols(".tsx", code)

    def _key(sym: dict[str, object]):
        return (sym.get("name"), sym.get("type"), sym.get("start_line"), sym.get("end_line"))

    keys = [_key(s) for s in symbols]
    assert len(keys) == len(set(keys)), "Duplicate symbols detected for TSX"

    # Ensure interface and class present (methods may also be captured)
    names = {s["name"] for s in symbols}
    assert {"Props", "Header"}.issubset(names)

    # Expect interface + class + method (render)
    names = {s["name"] for s in symbols}
    assert "Props" in names
    assert "Header" in names
