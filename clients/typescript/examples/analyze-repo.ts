import { Kit } from "@cased/kit";

async function main() {
  // Initialize Kit
  const kit = new Kit();

  // Get the repository path from command line or use current directory
  const repoPath = process.argv[2] || ".";

  console.log(`Analyzing repository: ${repoPath}\n`);

  // Create repository instance
  const repo = kit.repository(repoPath);

  // Get git info
  const gitInfo = await repo.gitInfo();
  console.log("Git Information:");
  console.log(`- Branch: ${gitInfo.currentBranch}`);
  console.log(`- SHA: ${gitInfo.currentSha}`);
  console.log(`- Dirty: ${gitInfo.isDirty}`);
  console.log();

  // Get file tree
  const files = await repo.fileTree();
  const sourceFiles = files.filter(
    (f) =>
      !f.is_dir &&
      (f.path.endsWith(".ts") ||
        f.path.endsWith(".js") ||
        f.path.endsWith(".py")),
  );

  console.log(`Found ${sourceFiles.length} source files\n`);

  // Extract symbols from first few files
  console.log("Symbols in first 3 files:");
  for (const file of sourceFiles.slice(0, 3)) {
    const symbols = await repo.symbols(file.path);
    const functions = symbols.filter((s) => s.type === "function");
    const classes = symbols.filter((s) => s.type === "class");

    console.log(`\n${file.path}:`);
    console.log(`  - ${functions.length} functions`);
    console.log(`  - ${classes.length} classes`);

    // Show first few function names
    if (functions.length > 0) {
      console.log(
        `  - Functions: ${functions
          .slice(0, 3)
          .map((f) => f.name)
          .join(", ")}${functions.length > 3 ? "..." : ""}`,
      );
    }
  }

  // Try semantic search if available
  console.log("\n\nTrying semantic search...");
  try {
    const results = await repo.searchSemantic("error handling", {
      topK: 3,
      format: "json",
    });

    console.log('\nSemantic search results for "error handling":');
    results.forEach((result, i) => {
      console.log(
        `\n${i + 1}. ${result.file} (score: ${result.score.toFixed(3)})`,
      );
      console.log(`   ${result.content.split("\n")[0]}...`);
    });
  } catch (error) {
    console.log(
      "Semantic search not available (requires sentence-transformers)",
    );
  }
}

main().catch(console.error);
