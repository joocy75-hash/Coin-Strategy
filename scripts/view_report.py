#!/usr/bin/env python3
"""
HTML 리포트를 브라우저에서 열기
"""

import sys
import webbrowser
from pathlib import Path

def main():
    report_path = Path(__file__).parent.parent / "data" / "report.html"
    
    if not report_path.exists():
        print(f"리포트 파일이 없습니다: {report_path}")
        print("\n먼저 리포트를 생성하세요:")
        print("  python scripts/generate_report.py")
        sys.exit(1)
    
    print(f"리포트 열기: {report_path}")
    webbrowser.open(f"file://{report_path.absolute()}")
    print("브라우저에서 리포트가 열렸습니다.")

if __name__ == "__main__":
    main()
