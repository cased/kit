import { execSync } from "child_process";
import path from "path";

// Skip integration test if environment variable set (e.g., CI debug)
const maybeDescribe = process.env.SKIP_INTEGRATION ? describe.skip : describe;

maybeDescribe("Kit TypeScript wrapper – integration", () => {
  it("should execute test-wrapper script successfully", () => {
    const repoRoot = path.resolve(__dirname, "../../../../");

    // Build the TypeScript client (dist/) – quiet if already built
    execSync("npm run build", { cwd: path.join(repoRoot, "clients/typescript"), stdio: "inherit" });

    // Run the manual wrapper test script; will throw if non-zero exit
    execSync("node clients/typescript/test-wrapper.js", { cwd: repoRoot, stdio: "inherit" });
  }, 300_000); // allow up to 5 min in CI
}); 