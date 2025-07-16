import { spawn } from "child_process";
import { Kit } from "../kit";

jest.mock("child_process");
const mockSpawn = spawn as jest.MockedFunction<typeof spawn>;

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

describe("Kit - Semantic Search", () => {
  let kit: Kit;

  beforeEach(() => {
    kit = new Kit();
    jest.clearAllMocks();
  });

  describe("searchSemantic", () => {
    it("should perform semantic search", async () => {
      const mockOutput = JSON.stringify([
        {
          file: "auth.py",
          score: 0.89,
          content: "def authenticate(user, password):",
          type: "function",
          name: "authenticate",
          line: 45,
        },
        {
          file: "user.py",
          score: 0.76,
          content: "class User:",
          type: "class",
          name: "User",
          line: 10,
        },
      ]);

      mockSpawn.mockReturnValue(createMockProcess(mockOutput) as any);

      const results = await kit.searchSemantic("/repo", "authentication logic");

      expect(mockSpawn).toHaveBeenCalledWith(
        "kit",
        [
          "search-semantic",
          "/repo",
          "authentication logic",
          "--format",
          "json",
        ],
        expect.any(Object),
      );
      expect(results).toHaveLength(2);
      expect(results[0].score).toBe(0.89);
      expect(results[0].name).toBe("authenticate");
    });

    it("should handle all semantic search options", async () => {
      mockSpawn.mockReturnValue(createMockProcess("[]") as any);

      await kit.searchSemantic("/repo", "test query", {
        topK: 20,
        output: "results.json",
        embeddingModel: "all-mpnet-base-v2",
        chunkBy: "lines",
        buildIndex: true,
        persistDir: ".semantic-cache",
        ref: "main",
      });

      expect(mockSpawn).toHaveBeenCalledWith(
        "kit",
        [
          "search-semantic",
          "/repo",
          "test query",
          "--top-k",
          "20",
          "--output",
          "results.json",
          "--embedding-model",
          "all-mpnet-base-v2",
          "--chunk-by",
          "lines",
          "--build-index",
          "--persist-dir",
          ".semantic-cache",
          "--ref",
          "main",
          "--format",
          "json",
        ],
        expect.any(Object),
      );
    });

    it("should handle missing sentence-transformers", async () => {
      const mockProcess = createMockProcess(
        "",
        "The 'sentence-transformers' package is required for semantic search",
        1,
      );
      mockSpawn.mockReturnValue(mockProcess as any);

      await expect(kit.searchSemantic("/repo", "test")).rejects.toThrow(
        "The 'sentence-transformers' package is required",
      );
    });
  });
});
