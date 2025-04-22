import os
import argparse
import subprocess
import json
import tempfile
import shutil
from pathlib import Path
from dotenv import load_dotenv
import openai
from kit.tree_sitter_symbol_extractor import TreeSitterSymbolExtractor
from kit import Repo

# Load OpenAI API key from environment
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# --- Symbol Extraction Logic ---
def extract_symbols_from_code(ext, code):
    return TreeSitterSymbolExtractor.extract_symbols(ext, code)

def extract_symbols_for_commit(repo_path, commit_sha, file_path):
    tmp_dir = tempfile.mkdtemp()
    try:
        result = subprocess.run([
            "git", "show", f"{commit_sha}:{file_path}"
        ], cwd=repo_path, check=True, capture_output=True, text=True)
        file_tmp_path = os.path.join(tmp_dir, os.path.basename(file_path))
        with open(file_tmp_path, "w") as f:
            f.write(result.stdout)
        ext = Path(file_path).suffix
        with open(file_tmp_path, "r", encoding="utf-8") as f:
            code = f.read()
        return extract_symbols_from_code(ext, code)
    finally:
        shutil.rmtree(tmp_dir)

# --- Diff Logic ---
def diff_symbols(symbols_before, symbols_after):
    before_set = {(s['type'], s['name']) for s in symbols_before}
    after_set = {(s['type'], s['name']) for s in symbols_after}
    added = after_set - before_set
    removed = before_set - after_set
    return {
        "added": [s for s in symbols_after if (s['type'], s['name']) in added],
        "removed": [s for s in symbols_before if (s['type'], s['name']) in removed]
    }

# --- Whole Repo Summarization ---
def summarize_codebase(repo_path: str) -> str:
    repo = Repo(repo_path)
    index = repo.index()
    lines = [f"# Codebase Summary for {repo_path}\n"]
    lines.append("## File Tree\n")
    for file in index["file_tree"]:
        lines.append(f"- {file}")
    lines.append("\n## Symbols\n")
    for file, symbols in index["symbols"].items():
        lines.append(f"### {file}")
        for symbol in symbols:
            lines.append(f"- **{symbol['type']}** `{symbol['name']}`")
        lines.append("")
    return "\n".join(lines)

# --- LLM Prompt Construction ---
def build_llm_prompt(symbol_diff, file_path):
    prompt = f"Review the following code changes in {file_path}:\n"
    if symbol_diff['added']:
        prompt += "\nNew symbols:\n"
        for s in symbol_diff['added']:
            prompt += f"- {s['type']} `{s['name']}`\n"
    if symbol_diff['removed']:
        prompt += "\nRemoved symbols:\n"
        for s in symbol_diff['removed']:
            prompt += f"- {s['type']} `{s['name']}`\n"
    prompt += "\nSuggest improvements, spot errors, and flag security issues."
    return prompt

# --- LLM Call ---
def get_llm_review(prompt, api_key):
    openai.api_key = api_key
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[{"role": "system", "content": "You are a senior code reviewer."},
                  {"role": "user", "content": prompt}]
    )
    return response['choices'][0]['message']['content']

# --- GitHub Integration ---
def get_changed_files(pr_number, repo_slug):
    cmd = [
        "gh", "pr", "view", str(pr_number),
        "--repo", repo_slug,
        "--json", "files,baseRefOid,headRefOid"
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    pr_info = json.loads(result.stdout)
    files = [f["path"] for f in pr_info["files"]]
    base_sha = pr_info["baseRefOid"]
    head_sha = pr_info["headRefOid"]
    return files, base_sha, head_sha

def post_github_comment(pr_number, repo_slug, body):
    subprocess.run([
        "gh", "pr", "comment", str(pr_number),
        "--repo", repo_slug,
        "--body", body
    ], check=True)

# --- Main CLI Entrypoint ---
def main():
    parser = argparse.ArgumentParser(description="AI Code Reviewer Demo")
    parser.add_argument("--pr", type=int, required=True, help="Pull request number")
    parser.add_argument("--repo", required=True, help="GitHub repo slug (e.g. owner/repo)")
    parser.add_argument("--base", help="Base commit SHA (optional)")
    parser.add_argument("--head", help="Head commit SHA (optional)")
    parser.add_argument("--post", action="store_true", help="Post review as GitHub PR comment")
    args = parser.parse_args()

    if not OPENAI_API_KEY:
        print("OPENAI_API_KEY not set. Set it in .env or as an environment variable.")
        exit(1)

    files, pr_base_sha, pr_head_sha = get_changed_files(args.pr, args.repo)
    base_sha = args.base or pr_base_sha
    head_sha = args.head or pr_head_sha

    # Whole repo understanding: summarize the repo at HEAD
    repo_summary = summarize_codebase(".")
    print("\n--- WHOLE REPO SUMMARY (HEAD) ---\n")
    print(repo_summary)

    for file_path in files:
        print(f"\n=== {file_path} ===")
        symbols_base = extract_symbols_for_commit(".", base_sha, file_path)
        symbols_head = extract_symbols_for_commit(".", head_sha, file_path)
        symbol_diff = diff_symbols(symbols_base, symbols_head)
        if not symbol_diff['added'] and not symbol_diff['removed']:
            print("No meaningful symbol changes detected.")
            continue
        # Attach repo summary to prompt for LLM
        prompt = f"Repository summary (for context):\n{repo_summary}\n\n" + build_llm_prompt(symbol_diff, file_path)
        print("Prompt:\n", prompt)
        review = get_llm_review(prompt, OPENAI_API_KEY)
        print("\nAI Review Suggestion:\n", review)
        if args.post:
            post_github_comment(args.pr, args.repo, review)
            print("(Posted as PR comment)")

if __name__ == "__main__":
    main()
