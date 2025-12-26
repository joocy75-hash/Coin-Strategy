#!/usr/bin/env python3
"""전체 파이프라인 실행 스크립트.

Usage:
    python scripts/run_full_pipeline.py
    python scripts/run_full_pipeline.py --max-strategies 50 --skip-llm
"""

import subprocess
import sys
from pathlib import Path


def main():
    """main.py를 실행하여 전체 파이프라인 수행."""
    project_root = Path(__file__).parent.parent
    main_script = project_root / "main.py"

    # 명령줄 인자 전달
    cmd = [sys.executable, str(main_script)] + sys.argv[1:]

    print("=" * 60)
    print("TradingView Strategy Research Lab - Full Pipeline")
    print("=" * 60)
    print(f"Command: {' '.join(cmd)}")
    print()

    result = subprocess.run(cmd, cwd=project_root)
    sys.exit(result.returncode)


if __name__ == "__main__":
    main()
