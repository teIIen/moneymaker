import argparse
from pathlib import Path


def clear_file(path: Path) -> None:
    path.write_text("", encoding="utf-8")


def clear_all_logs(logs_dir: Path) -> int:
    count = 0
    for file_path in logs_dir.glob("*.log"):
        clear_file(file_path)
        count += 1
    return count


def main() -> None:
    parser = argparse.ArgumentParser(description="Clear log files in project logs directory.")
    parser.add_argument("--all", action="store_true", help="Clear all .log files in logs/.")
    parser.add_argument("--file", type=str, help="Clear one log file by name, e.g. MainLoop.log")
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parents[1]
    logs_dir = project_root / "logs"

    if not logs_dir.exists():
        raise SystemExit(f"Logs directory does not exist: {logs_dir}")

    if args.file:
        target = logs_dir / args.file
        if not target.exists():
            raise SystemExit(f"Log file not found: {target}")
        clear_file(target)
        print(f"Cleared: {target.name}")
        return

    if args.all or not args.file:
        total = clear_all_logs(logs_dir)
        print(f"Cleared log files: {total}")


if __name__ == "__main__":
    main()
