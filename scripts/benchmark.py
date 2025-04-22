import time
from kit import Repo

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Benchmark kit repo indexing.")
    parser.add_argument("repo", nargs="?", default=".", help="Path to repo root (default: .)")
    args = parser.parse_args()
    repo = Repo(args.repo)

    print(f"Indexing repo at {args.repo} ...")
    start = time.time()
    idx = repo.index()
    elapsed = time.time() - start
    num_files = len(idx["file_tree"])
    num_symbols = sum(len(syms) for syms in idx["symbols"].values())
    print(f"Indexed {num_files} files, {num_symbols} symbols in {elapsed:.2f} seconds.")

if __name__ == "__main__":
    main()
