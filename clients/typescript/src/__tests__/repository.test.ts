import { spawn } from "child_process";
import { Kit, Repository } from "../kit";
import fs from "fs";

jest.mock("child_process");
const mockSpawn = spawn as jest.MockedFunction<typeof spawn>;

jest.mock("fs");
const mockFs = fs as unknown as {
  readFileSync: jest.Mock;
  unlinkSync: jest.Mock;
};

// Helper to create mock child process
function createMockProcess(
  stdout: string,
  stderr: string = "",
  exitCode: number = 0,
) {
  const mockProcess = {
    stdout: {
      on: jest.fn((event, handler) => {
        if (event === "data") {
          handler(Buffer.from(stdout));
        }
      }),
    },
    stderr: {
      on: jest.fn((event, handler) => {
        if (event === "data" && stderr) {
          handler(Buffer.from(stderr));
        }
      }),
    },
    on: jest.fn((event, handler) => {
      if (event === "close") {
        handler(exitCode);
      }
    }),
  };

  return mockProcess;
}

describe("Repository", () => {
  let kit: Kit;
  let repo: Repository;

  beforeEach(() => {
    kit = new Kit();
    repo = kit.repository("/test/repo", "main");
    jest.clearAllMocks();
    mockFs.readFileSync.mockReset();
    mockFs.unlinkSync.mockReset();
  });

  describe("symbols", () => {
    it("should get symbols with repo path prepended", async () => {
      const mockOutput = JSON.stringify([
        { name: "test_function", type: "function", line: 5 },
      ]);

      mockSpawn.mockReturnValue(createMockProcess(mockOutput) as any);

      const symbols = await repo.symbols("src/main.py");

      expect(mockSpawn).toHaveBeenCalledWith(
        "kit",
        [
          "symbols",
          "/test/repo/src/main.py",
          "--format",
          "json",
          "--ref",
          "main",
        ],
        expect.any(Object),
      );
      expect(symbols[0].name).toBe("test_function");
    });
  });

  describe("fileTree", () => {
    it("should get file tree for the repository", async () => {
      const mockOutput = JSON.stringify([{ path: "README.md", is_dir: false }]);

      mockSpawn.mockReturnValue(createMockProcess("File tree written") as any);
      mockFs.readFileSync.mockReturnValue(mockOutput);

      const _files = await repo.fileTree();

      expect(mockSpawn).toHaveBeenCalledWith(
        "kit",
        [
          "file-tree",
          "/test/repo",
          "--output",
          expect.stringMatching(/kit-file-tree-/),
          "--ref",
          "main",
        ],
        expect.any(Object),
      );
      expect(_files.length).toBeGreaterThanOrEqual(0);
    });
  });

  describe("searchSemantic", () => {
    it("should perform semantic search in the repository", async () => {
      const mockOutput = JSON.stringify([
        { file: "test.py", score: 0.9, content: "test content" },
      ]);

      mockSpawn.mockReturnValue(createMockProcess(mockOutput) as any);

      const results = await repo.searchSemantic("query", { topK: 5 });

      expect(mockSpawn).toHaveBeenCalledWith(
        "kit",
        [
          "search-semantic",
          "/test/repo",
          "query",
          "--top-k",
          "5",
          "--ref",
          "main",
          "--format",
          "json",
        ],
        expect.any(Object),
      );
      expect(results[0].score).toBe(0.9);
    });
  });

  describe("without ref", () => {
    it("should work without a ref parameter", async () => {
      const repoNoRef = kit.repository("/test/repo");
      mockSpawn.mockReturnValue(createMockProcess("[]") as any);

      await repoNoRef.symbols("test.py");

      expect(mockSpawn).toHaveBeenCalledWith(
        "kit",
        ["symbols", "/test/repo/test.py", "--format", "json"],
        expect.any(Object),
      );
      // Note: no --ref parameter
    });
  });
});
