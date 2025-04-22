# AI Code Reviewer Demo

This is a working demo of an AI-powered code reviewer that leverages symbol extraction and LLMs to review GitHub pull requests. It is CLI-based, simple to run, and easy to extend.

---

## Features
- Fetches changed files for a PR from GitHub
- Extracts code symbols from both base and head commits
- Diffs symbols to find meaningful code changes
- Builds focused prompts for an LLM (OpenAI GPT-4 or compatible)
- Outputs review suggestions to the console (optionally, posts to GitHub)
- Language-agnostic: works with any language supported by the symbol extractor

---

## Requirements
- Python 3.8+
- Dependencies in `requirements.txt`
- OpenAI API key (for LLM calls)
- GitHub CLI (`gh`) or a GitHub token (for PR info)
- The `kit` repo installed (symbol extraction)

---

## Setup

1. **Install dependencies:**
   ```sh
   pip install -r requirements.txt
   # Or use uv if preferred
   # uv pip install -r requirements.txt
   ```
2. **Install kit in editable mode (from the repo root):**
   ```sh
   uv pip install -e ../..
   ```
3. **Set your OpenAI API key:**
   - Export as an environment variable: `export OPENAI_API_KEY=sk-...`
   - Or copy `.env.example` to `.env` and fill in your key.

---

## Usage

From this directory, run:

```sh
python main.py --pr <PR_NUMBER> --repo <owner/repo> [--base BASE_SHA] [--head HEAD_SHA]
```

- The script will fetch changed files, extract/diff symbols, call the LLM, and print the review.
- To post the review as a comment, use the `--post` flag (requires authenticated GitHub CLI).

---

## Example

```sh
python main.py --pr 42 --repo your-org/your-repo --base abc123 --head def456
```

---

## Extending
- Add support for inline comments or suggestions
- Integrate with CI/CD for automation
- Use other LLM providers or prompt engineering strategies

---

## Security & Notes
- Never commit real API keys or secrets.
- The demo is for educational and prototyping purposes.

---

## License
MIT (or as per the main repo)
