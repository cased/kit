const { Kit } = require("./dist/index");

async function test() {
  console.log("Testing Kit TypeScript wrapper...\n");

  try {
    // Initialize Kit
    const kit = new Kit();
    console.log("✅ Kit initialized");

    // Create repository instance for current directory
    const repo = kit.repository("../.."); // Point to kit root
    console.log("✅ Repository created");

    // Test 1: Get git info
    console.log("\n📊 Git Info:");
    const gitInfo = await repo.gitInfo();
    console.log(`  Branch: ${gitInfo.currentBranch}`);
    console.log(`  SHA: ${gitInfo.currentSha?.substring(0, 8)}...`);
    console.log(`  Dirty: ${gitInfo.isDirty}`);

    // Test 2: Get some Python files
    console.log("\n📁 Python files:");
    const files = await repo.fileTree();
    const pyFiles = files
      .filter((f) => !f.is_dir && f.path.endsWith(".py"))
      .slice(0, 5);
    pyFiles.forEach((f) => console.log(`  - ${f.path}`));

    // Test 3: Extract symbols from a file
    if (pyFiles.length > 0) {
      console.log("\n🔍 Symbols in", pyFiles[0].path + ":");
      const symbols = await repo.symbols(pyFiles[0].path);
      const functions = symbols
        .filter((s) => s.type === "function")
        .slice(0, 3);
      functions.forEach((f) => console.log(`  - function ${f.name}`));
    }

    // Test 4: Search for something
    console.log('\n🔎 Searching for "test":');
    const searchResults = await repo.search("test");
    console.log(`  Found ${searchResults.length} results`);
    if (searchResults.length > 0) {
      console.log(
        `  First result: ${searchResults[0].file}:${searchResults[0].line}`,
      );
    }

    console.log("\n✅ All tests passed! The TypeScript wrapper works!");
  } catch (error) {
    console.error("❌ Error:", error.message);
    console.error(error.stack);
  }
}

test();
