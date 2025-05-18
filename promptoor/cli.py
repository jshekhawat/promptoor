import os
import sys
import argparse
from pathlib import Path

try:
    import pathspec
except ImportError:
    print("Please install pathspec: pip install pathspec")
    sys.exit(1)


def is_binary(file_path):
    try:
        with open(file_path, "rb") as f:
            chunk = f.read(1024)
            return b"\0" in chunk
    except Exception:
        return True  # treat unreadable files as binary


def load_gitignore(root="."):
    gitignore = Path(root) / ".gitignore"
    if not gitignore.exists():
        return pathspec.PathSpec.from_lines("gitwildmatch", [])
    with open(gitignore) as f:
        return pathspec.PathSpec.from_lines("gitwildmatch", f)


def walk_repo(root, spec, show_hidden=False):
    files = []
    for dirpath, dirnames, filenames in os.walk(root):
        rel_dir = os.path.relpath(dirpath, root)
        dirnames[:] = [
            d
            for d in dirnames
            if not spec.match_file(os.path.normpath(os.path.join(rel_dir, d)))
            and (show_hidden or not d.startswith("."))
        ]
        for filename in filenames:
            rel_file = os.path.normpath(os.path.join(rel_dir, filename))
            if not show_hidden and os.path.basename(rel_file).startswith("."):
                continue
            if spec.match_file(rel_file):
                continue
            files.append(rel_file)
    return sorted(files)


def print_tree(files, file=sys.stdout):
    print("Repo structure:", file=file)
    for f in files:
        print("  " + f, file=file)
    print(file=file)


def print_file_contents(files, root, max_file_size, file=sys.stdout):
    for f in files:
        abs_path = os.path.join(root, f)
        if not os.path.isfile(abs_path):
            continue
        if os.path.getsize(abs_path) > max_file_size:
            continue
        try:
            if is_binary(abs_path):
                continue
            print(f"\n--- File: {f} ---\n", file=file)
            with open(abs_path, "r", encoding="utf-8", errors="replace") as infile:
                print(infile.read(), file=file)
        except Exception as e:
            print(f"# Could not read {f}: {e}", file=file)


def main():
    parser = argparse.ArgumentParser(
        description="Package your repo for pasting into an LLM prompt, respecting .gitignore."
    )
    parser.add_argument(
        "repo_root",
        nargs="?",
        default=".",
        help="Root of the repo (default: current directory)",
    )
    parser.add_argument(
        "--max-size",
        type=int,
        default=30 * 1024,
        help="Max file size in bytes to include (default: 30720)",
    )
    parser.add_argument(
        "--tree-only",
        action="store_true",
        help="Only print the file tree, not contents",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=str,
        default=None,
        help="Output to a file instead of stdout",
    )
    parser.add_argument(
        "--show-hidden", action="store_true", help="Include hidden files and dirs"
    )
    args = parser.parse_args()

    repo_root = args.repo_root
    spec = load_gitignore(repo_root)
    files = walk_repo(repo_root, spec, show_hidden=args.show_hidden)

    output_file = (
        open(args.output, "w", encoding="utf-8") if args.output else sys.stdout
    )

    print_tree(files, file=output_file)
    if not args.tree_only:
        print_file_contents(files, repo_root, args.max_size, file=output_file)

    if args.output:
        output_file.close()


if __name__ == "__main__":
    main()
