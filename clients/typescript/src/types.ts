/**
 * Type definitions for Kit CLI wrapper
 */

export interface KitOptions {
  /** Path to the kit executable. Defaults to 'kit' */
  kitPath?: string;
  /** Path to Python executable. Defaults to 'python3' */
  pythonPath?: string;
  /** Working directory for commands */
  cwd?: string;
  /** Environment variables */
  env?: Record<string, string>;
}

export interface Symbol {
  name: string;
  type: string;
  line: number;
  end_line?: number;
  file?: string;
}

export interface FileNode {
  path: string;
  is_dir: boolean;
  size?: number;
}

export interface SearchResult {
  file: string;
  line: number;
  column: number;
  match: string;
  context?: string;
}

export interface SemanticSearchResult {
  file: string;
  score: number;
  content: string;
  type?: string;
  name?: string;
  line?: number;
}

export interface PRReviewOptions {
  githubToken?: string;
  llmProvider?: 'openai' | 'anthropic' | 'google' | 'ollama';
  model?: string;
  apiKey?: string;
  priorities?: ('high' | 'medium' | 'low')[];
  postAsComment?: boolean;
  cloneForAnalysis?: boolean;
  repoPath?: string;
}

export interface ExportOptions {
  output?: string;
  format?: 'json' | 'yaml';
  includeDependencies?: boolean;
  includeUsages?: boolean;
}

export interface SearchOptions {
  caseSensitive?: boolean;
  includePattern?: string;
  excludePattern?: string;
}

export interface SemanticSearchOptions {
  topK?: number;
  output?: string;
  embeddingModel?: string;
  chunkBy?: 'symbols' | 'lines';
  buildIndex?: boolean;
  persistDir?: string;
  format?: 'table' | 'json' | 'plain';
  ref?: string;
}

export interface SymbolOptions {
  format?: 'tree' | 'json' | 'names';
  type?: string;
  ref?: string;
}

export interface UsagesOptions {
  format?: 'table' | 'json';
  includeTests?: boolean;
  ref?: string;
}

export interface DependenciesOptions {
  direction?: 'imports' | 'imported-by' | 'both';
  transitive?: boolean;
  maxDepth?: number;
  format?: 'tree' | 'json' | 'dot';
  ref?: string;
}

export interface KitError extends Error {
  code: string;
  exitCode: number;
  stderr: string;
}

export interface GitInfo {
  currentSha: string;
  currentBranch: string;
  remoteUrl?: string;
  isDirty: boolean;
} 