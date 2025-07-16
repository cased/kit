import { spawn, SpawnOptions } from "child_process";
import {
  KitOptions,
  KitError,
  Symbol,
  FileNode,
  SearchResult,
  SemanticSearchResult,
  PRReviewOptions,
  ExportOptions,
  SearchOptions,
  SemanticSearchOptions,
  SymbolOptions,
  UsagesOptions,
  DependenciesOptions,
  GitInfo,
} from "./types";

export class Kit {
  private options: Required<KitOptions>;

  constructor(options: KitOptions = {}) {
    this.options = {
      kitPath: options.kitPath || "kit",
      pythonPath: options.pythonPath || "python3",
      cwd: options.cwd || process.cwd(),
      env: options.env || (process.env as Record<string, string>),
    };
  }

  /**
   * Execute a kit command and return the output
   */
  private async exec(args: string[], options?: SpawnOptions): Promise<string> {
    return new Promise((resolve, reject) => {
      const spawnOptions: SpawnOptions = {
        cwd: this.options.cwd,
        env: this.options.env,
        ...options,
      };

      const child = spawn(this.options.kitPath, args, spawnOptions);
      let stdout = "";
      let stderr = "";

      child.stdout?.on("data", (data) => {
        stdout += data.toString();
      });

      child.stderr?.on("data", (data) => {
        stderr += data.toString();
      });

      child.on("close", (code) => {
        if (code === 0) {
          resolve(stdout);
        } else {
          const error = new Error(`Kit command failed: ${stderr}`) as KitError;
          error.code = "KIT_COMMAND_FAILED";
          error.exitCode = code || 1;
          error.stderr = stderr;
          reject(error);
        }
      });

      child.on("error", (err) => {
        reject(err);
      });
    });
  }

  /**
   * Parse JSON output from kit commands
   */
  private parseJSON<T>(output: string): T {
    try {
      return JSON.parse(output);
    } catch (error) {
      throw new Error(`Failed to parse kit output as JSON: ${output}`);
    }
  }

  /**
   * Get symbols from a file
   */
  async symbols(path: string, options: SymbolOptions = {}): Promise<Symbol[]> {
    const args = ["symbols", path];

    if (options.format && options.format !== "json") {
      args.push("--format", options.format);
    } else {
      args.push("--format", "json");
    }

    if (options.type) args.push("--type", options.type);
    if (options.ref) args.push("--ref", options.ref);

    const output = await this.exec(args);
    return this.parseJSON<Symbol[]>(output);
  }

  /**
   * Get file tree structure
   */
  async fileTree(path: string = ".", ref?: string): Promise<FileNode[]> {
    const args = ["file-tree", path];

    // Create a temporary file for JSON output
    const tmpFile = `/tmp/kit-file-tree-${Date.now()}.json`;

    args.push("--output", tmpFile);
    if (ref) args.push("--ref", ref);

    try {
      await this.exec(args);
      // Read the JSON from the temp file
      const fs = require("fs");
      const jsonData = fs.readFileSync(tmpFile, "utf8");
      fs.unlinkSync(tmpFile); // Clean up
      return JSON.parse(jsonData);
    } catch (error) {
      // Clean up temp file on error
      try {
        require("fs").unlinkSync(tmpFile);
      } catch {}
      throw error;
    }
  }

  /**
   * Search for text in files
   */
  async search(
    query: string,
    path?: string,
    options: SearchOptions = {},
  ): Promise<SearchResult[]> {
    const args = ["search", query];
    if (path) args.push(path);

    if (options.caseSensitive) args.push("--case-sensitive");
    if (options.includePattern) args.push("--include", options.includePattern);
    if (options.excludePattern) args.push("--exclude", options.excludePattern);

    const output = await this.exec(args);
    // Parse the output format from kit search
    const lines = output.trim().split("\n");
    const results: SearchResult[] = [];

    for (const line of lines) {
      // Parse format: "file:line:column:match"
      const match = line.match(/^(.+):(\d+):(\d+):(.*)$/);
      if (match) {
        results.push({
          file: match[1],
          line: parseInt(match[2]),
          column: parseInt(match[3]),
          match: match[4],
        });
      }
    }

    return results;
  }

  /**
   * Perform semantic search
   */
  async searchSemantic(
    path: string,
    query: string,
    options: SemanticSearchOptions = {},
  ): Promise<SemanticSearchResult[]> {
    const args = ["search-semantic", path, query];

    if (options.topK) args.push("--top-k", options.topK.toString());
    if (options.output) args.push("--output", options.output);
    if (options.embeddingModel)
      args.push("--embedding-model", options.embeddingModel);
    if (options.chunkBy) args.push("--chunk-by", options.chunkBy);
    if (options.buildIndex) args.push("--build-index");
    if (options.persistDir) args.push("--persist-dir", options.persistDir);
    if (options.ref) args.push("--ref", options.ref);

    // Always use JSON format for parsing
    args.push("--format", "json");

    const output = await this.exec(args);
    return this.parseJSON<SemanticSearchResult[]>(output);
  }

  /**
   * Find usages of a symbol
   */
  async usages(
    symbolName: string,
    path?: string,
    options: UsagesOptions = {},
  ): Promise<any> {
    const args = ["usages", symbolName];
    if (path) args.push(path);

    if (options.format && options.format !== "json") {
      args.push("--format", options.format);
    } else {
      args.push("--format", "json");
    }

    if (options.includeTests) args.push("--include-tests");
    if (options.ref) args.push("--ref", options.ref);

    const output = await this.exec(args);
    return this.parseJSON(output);
  }

  /**
   * Get dependencies
   */
  async dependencies(
    filePath: string,
    options: DependenciesOptions = {},
  ): Promise<any> {
    const args = ["dependencies", filePath];

    if (options.direction) args.push("--direction", options.direction);
    if (options.transitive) args.push("--transitive");
    if (options.maxDepth) args.push("--max-depth", options.maxDepth.toString());

    if (options.format && options.format !== "json") {
      args.push("--format", options.format);
    } else {
      args.push("--format", "json");
    }

    if (options.ref) args.push("--ref", options.ref);

    const output = await this.exec(args);
    return this.parseJSON(output);
  }

  /**
   * Export repository data
   */
  async export(path?: string, options: ExportOptions = {}): Promise<any> {
    const args = ["export"];
    if (path) args.push(path);

    if (options.output) args.push("--output", options.output);
    if (options.format) args.push("--format", options.format);
    if (options.includeDependencies) args.push("--include-dependencies");
    if (options.includeUsages) args.push("--include-usages");

    const output = await this.exec(args);
    return this.parseJSON(output);
  }

  /**
   * Review a pull request
   */
  async reviewPR(
    prUrl: string,
    options: PRReviewOptions = {},
  ): Promise<string> {
    const args = ["pr-review", prUrl];

    // Set up environment variables for API keys
    const env = { ...this.options.env };

    if (options.githubToken) {
      env.GITHUB_TOKEN = options.githubToken;
    }

    if (options.apiKey) {
      switch (options.llmProvider) {
        case "openai":
          env.OPENAI_API_KEY = options.apiKey;
          break;
        case "anthropic":
          env.ANTHROPIC_API_KEY = options.apiKey;
          break;
        case "google":
          env.GOOGLE_API_KEY = options.apiKey;
          break;
      }
    }

    if (options.llmProvider) args.push("--llm-provider", options.llmProvider);
    if (options.model) args.push("--model", options.model);
    if (options.priorities) {
      args.push("--priority-filter", options.priorities.join(","));
    }
    if (options.postAsComment) args.push("--post-as-comment");
    if (options.cloneForAnalysis) args.push("--clone-for-analysis");
    if (options.repoPath) args.push("--repo-path", options.repoPath);

    const output = await this.exec(args, { env });
    return output;
  }

  /**
   * Get git information
   */
  async gitInfo(path?: string, ref?: string): Promise<GitInfo> {
    const args = ["git-info"];
    if (path) args.push(path);
    if (ref) args.push("--ref", ref);

    const output = await this.exec(args);

    // Parse the text output
    const lines = output.split("\n");
    const info: Partial<GitInfo> = {};

    for (const line of lines) {
      if (line.startsWith("Current SHA:")) {
        info.currentSha = line.split(":")[1].trim();
      } else if (line.startsWith("Current Branch:")) {
        info.currentBranch = line.split(":")[1].trim();
      } else if (line.startsWith("Remote URL:")) {
        info.remoteUrl = line.split(":").slice(1).join(":").trim();
      } else if (line.includes("dirty")) {
        info.isDirty = true;
      }
    }

    info.isDirty = info.isDirty || false;

    return info as GitInfo;
  }

  /**
   * Create a Repository instance for a specific path
   */
  repository(path: string, ref?: string): Repository {
    return new Repository(this, path, ref);
  }
}

/**
 * Repository class for repository-specific operations
 */
export class Repository {
  constructor(
    private kit: Kit,
    private path: string,
    private ref?: string,
  ) {}

  async symbols(
    filePath: string,
    options?: Omit<SymbolOptions, "ref">,
  ): Promise<Symbol[]> {
    return this.kit.symbols(`${this.path}/${filePath}`, {
      ...options,
      ref: this.ref,
    });
  }

  async fileTree(): Promise<FileNode[]> {
    return this.kit.fileTree(this.path, this.ref);
  }

  async search(
    query: string,
    options?: SearchOptions,
  ): Promise<SearchResult[]> {
    return this.kit.search(query, this.path, options);
  }

  async searchSemantic(
    query: string,
    options?: Omit<SemanticSearchOptions, "ref">,
  ): Promise<SemanticSearchResult[]> {
    return this.kit.searchSemantic(this.path, query, {
      ...options,
      ref: this.ref,
    });
  }

  async usages(
    symbolName: string,
    options?: Omit<UsagesOptions, "ref">,
  ): Promise<any> {
    return this.kit.usages(symbolName, this.path, {
      ...options,
      ref: this.ref,
    });
  }

  async dependencies(
    filePath: string,
    options?: Omit<DependenciesOptions, "ref">,
  ): Promise<any> {
    return this.kit.dependencies(`${this.path}/${filePath}`, {
      ...options,
      ref: this.ref,
    });
  }

  async export(options?: ExportOptions): Promise<any> {
    return this.kit.export(this.path, options);
  }

  async gitInfo(): Promise<GitInfo> {
    return this.kit.gitInfo(this.path, this.ref);
  }
}
