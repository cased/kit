---
title: Providing Kit Output as Context to LLMs
---

## General Principles

Large Language Models (LLMs) perform best with relevant, concise, and structured context. The `kit` library provides multiple ways to extract information from your codebase suited to different prompting scenarios. Effective use of these data types maximizes the quality of LLM responses.

* **Relevance:** Provide only directly related context. Irrelevant information can confuse the LLM.
* **Conciseness:** Use minimal necessary context to fit within limited context windows.
* **Clear Structure:** Format context clearly using Markdown, especially code blocks.
* **Iteration:** Start minimal and add context incrementally as required.

## Using `kit` Data in Prompts

Here's how to effectively utilize different `kit` data types:

### 1. File Tree (`repo.get_file_tree()`)

* **Purpose:** Overview of project structure.
* **Use for:**
  * Broad questions about project organization (e.g., locating authentication logic).
  * Providing an initial map before specifics.
* **Prompt Example:**

> Given the following project structure:
>
> ```
> <file_tree_output>
> ```
>
> Answer the following question...

* **Caution:** Use depth limits or filtering for large projects.

### 2. Extracted Symbols (`repo.extract_symbols()`)

* **Purpose:** Lists functions, classes, variables with signatures or snippets.
* **Use for:**
  * Contextualizing components within a file or module.
  * Informing the LLM about available functions/classes.
* **Prompt Example:**

> Refactor `process_data` in `utils.py`. Symbols in this file:
>
> ```
> <symbols_output>
> ```

* **Tip:** Filter symbols to relevant files/modules.

### 3. Code Chunks (`repo.chunk_file_by_lines()`, `repo.chunk_file_by_symbols()`)

* **Purpose:** Splitting large files into manageable segments.
* **Use for:**
  * Handling files larger than the context window.
  * Focusing on specific code sections.
  * Tasks like summarizing/documentation.
* **Prompt Example:**

> Summarize the following chunk:
>
> ```python
> <code_chunk>
> ```

* **Tip:** Clearly identify chunks and prefer symbol-based chunking.

### 4. Text Search Results (`repo.search_text()`)

* **Purpose:** Finding specific patterns or keywords.
* **Use for:**
  * Displaying specific variable/API call occurrences.
  * Assessing impact of changes.
* **Prompt Example:**

> Here are all occurrences of `api.call()`:
>
> ```
> <search_results>
> ```
>
> How can we refactor this pattern?

* **Tip:** Clearly specify the search query.

### 5. Symbol Usages (`repo.find_symbol_usages()`)

* **Purpose:** Locating definitions and references of functions/classes.
* **Use for:**
  * Refactoring functions/classes and updating call sites.
  * Analyzing dependencies and impacts.
* **Prompt Example:**

> Update arguments for `calculate_total()`. Here are its usages:
>
> ```
> <usages_output>
> ```
>
> Provide an updated function definition and adjust call sites.

* **Tip:** Clearly indicate the investigated symbol.

### 6. Semantic Search Results (`repo.search_semantic()`)

* **Purpose:** Finding code by meaning rather than exact text.
* **Use for:**
  * Identifying relevant code without exact names.
  * Exploring concept implementation examples.
* **Prompt Example:**

> Examples of database connection handling:
>
> ```
> <semantic_results>
> ```

* **Tip:** Indicate results come from semantic search.

### 7. Context Around a Line (`repo.extract_context_around_line()`)

* **Purpose:** Surrounding code context of a specific line.
* **Use for:**
  * Detailed logic explanation or debugging.
* **Prompt Example:**

> Explain this function's logic:
>
> ```python
> <context_output>
> ```
>
> Specifically, what happens on line X?

* **Tip:** Pair with specific line numbers for targeted context.

Using these structured approaches will significantly enhance LLM accuracy and response relevance in coding tasks.
