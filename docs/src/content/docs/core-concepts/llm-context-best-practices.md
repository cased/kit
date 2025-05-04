---
title: Providing kit output as context to LLMs
---

Large Language Models (LLMs) perform best when given relevant, concise, and well-structured context. `kit` provides several ways to extract information from your codebase, each suited for different LLM prompting scenarios. Understanding how to use each data type effectively is key to maximizing the quality of LLM responses for coding tasks.

## General Principles

*   **Relevance is Key:** Only provide context directly related to the task. Too much irrelevant information can confuse the LLM.
*   **Conciseness:** LLMs have limited context windows. Use `kit` to extract *only* the necessary information, not entire files if a specific function or class will do.
*   **Structure Matters:** Present context clearly. Use Markdown formatting (like code blocks) within your prompt when feeding code or structured data.
*   **Iterate:** Start with minimal context and add more as needed if the LLM struggles.

## Using `kit` Data in Prompts

Here's how to best utilize the different data types `kit` can generate:

### 1. File Tree (`repo.get_file_tree()`)

*   **Purpose:** Provides a high-level overview of the project's structure.
*   **When to Use:**
    *   When asking the LLM broad questions about project organization (e.g., "Where would I find the authentication logic?").
    *   To give the LLM a basic map before diving into specific files.
*   **Prompting Tip:** Include the tree (potentially filtered or summarized if large) early in the prompt to set the stage. You might say, "Given the following project structure:
```
<file_tree_output>
```
     ... answer the following question..."
*   **Caution:** A full file tree can be very large for big projects. Consider using `depth` limits or filtering if needed.

### 2. Extracted Symbols (`repo.extract_symbols()`)

*   **Purpose:** Lists functions, classes, variables, etc., often with their signatures or code snippets.
*   **When to Use:**
    *   When you need the LLM to understand the available components in a file or module (e.g., "Refactor the `process_data` function in `utils.py`. Here are the symbols in that file:
```
<symbols_output>
```
").
    *   To provide context about related functions or classes that might be called.
*   **Prompting Tip:** Filter symbols to the relevant file or module. Provide the symbol list before showing the specific code snippet you want the LLM to work on.

### 3. Code Chunks (`repo.chunk_file_by_lines()`, `repo.chunk_file_by_symbols()`)

*   **Purpose:** Breaks down large files into manageable pieces.
*   **When to Use:**
    *   When dealing with files too large for the LLM's context window.
    *   To focus the LLM on a specific part of a file (symbol-based chunking is often better for this).
    *   For tasks like summarizing or documenting sections of a file.
*   **Prompting Tip:** Clearly indicate which chunk you are providing. If providing multiple chunks sequentially, maintain context clarity. Symbol-based chunking often provides more logical context boundaries than line-based chunking.

### 4. Text Search Results (`repo.search_text()`)

*   **Purpose:** Finds specific keywords or patterns.
*   **When to Use:**
    *   When you need to show the LLM specific occurrences of a variable, API call, or pattern (e.g., "Here are all the places `api.call()` is used:
```
<search_results>
```
How can I refactor this usage pattern?").
    *   Understanding the impact of changing a piece of code.
*   **Prompting Tip:** Include the search query used to generate the results for clarity. Provide the results as context for tasks like refactoring, analysis, or finding examples.

### 5. Symbol Usages (`repo.find_symbol_usages()`)

*   **Purpose:** Shows where a specific function or class is defined and referenced.
*   **When to Use:**
    *   Crucial for refactoring tasks (e.g., "I want to change the arguments of `calculate_total()`. Here are all its usages:
```
<usages_output>
```
Help me update the function definition and all call sites.").
    *   Understanding the impact of changing a piece of code.
*   **Prompting Tip:** Clearly state the symbol being investigated. Provide the list of usages when asking the LLM to modify the symbol or analyze its dependencies.

### 6. Semantic Search Results (`repo.search_semantic()`)

*   **Purpose:** Finds code related by meaning, not just keywords.
*   **When to Use:**
    *   Discovering relevant code when you don't know the exact names or terms.
    *   Finding examples of how a concept is implemented (e.g., "Show me examples of database connection handling in this project. Semantic search results:
```
<semantic_results>
```
").
*   **Prompting Tip:** Explain that the results are from semantic search. Use these results to bootstrap understanding or find starting points for more specific analysis.

### 7. Context Around a Line (`repo.extract_context_around_line()`)

*   **Purpose:** Gets the surrounding function or class for a specific line.
*   **When to Use:**
    *   Ideal for focusing the LLM on a specific piece of logic within its immediate context (e.g., "Explain the logic in this function:
```python
<context_output>
```
Specifically, what happens on line X?").
    *   Debugging errors reported for a specific line number.
*   **Prompting Tip:** This provides focused, high-quality context. Often pair it with the line number of interest.

By selecting the appropriate `kit` methods and structuring the extracted data effectively within your prompts, you can significantly improve the accuracy and relevance of LLM responses for your coding needs.
