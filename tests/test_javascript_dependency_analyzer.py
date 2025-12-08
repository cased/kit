import json
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from kit import Repository


def test_javascript_dependency_analyzer_esm_basic():
    """Test basic ESM import functionality."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create package.json
        with open(f"{tmpdir}/package.json", "w") as f:
            json.dump({"name": "my-app", "version": "1.0.0"}, f)

        # Create main.js with ESM imports
        with open(f"{tmpdir}/main.js", "w") as f:
            f.write("""import express from 'express';
import { helper } from './utils/helper.js';

const app = express();
helper();
""")

        # Create utils/helper.js
        os.makedirs(f"{tmpdir}/utils")
        with open(f"{tmpdir}/utils/helper.js", "w") as f:
            f.write("""import lodash from 'lodash';

export function helper() {
    return lodash.noop();
}
""")

        repo = Repository(tmpdir)
        analyzer = repo.get_dependency_analyzer("javascript")

        graph = analyzer.build_dependency_graph()

        # Check internal files are found
        assert "main.js" in graph
        assert "utils/helper.js" in graph

        # Check external packages are found
        assert "express" in graph
        assert "lodash" in graph

        # Check dependencies
        main_deps = graph["main.js"]["dependencies"]
        assert "express" in main_deps


def test_javascript_dependency_analyzer_cjs_require():
    """Test CommonJS require() imports."""
    with tempfile.TemporaryDirectory() as tmpdir:
        with open(f"{tmpdir}/package.json", "w") as f:
            json.dump({"name": "cjs-app"}, f)

        with open(f"{tmpdir}/index.js", "w") as f:
            f.write("""const express = require('express');
const path = require('path');
const { utils } = require('./lib/utils');

module.exports = { app: express() };
""")

        os.makedirs(f"{tmpdir}/lib")
        with open(f"{tmpdir}/lib/utils.js", "w") as f:
            f.write("""const fs = require('fs');

module.exports.utils = {
    read: fs.readFileSync
};
""")

        repo = Repository(tmpdir)
        analyzer = repo.get_dependency_analyzer("javascript")

        graph = analyzer.build_dependency_graph()

        # Check CJS imports are detected
        assert "express" in graph
        assert "path" in graph
        assert "fs" in graph

        # Check node builtins are classified correctly
        assert graph["path"]["type"] == "node_builtin"
        assert graph["fs"]["type"] == "node_builtin"


def test_javascript_dependency_analyzer_typescript():
    """Test TypeScript file analysis."""
    with tempfile.TemporaryDirectory() as tmpdir:
        with open(f"{tmpdir}/package.json", "w") as f:
            json.dump({"name": "ts-app"}, f)

        with open(f"{tmpdir}/main.ts", "w") as f:
            f.write("""import express, { Request, Response } from 'express';
import { UserService } from './services/user';

const app = express();

app.get('/', (req: Request, res: Response) => {
    const service = new UserService();
});
""")

        os.makedirs(f"{tmpdir}/services")
        with open(f"{tmpdir}/services/user.ts", "w") as f:
            f.write("""import { Database } from './database';

export class UserService {
    private db = new Database();
}
""")

        with open(f"{tmpdir}/services/database.ts", "w") as f:
            f.write("""export class Database {
    connect() {}
}
""")

        repo = Repository(tmpdir)
        analyzer = repo.get_dependency_analyzer("typescript")

        graph = analyzer.build_dependency_graph()

        # Check TypeScript files are found
        assert "main.ts" in graph
        assert "services/user.ts" in graph
        assert "services/database.ts" in graph


def test_javascript_dependency_analyzer_import_types():
    """Test classification of imports as internal, node_builtin, or external."""
    with tempfile.TemporaryDirectory() as tmpdir:
        with open(f"{tmpdir}/package.json", "w") as f:
            json.dump({"name": "types-test", "dependencies": {"axios": "^1.0.0"}}, f)

        with open(f"{tmpdir}/main.js", "w") as f:
            f.write("""import axios from 'axios';
import fs from 'fs';
import path from 'node:path';
import { helper } from './helper.js';

axios.get('/api');
""")

        with open(f"{tmpdir}/helper.js", "w") as f:
            f.write("""export function helper() {}
""")

        repo = Repository(tmpdir)
        analyzer = repo.get_dependency_analyzer("javascript")

        graph = analyzer.build_dependency_graph()

        # Check type classifications
        assert graph["axios"]["type"] == "external"
        assert graph["fs"]["type"] == "node_builtin"
        assert graph["path"]["type"] == "node_builtin"
        assert graph["main.js"]["type"] == "internal"
        assert graph["helper.js"]["type"] == "internal"


def test_javascript_dependency_analyzer_scoped_packages():
    """Test handling of scoped packages (@org/pkg)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        with open(f"{tmpdir}/package.json", "w") as f:
            json.dump(
                {
                    "name": "scoped-test",
                    "dependencies": {"@types/node": "^18.0.0", "@babel/core": "^7.0.0"},
                },
                f,
            )

        with open(f"{tmpdir}/index.js", "w") as f:
            f.write("""import { transform } from '@babel/core';
import parser from '@babel/parser';
import * as t from '@babel/types';

transform(code);
""")

        repo = Repository(tmpdir)
        analyzer = repo.get_dependency_analyzer("javascript")

        graph = analyzer.build_dependency_graph()

        # Scoped packages should be detected
        assert "@babel/core" in graph
        assert "@babel/parser" in graph
        assert "@babel/types" in graph

        # All scoped packages are external
        assert graph["@babel/core"]["type"] == "external"


def test_javascript_dependency_analyzer_cycles():
    """Test cycle detection in JavaScript modules."""
    with tempfile.TemporaryDirectory() as tmpdir:
        with open(f"{tmpdir}/package.json", "w") as f:
            json.dump({"name": "cycle-test"}, f)

        with open(f"{tmpdir}/a.js", "w") as f:
            f.write("""import { b } from './b.js';
export const a = () => b();
""")

        with open(f"{tmpdir}/b.js", "w") as f:
            f.write("""import { c } from './c.js';
export const b = () => c();
""")

        with open(f"{tmpdir}/c.js", "w") as f:
            f.write("""import { a } from './a.js';
export const c = () => a();
""")

        repo = Repository(tmpdir)
        analyzer = repo.get_dependency_analyzer("javascript")

        analyzer.build_dependency_graph()
        cycles = analyzer.find_cycles()

        assert len(cycles) > 0

        # Check that we found the cycle
        found_cycle = False
        for cycle in cycles:
            file_names = [os.path.basename(p) for p in cycle]
            if "a.js" in file_names and "b.js" in file_names and "c.js" in file_names:
                found_cycle = True
                break

        assert found_cycle, "Expected cycle between a.js, b.js, and c.js was not found"


def test_javascript_dependency_analyzer_export_json():
    """Test JSON export of dependency graph."""
    with tempfile.TemporaryDirectory() as tmpdir:
        with open(f"{tmpdir}/package.json", "w") as f:
            json.dump({"name": "export-test"}, f)

        with open(f"{tmpdir}/index.js", "w") as f:
            f.write("""import express from 'express';
const app = express();
""")

        repo = Repository(tmpdir)
        analyzer = repo.get_dependency_analyzer("javascript")

        result = analyzer.export_dependency_graph(output_format="json")

        assert isinstance(result, dict)
        assert "index.js" in result
        assert "express" in result
        assert isinstance(result["index.js"]["dependencies"], list)


def test_javascript_dependency_analyzer_export_dot():
    """Test DOT format export."""
    with tempfile.TemporaryDirectory() as tmpdir:
        with open(f"{tmpdir}/package.json", "w") as f:
            json.dump({"name": "dot-test"}, f)

        with open(f"{tmpdir}/index.js", "w") as f:
            f.write("""import './helper.js';
""")

        with open(f"{tmpdir}/helper.js", "w") as f:
            f.write("""export default {};
""")

        repo = Repository(tmpdir)
        analyzer = repo.get_dependency_analyzer("javascript")

        result = analyzer.export_dependency_graph(output_format="dot")

        assert isinstance(result, str)
        assert "digraph G" in result


def test_javascript_dependency_analyzer_mixed_imports():
    """Test file with mixed ESM and CJS imports."""
    with tempfile.TemporaryDirectory() as tmpdir:
        with open(f"{tmpdir}/package.json", "w") as f:
            json.dump({"name": "mixed-test"}, f)

        with open(f"{tmpdir}/index.js", "w") as f:
            f.write("""import express from 'express';
const lodash = require('lodash');
import('./dynamic.js').then(mod => mod.default());

const app = express();
lodash.noop();
""")

        with open(f"{tmpdir}/dynamic.js", "w") as f:
            f.write("""export default function() {}
""")

        repo = Repository(tmpdir)
        analyzer = repo.get_dependency_analyzer("javascript")

        graph = analyzer.build_dependency_graph()

        # All import types should be detected
        assert "express" in graph
        assert "lodash" in graph

        index_deps = graph["index.js"]["dependencies"]
        assert "express" in index_deps
        assert "lodash" in index_deps


def test_javascript_dependency_analyzer_get_dependents():
    """Test getting modules that depend on a given module."""
    with tempfile.TemporaryDirectory() as tmpdir:
        with open(f"{tmpdir}/package.json", "w") as f:
            json.dump({"name": "dependents-test"}, f)

        with open(f"{tmpdir}/shared.js", "w") as f:
            f.write("""export const shared = {};
""")

        with open(f"{tmpdir}/a.js", "w") as f:
            f.write("""import { shared } from './shared.js';
export const a = shared;
""")

        with open(f"{tmpdir}/b.js", "w") as f:
            f.write("""import { shared } from './shared.js';
export const b = shared;
""")

        repo = Repository(tmpdir)
        analyzer = repo.get_dependency_analyzer("javascript")

        analyzer.build_dependency_graph()
        dependents = analyzer.get_dependents("shared.js")

        assert "a.js" in dependents
        assert "b.js" in dependents


def test_javascript_dependency_analyzer_llm_context():
    """Test LLM context generation."""
    with tempfile.TemporaryDirectory() as tmpdir:
        with open(f"{tmpdir}/package.json", "w") as f:
            json.dump({"name": "context-test", "dependencies": {"react": "^18.0.0"}}, f)

        with open(f"{tmpdir}/App.js", "w") as f:
            f.write("""import React from 'react';
import { Component } from './Component.js';

export function App() {
    return <Component />;
}
""")

        with open(f"{tmpdir}/Component.js", "w") as f:
            f.write("""import React from 'react';

export function Component() {
    return <div>Hello</div>;
}
""")

        repo = Repository(tmpdir)
        analyzer = repo.get_dependency_analyzer("javascript")

        context = analyzer.generate_llm_context(output_format="markdown")

        assert "# Dependency Analysis Summary" in context
        assert "JavaScript/TypeScript-Specific Insights" in context


def test_javascript_dependency_analyzer_factory():
    """Test that the factory method correctly returns JavaScriptDependencyAnalyzer."""
    with tempfile.TemporaryDirectory() as tmpdir:
        with open(f"{tmpdir}/package.json", "w") as f:
            json.dump({"name": "factory-test"}, f)
        with open(f"{tmpdir}/index.js", "w") as f:
            f.write("export default {};")

        repo = Repository(tmpdir)

        # Test all aliases work
        from kit.dependency_analyzer.javascript_dependency_analyzer import JavaScriptDependencyAnalyzer

        for lang in ["javascript", "typescript", "js", "ts"]:
            analyzer = repo.get_dependency_analyzer(lang)
            assert isinstance(analyzer, JavaScriptDependencyAnalyzer)


def test_javascript_dependency_analyzer_no_package_json():
    """Test analyzer behavior when package.json is missing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        with open(f"{tmpdir}/index.js", "w") as f:
            f.write("""import express from 'express';
""")

        repo = Repository(tmpdir)
        analyzer = repo.get_dependency_analyzer("javascript")

        # Should not raise, just work without package name
        graph = analyzer.build_dependency_graph()

        assert "index.js" in graph
        assert "express" in graph


def test_javascript_dependency_analyzer_export_from():
    """Test re-export statements."""
    with tempfile.TemporaryDirectory() as tmpdir:
        with open(f"{tmpdir}/package.json", "w") as f:
            json.dump({"name": "reexport-test"}, f)

        with open(f"{tmpdir}/index.js", "w") as f:
            f.write("""export { foo } from './foo.js';
export * from './bar.js';
""")

        with open(f"{tmpdir}/foo.js", "w") as f:
            f.write("""export const foo = 'foo';
""")

        with open(f"{tmpdir}/bar.js", "w") as f:
            f.write("""export const bar = 'bar';
""")

        repo = Repository(tmpdir)
        analyzer = repo.get_dependency_analyzer("javascript")

        graph = analyzer.build_dependency_graph()

        # Re-exports should be detected as dependencies
        index_deps = graph["index.js"]["dependencies"]
        # Check that foo.js and bar.js paths are in dependencies
        assert any("foo" in dep for dep in index_deps)
        assert any("bar" in dep for dep in index_deps)


def test_javascript_dependency_analyzer_jsx_tsx():
    """Test JSX and TSX file handling."""
    with tempfile.TemporaryDirectory() as tmpdir:
        with open(f"{tmpdir}/package.json", "w") as f:
            json.dump({"name": "jsx-test"}, f)

        with open(f"{tmpdir}/App.jsx", "w") as f:
            f.write("""import React from 'react';
import { Header } from './Header.tsx';

export function App() {
    return <Header title="Hello" />;
}
""")

        with open(f"{tmpdir}/Header.tsx", "w") as f:
            f.write("""import React from 'react';

interface Props {
    title: string;
}

export function Header({ title }: Props) {
    return <h1>{title}</h1>;
}
""")

        repo = Repository(tmpdir)
        analyzer = repo.get_dependency_analyzer("javascript")

        graph = analyzer.build_dependency_graph()

        assert "App.jsx" in graph
        assert "Header.tsx" in graph


def test_javascript_dependency_analyzer_node_modules_excluded():
    """Test that node_modules directory is excluded."""
    with tempfile.TemporaryDirectory() as tmpdir:
        with open(f"{tmpdir}/package.json", "w") as f:
            json.dump({"name": "exclude-test"}, f)

        with open(f"{tmpdir}/index.js", "w") as f:
            f.write("""import express from 'express';
""")

        # Create a fake node_modules with express
        os.makedirs(f"{tmpdir}/node_modules/express")
        with open(f"{tmpdir}/node_modules/express/index.js", "w") as f:
            f.write("""module.exports = function() {};
""")

        repo = Repository(tmpdir)
        analyzer = repo.get_dependency_analyzer("javascript")

        graph = analyzer.build_dependency_graph()

        # node_modules files should not be in the graph as internal modules
        internal_files = [m for m, d in graph.items() if d["type"] == "internal"]
        assert not any("node_modules" in f for f in internal_files)


def test_javascript_dependency_analyzer_index_resolution():
    """Test that directory imports resolve to index files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        with open(f"{tmpdir}/package.json", "w") as f:
            json.dump({"name": "index-test"}, f)

        with open(f"{tmpdir}/main.js", "w") as f:
            f.write("""import { utils } from './lib';
""")

        os.makedirs(f"{tmpdir}/lib")
        with open(f"{tmpdir}/lib/index.js", "w") as f:
            f.write("""export const utils = {};
""")

        repo = Repository(tmpdir)
        analyzer = repo.get_dependency_analyzer("javascript")

        graph = analyzer.build_dependency_graph()

        # The index file should be in the graph
        assert "lib/index.js" in graph


def test_javascript_dependency_analyzer_get_dependencies_generic():
    """Test the generic get_dependencies method."""
    with tempfile.TemporaryDirectory() as tmpdir:
        with open(f"{tmpdir}/package.json", "w") as f:
            json.dump({"name": "generic-test"}, f)

        with open(f"{tmpdir}/main.js", "w") as f:
            f.write("""import { helper } from './helper.js';
import express from 'express';
""")

        with open(f"{tmpdir}/helper.js", "w") as f:
            f.write("""export function helper() {}
""")

        repo = Repository(tmpdir)
        analyzer = repo.get_dependency_analyzer("javascript")

        analyzer.build_dependency_graph()

        # Test generic get_dependencies method
        deps = analyzer.get_dependencies("main.js")
        assert "express" in deps or "helper.js" in deps

        # Should be same as get_module_dependencies
        module_deps = analyzer.get_module_dependencies("main.js")
        assert deps == module_deps


def test_javascript_dependency_analyzer_dependency_report():
    """Test dependency report generation."""
    with tempfile.TemporaryDirectory() as tmpdir:
        with open(f"{tmpdir}/package.json", "w") as f:
            json.dump(
                {"name": "report-test", "dependencies": {"express": "^4.0.0", "lodash": "^4.0.0"}},
                f,
            )

        with open(f"{tmpdir}/index.js", "w") as f:
            f.write("""import express from 'express';
import lodash from 'lodash';
import fs from 'fs';
""")

        repo = Repository(tmpdir)
        analyzer = repo.get_dependency_analyzer("javascript")

        report = analyzer.generate_dependency_report()

        assert "summary" in report
        assert report["summary"]["package_name"] == "report-test"
        assert "external_dependencies" in report
        assert "node_builtins_used" in report
        assert "fs" in report["node_builtins_used"]
