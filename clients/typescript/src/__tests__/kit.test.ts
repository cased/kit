import { spawn } from "child_process";
import { Kit, Repository } from "../kit";
import { KitError } from "../types";

// Mock child_process
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

describe("Kit", () => {
  let kit: Kit;

  beforeEach(() => {
    kit = new Kit();
    jest.clearAllMocks();
  });

  describe("constructor", () => {
    it("should use default options", () => {
      const kit = new Kit();
      expect(kit["options"].kitPath).toBe("kit");
      expect(kit["options"].pythonPath).toBe("python3");
    });

    it("should accept custom options", () => {
      const kit = new Kit({
        kitPath: "/usr/local/bin/kit",
        pythonPath: "/usr/bin/python3",
        cwd: "/tmp",
      });
      expect(kit["options"].kitPath).toBe("/usr/local/bin/kit");
      expect(kit["options"].pythonPath).toBe("/usr/bin/python3");
      expect(kit["options"].cwd).toBe("/tmp");
    });
  });

  describe("symbols", () => {
    it("should extract symbols from a file", async () => {
      const mockOutput = JSON.stringify([
        { name: "myFunction", type: "function", line: 10 },
        { name: "MyClass", type: "class", line: 20 },
      ]);

      mockSpawn.mockReturnValue(createMockProcess(mockOutput) as any);

      const symbols = await kit.symbols("test.py");

      expect(mockSpawn).toHaveBeenCalledWith(
        "kit",
        ["symbols", "test.py", "--format", "json"],
        expect.any(Object),
      );
      expect(symbols).toHaveLength(2);
      expect(symbols[0].name).toBe("myFunction");
      expect(symbols[1].name).toBe("MyClass");
    });

    it("should handle symbol options", async () => {
      mockSpawn.mockReturnValue(createMockProcess("[]") as any);

      await kit.symbols("test.py", {
        type: "function",
        ref: "main",
      });

      expect(mockSpawn).toHaveBeenCalledWith(
        "kit",
        [
          "symbols",
          "test.py",
          "--format",
          "json",
          "--type",
          "function",
          "--ref",
          "main",
        ],
        expect.any(Object),
      );
    });

    it("should handle errors", async () => {
      const mockProcess = createMockProcess("", "File not found", 1);
      mockSpawn.mockReturnValue(mockProcess as any);

      await expect(kit.symbols("nonexistent.py")).rejects.toThrow(
        "Kit command failed",
      );
    });
  });

  describe("fileTree", () => {
    it("should get file tree", async () => {
      const mockOutput = JSON.stringify([
        { path: "src", is_dir: true },
        { path: "src/main.py", is_dir: false, size: 1234 },
      ]);

      mockSpawn.mockReturnValue(createMockProcess(mockOutput) as any);

      const files = await kit.fileTree();

      expect(mockSpawn).toHaveBeenCalledWith(
        "kit",
        ["file-tree"],
        expect.any(Object),
      );
      expect(files).toHaveLength(2);
      expect(files[0].is_dir).toBe(true);
      expect(files[1].size).toBe(1234);
    });

    it("should accept path and ref", async () => {
      mockSpawn.mockReturnValue(createMockProcess("[]") as any);

      await kit.fileTree("/repo", "feature-branch");

      expect(mockSpawn).toHaveBeenCalledWith(
        "kit",
        ["file-tree", "/repo", "--ref", "feature-branch"],
        expect.any(Object),
      );
    });
  });
});
