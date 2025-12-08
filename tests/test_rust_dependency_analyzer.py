import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from kit import Repository


def test_rust_dependency_analyzer_basic():
    """Test basic Rust crate analysis."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create Cargo.toml
        with open(f"{tmpdir}/Cargo.toml", "w") as f:
            f.write("""[package]
name = "my_crate"
version = "0.1.0"
edition = "2021"

[dependencies]
serde = "1.0"
tokio = "1.0"
""")

        # Create src/lib.rs
        os.makedirs(f"{tmpdir}/src")
        with open(f"{tmpdir}/src/lib.rs", "w") as f:
            f.write("""use serde::Serialize;
use std::collections::HashMap;

mod utils;

pub fn process() -> HashMap<String, String> {
    HashMap::new()
}
""")

        # Create src/utils.rs
        with open(f"{tmpdir}/src/utils.rs", "w") as f:
            f.write("""use tokio::runtime::Runtime;

pub fn get_runtime() -> Runtime {
    Runtime::new().unwrap()
}
""")

        repo = Repository(tmpdir)
        analyzer = repo.get_dependency_analyzer("rust")

        graph = analyzer.build_dependency_graph()

        # Check internal files are found
        assert "src/lib.rs" in graph
        assert "src/utils.rs" in graph

        # Check external crates are found
        assert "serde" in graph
        assert "tokio" in graph

        # Check std library is found
        assert "std" in graph


def test_rust_dependency_analyzer_use_statements():
    """Test extraction of various use statement patterns."""
    with tempfile.TemporaryDirectory() as tmpdir:
        with open(f"{tmpdir}/Cargo.toml", "w") as f:
            f.write("""[package]
name = "use_test"
version = "0.1.0"

[dependencies]
anyhow = "1.0"
""")

        os.makedirs(f"{tmpdir}/src")
        with open(f"{tmpdir}/src/main.rs", "w") as f:
            f.write("""use std::io::{self, Read, Write};
use std::collections::*;
use anyhow::{Result, Context};
use crate::utils::helper;

mod utils;

fn main() -> Result<()> {
    Ok(())
}
""")

        with open(f"{tmpdir}/src/utils.rs", "w") as f:
            f.write("""pub fn helper() {}
""")

        repo = Repository(tmpdir)
        analyzer = repo.get_dependency_analyzer("rust")

        graph = analyzer.build_dependency_graph()

        # Check that use statements are parsed
        main_deps = graph["src/main.rs"]["dependencies"]
        assert "std" in main_deps
        assert "anyhow" in main_deps
        # Check that crate:: paths are resolved to internal modules
        assert "utils" in main_deps


def test_rust_dependency_analyzer_crate_paths():
    """Test that crate::, self::, super:: paths are resolved to internal modules."""
    with tempfile.TemporaryDirectory() as tmpdir:
        with open(f"{tmpdir}/Cargo.toml", "w") as f:
            f.write("""[package]
name = "path_test"
version = "0.1.0"
""")

        os.makedirs(f"{tmpdir}/src/handlers")
        with open(f"{tmpdir}/src/lib.rs", "w") as f:
            f.write("""mod config;
mod handlers;

use crate::config::Settings;
use crate::handlers::api;
""")

        with open(f"{tmpdir}/src/config.rs", "w") as f:
            f.write("""pub struct Settings {}
""")

        with open(f"{tmpdir}/src/handlers/mod.rs", "w") as f:
            f.write("""pub mod api;
pub mod web;

use super::config::Settings;
use self::api::handle;
""")

        with open(f"{tmpdir}/src/handlers/api.rs", "w") as f:
            f.write("""pub fn handle() {}
""")

        with open(f"{tmpdir}/src/handlers/web.rs", "w") as f:
            f.write("""use crate::config::Settings;
pub fn serve() {}
""")

        repo = Repository(tmpdir)
        analyzer = repo.get_dependency_analyzer("rust")

        graph = analyzer.build_dependency_graph()

        # lib.rs should depend on config and handlers via crate::
        lib_deps = graph["src/lib.rs"]["dependencies"]
        assert "config" in lib_deps
        assert "handlers" in lib_deps

        # handlers/mod.rs should depend on config via super:: and api via self::
        handlers_deps = graph["src/handlers/mod.rs"]["dependencies"]
        assert "config" in handlers_deps
        assert "api" in handlers_deps

        # handlers/web.rs should depend on config via crate::
        web_deps = graph["src/handlers/web.rs"]["dependencies"]
        assert "config" in web_deps


def test_rust_dependency_analyzer_mod_declarations():
    """Test mod declaration handling."""
    with tempfile.TemporaryDirectory() as tmpdir:
        with open(f"{tmpdir}/Cargo.toml", "w") as f:
            f.write("""[package]
name = "mod_test"
version = "0.1.0"
""")

        os.makedirs(f"{tmpdir}/src")
        with open(f"{tmpdir}/src/lib.rs", "w") as f:
            f.write("""pub mod config;
pub mod handlers;
mod internal;
""")

        with open(f"{tmpdir}/src/config.rs", "w") as f:
            f.write("""pub struct Config {}
""")

        with open(f"{tmpdir}/src/handlers.rs", "w") as f:
            f.write("""pub fn handle() {}
""")

        with open(f"{tmpdir}/src/internal.rs", "w") as f:
            f.write("""fn internal() {}
""")

        repo = Repository(tmpdir)
        analyzer = repo.get_dependency_analyzer("rust")

        graph = analyzer.build_dependency_graph()

        # All internal modules should be found
        assert "src/lib.rs" in graph
        assert "src/config.rs" in graph
        assert "src/handlers.rs" in graph
        assert "src/internal.rs" in graph


def test_rust_dependency_analyzer_import_types():
    """Test classification of imports as internal, std, or external."""
    with tempfile.TemporaryDirectory() as tmpdir:
        with open(f"{tmpdir}/Cargo.toml", "w") as f:
            f.write("""[package]
name = "types_test"
version = "0.1.0"

[dependencies]
serde = "1.0"

[dev-dependencies]
criterion = "0.4"
""")

        os.makedirs(f"{tmpdir}/src")
        with open(f"{tmpdir}/src/lib.rs", "w") as f:
            f.write("""use std::fmt;
use core::mem;
use alloc::vec::Vec;
use serde::Serialize;
use criterion::black_box;

mod helpers;
""")

        with open(f"{tmpdir}/src/helpers.rs", "w") as f:
            f.write("""pub fn help() {}
""")

        repo = Repository(tmpdir)
        analyzer = repo.get_dependency_analyzer("rust")

        graph = analyzer.build_dependency_graph()

        # Check type classifications
        assert graph["std"]["type"] == "std"
        assert graph["core"]["type"] == "std"
        assert graph["alloc"]["type"] == "std"
        assert graph["serde"]["type"] == "external"
        assert graph["criterion"]["type"] == "external"
        assert graph["src/lib.rs"]["type"] == "internal"


def test_rust_dependency_analyzer_cycles():
    """Test cycle detection in Rust modules."""
    with tempfile.TemporaryDirectory() as tmpdir:
        with open(f"{tmpdir}/Cargo.toml", "w") as f:
            f.write("""[package]
name = "cycle_test"
version = "0.1.0"
""")

        os.makedirs(f"{tmpdir}/src")
        # Note: Rust doesn't typically have module cycles like other languages,
        # but we can simulate dependency relationships through use statements
        with open(f"{tmpdir}/src/lib.rs", "w") as f:
            f.write("""mod a;
mod b;
mod c;
""")

        with open(f"{tmpdir}/src/a.rs", "w") as f:
            f.write("""use crate::b::*;
pub fn a_fn() {}
""")

        with open(f"{tmpdir}/src/b.rs", "w") as f:
            f.write("""use crate::c::*;
pub fn b_fn() {}
""")

        with open(f"{tmpdir}/src/c.rs", "w") as f:
            f.write("""use crate::a::*;
pub fn c_fn() {}
""")

        repo = Repository(tmpdir)
        analyzer = repo.get_dependency_analyzer("rust")

        analyzer.build_dependency_graph()
        cycles = analyzer.find_cycles()

        # The cycle detection should work (though depends on implementation)
        # At minimum, it shouldn't crash
        assert isinstance(cycles, list)


def test_rust_dependency_analyzer_export_json():
    """Test JSON export of dependency graph."""
    with tempfile.TemporaryDirectory() as tmpdir:
        with open(f"{tmpdir}/Cargo.toml", "w") as f:
            f.write("""[package]
name = "export_test"
version = "0.1.0"

[dependencies]
serde = "1.0"
""")

        os.makedirs(f"{tmpdir}/src")
        with open(f"{tmpdir}/src/lib.rs", "w") as f:
            f.write("""use serde::Serialize;

#[derive(Serialize)]
pub struct Data {}
""")

        repo = Repository(tmpdir)
        analyzer = repo.get_dependency_analyzer("rust")

        result = analyzer.export_dependency_graph(output_format="json")

        assert isinstance(result, dict)
        assert "src/lib.rs" in result
        assert "serde" in result
        assert isinstance(result["src/lib.rs"]["dependencies"], list)


def test_rust_dependency_analyzer_export_dot():
    """Test DOT format export."""
    with tempfile.TemporaryDirectory() as tmpdir:
        with open(f"{tmpdir}/Cargo.toml", "w") as f:
            f.write("""[package]
name = "dot_test"
version = "0.1.0"
""")

        os.makedirs(f"{tmpdir}/src")
        with open(f"{tmpdir}/src/lib.rs", "w") as f:
            f.write("""mod utils;
""")

        with open(f"{tmpdir}/src/utils.rs", "w") as f:
            f.write("""pub fn util() {}
""")

        repo = Repository(tmpdir)
        analyzer = repo.get_dependency_analyzer("rust")

        result = analyzer.export_dependency_graph(output_format="dot")

        assert isinstance(result, str)
        assert "digraph G" in result


def test_rust_dependency_analyzer_get_dependents():
    """Test getting modules that depend on a given module."""
    with tempfile.TemporaryDirectory() as tmpdir:
        with open(f"{tmpdir}/Cargo.toml", "w") as f:
            f.write("""[package]
name = "dependents_test"
version = "0.1.0"

[dependencies]
serde = "1.0"
""")

        os.makedirs(f"{tmpdir}/src")
        with open(f"{tmpdir}/src/lib.rs", "w") as f:
            f.write("""use serde::Serialize;
mod a;
mod b;
""")

        with open(f"{tmpdir}/src/a.rs", "w") as f:
            f.write("""use serde::Deserialize;
pub struct A {}
""")

        with open(f"{tmpdir}/src/b.rs", "w") as f:
            f.write("""use serde::Serialize;
pub struct B {}
""")

        repo = Repository(tmpdir)
        analyzer = repo.get_dependency_analyzer("rust")

        analyzer.build_dependency_graph()
        dependents = analyzer.get_dependents("serde")

        # All files using serde should be dependents
        assert "src/lib.rs" in dependents
        assert "src/a.rs" in dependents
        assert "src/b.rs" in dependents


def test_rust_dependency_analyzer_llm_context():
    """Test LLM context generation."""
    with tempfile.TemporaryDirectory() as tmpdir:
        with open(f"{tmpdir}/Cargo.toml", "w") as f:
            f.write("""[package]
name = "context_test"
version = "0.1.0"

[dependencies]
tokio = "1.0"
serde = "1.0"
""")

        os.makedirs(f"{tmpdir}/src")
        with open(f"{tmpdir}/src/lib.rs", "w") as f:
            f.write("""use tokio::runtime::Runtime;
use serde::Serialize;
use std::io;

mod handlers;
""")

        with open(f"{tmpdir}/src/handlers.rs", "w") as f:
            f.write("""pub async fn handle() {}
""")

        repo = Repository(tmpdir)
        analyzer = repo.get_dependency_analyzer("rust")

        context = analyzer.generate_llm_context(output_format="markdown")

        assert "# Dependency Analysis Summary" in context
        assert "Rust-Specific Insights" in context


def test_rust_dependency_analyzer_factory():
    """Test that the factory method correctly returns RustDependencyAnalyzer."""
    with tempfile.TemporaryDirectory() as tmpdir:
        with open(f"{tmpdir}/Cargo.toml", "w") as f:
            f.write("""[package]
name = "factory_test"
version = "0.1.0"
""")
        os.makedirs(f"{tmpdir}/src")
        with open(f"{tmpdir}/src/lib.rs", "w") as f:
            f.write("pub fn test() {}")

        repo = Repository(tmpdir)

        from kit.dependency_analyzer.rust_dependency_analyzer import RustDependencyAnalyzer

        analyzer = repo.get_dependency_analyzer("rust")
        assert isinstance(analyzer, RustDependencyAnalyzer)


def test_rust_dependency_analyzer_no_cargo_toml():
    """Test analyzer behavior when Cargo.toml is missing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        os.makedirs(f"{tmpdir}/src")
        with open(f"{tmpdir}/src/main.rs", "w") as f:
            f.write("""use std::io;

fn main() {
    println!("Hello");
}
""")

        repo = Repository(tmpdir)
        analyzer = repo.get_dependency_analyzer("rust")

        # Should not raise, just work without crate info
        graph = analyzer.build_dependency_graph()

        assert "src/main.rs" in graph
        assert "std" in graph


def test_rust_dependency_analyzer_extern_crate():
    """Test extern crate declarations (older Rust style)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        with open(f"{tmpdir}/Cargo.toml", "w") as f:
            f.write("""[package]
name = "extern_test"
version = "0.1.0"

[dependencies]
rand = "0.8"
""")

        os.makedirs(f"{tmpdir}/src")
        with open(f"{tmpdir}/src/lib.rs", "w") as f:
            f.write("""extern crate rand;

use rand::Rng;

pub fn random() -> i32 {
    rand::thread_rng().gen()
}
""")

        repo = Repository(tmpdir)
        analyzer = repo.get_dependency_analyzer("rust")

        graph = analyzer.build_dependency_graph()

        # rand should be detected from both extern crate and use
        assert "rand" in graph
        assert graph["rand"]["type"] == "external"


def test_rust_dependency_analyzer_nested_modules():
    """Test nested module structure (mod.rs pattern)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        with open(f"{tmpdir}/Cargo.toml", "w") as f:
            f.write("""[package]
name = "nested_test"
version = "0.1.0"
""")

        os.makedirs(f"{tmpdir}/src/handlers")
        with open(f"{tmpdir}/src/lib.rs", "w") as f:
            f.write("""mod handlers;

pub use handlers::*;
""")

        with open(f"{tmpdir}/src/handlers/mod.rs", "w") as f:
            f.write("""mod api;
mod web;

pub use api::*;
pub use web::*;
""")

        with open(f"{tmpdir}/src/handlers/api.rs", "w") as f:
            f.write("""pub fn api_handler() {}
""")

        with open(f"{tmpdir}/src/handlers/web.rs", "w") as f:
            f.write("""pub fn web_handler() {}
""")

        repo = Repository(tmpdir)
        analyzer = repo.get_dependency_analyzer("rust")

        graph = analyzer.build_dependency_graph()

        # All modules should be found
        assert "src/lib.rs" in graph
        assert "src/handlers/mod.rs" in graph
        assert "src/handlers/api.rs" in graph
        assert "src/handlers/web.rs" in graph


def test_rust_dependency_analyzer_target_excluded():
    """Test that target directory is excluded."""
    with tempfile.TemporaryDirectory() as tmpdir:
        with open(f"{tmpdir}/Cargo.toml", "w") as f:
            f.write("""[package]
name = "exclude_test"
version = "0.1.0"
""")

        os.makedirs(f"{tmpdir}/src")
        with open(f"{tmpdir}/src/lib.rs", "w") as f:
            f.write("""pub fn test() {}
""")

        # Create a fake target directory
        os.makedirs(f"{tmpdir}/target/debug")
        with open(f"{tmpdir}/target/debug/build.rs", "w") as f:
            f.write("""fn main() {}
""")

        repo = Repository(tmpdir)
        analyzer = repo.get_dependency_analyzer("rust")

        graph = analyzer.build_dependency_graph()

        # target files should not be in the graph
        internal_files = [m for m, d in graph.items() if d["type"] == "internal"]
        assert not any("target" in f for f in internal_files)


def test_rust_dependency_analyzer_get_dependencies_generic():
    """Test the generic get_dependencies method."""
    with tempfile.TemporaryDirectory() as tmpdir:
        with open(f"{tmpdir}/Cargo.toml", "w") as f:
            f.write("""[package]
name = "generic_test"
version = "0.1.0"

[dependencies]
serde = "1.0"
""")

        os.makedirs(f"{tmpdir}/src")
        with open(f"{tmpdir}/src/lib.rs", "w") as f:
            f.write("""use serde::Serialize;
use std::collections::HashMap;

mod utils;
""")

        with open(f"{tmpdir}/src/utils.rs", "w") as f:
            f.write("""pub fn util() {}
""")

        repo = Repository(tmpdir)
        analyzer = repo.get_dependency_analyzer("rust")

        analyzer.build_dependency_graph()

        # Test generic get_dependencies method
        deps = analyzer.get_dependencies("src/lib.rs")
        assert "serde" in deps or "std" in deps

        # Should be same as get_module_dependencies
        module_deps = analyzer.get_module_dependencies("src/lib.rs")
        assert deps == module_deps


def test_rust_dependency_analyzer_dependency_report():
    """Test dependency report generation."""
    with tempfile.TemporaryDirectory() as tmpdir:
        with open(f"{tmpdir}/Cargo.toml", "w") as f:
            f.write("""[package]
name = "report_test"
version = "0.1.0"

[dependencies]
serde = "1.0"
tokio = "1.0"
""")

        os.makedirs(f"{tmpdir}/src")
        with open(f"{tmpdir}/src/lib.rs", "w") as f:
            f.write("""use serde::Serialize;
use tokio::runtime::Runtime;
use std::io;
""")

        repo = Repository(tmpdir)
        analyzer = repo.get_dependency_analyzer("rust")

        report = analyzer.generate_dependency_report()

        assert "summary" in report
        assert report["summary"]["crate_name"] == "report_test"
        assert "external_crates" in report
        assert "std_crates_used" in report
        assert "std" in report["std_crates_used"]


def test_rust_dependency_analyzer_workspace():
    """Test handling of Cargo workspace (basic support)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a workspace Cargo.toml
        with open(f"{tmpdir}/Cargo.toml", "w") as f:
            f.write("""[workspace]
members = ["crate_a", "crate_b"]
""")

        # Create crate_a
        os.makedirs(f"{tmpdir}/crate_a/src")
        with open(f"{tmpdir}/crate_a/Cargo.toml", "w") as f:
            f.write("""[package]
name = "crate_a"
version = "0.1.0"
""")

        with open(f"{tmpdir}/crate_a/src/lib.rs", "w") as f:
            f.write("""pub fn a_func() {}
""")

        # Create crate_b
        os.makedirs(f"{tmpdir}/crate_b/src")
        with open(f"{tmpdir}/crate_b/Cargo.toml", "w") as f:
            f.write("""[package]
name = "crate_b"
version = "0.1.0"

[dependencies]
crate_a = { path = "../crate_a" }
""")

        with open(f"{tmpdir}/crate_b/src/lib.rs", "w") as f:
            f.write("""use crate_a::a_func;

pub fn b_func() {
    a_func();
}
""")

        repo = Repository(tmpdir)
        analyzer = repo.get_dependency_analyzer("rust")

        # Should not crash on workspace
        graph = analyzer.build_dependency_graph()

        # Should find the rust files
        assert any("lib.rs" in key for key in graph.keys())
