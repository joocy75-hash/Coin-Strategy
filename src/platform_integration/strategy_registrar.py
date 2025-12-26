"""
Strategy Registrar Module

TradingView 전략을 플랫폼의 strategies 폴더에 자동 등록하는 모듈
"""

import os
import shutil
import re
from pathlib import Path
from typing import List, Optional
from datetime import datetime


class StrategyRegistrar:
    """전략 자동 등록 클래스"""

    def __init__(self, platform_path: Optional[str] = None):
        """
        Args:
            platform_path: 플랫폼 루트 경로 (기본값: 자동 탐지)
        """
        if platform_path:
            self.platform_path = Path(platform_path)
        else:
            # 기본 플랫폼 경로 설정 (현재 프로젝트의 상위 디렉토리)
            self.platform_path = Path(__file__).parent.parent.parent.parent / 'platform'

        self.strategies_path = self.platform_path / 'strategies'
        self.loader_path = self.strategies_path / 'strategy_loader.py'
        self.init_path = self.strategies_path / '__init__.py'
        self.backup_path = self.platform_path / 'backups'

        # 백업 디렉토리 생성
        self.backup_path.mkdir(parents=True, exist_ok=True)

    def register_strategy(
        self,
        strategy_file_path: str,
        strategy_code: str,
        class_name: str
    ) -> bool:
        """
        전략을 플랫폼에 등록

        Args:
            strategy_file_path: 전략 파일 경로
            strategy_code: 전략 코드 (예: 'SMA_CROSS')
            class_name: 전략 클래스명 (예: 'SMACrossStrategy')

        Returns:
            bool: 등록 성공 여부
        """
        try:
            # 1. 전략 파일이 존재하는지 확인
            source_path = Path(strategy_file_path)
            if not source_path.exists():
                raise FileNotFoundError(f"전략 파일을 찾을 수 없습니다: {strategy_file_path}")

            # 2. strategies 폴더가 존재하는지 확인
            if not self.strategies_path.exists():
                self.strategies_path.mkdir(parents=True, exist_ok=True)
                print(f"Strategies 폴더 생성: {self.strategies_path}")

            # 3. 전략 파일 복사
            dest_filename = f"{strategy_code.lower()}.py"
            dest_path = self.strategies_path / dest_filename

            # 기존 파일이 있으면 백업
            if dest_path.exists():
                self._backup_file(dest_path)

            shutil.copy2(source_path, dest_path)
            print(f"전략 파일 복사 완료: {dest_path}")

            # 4. strategy_loader.py 업데이트
            self._update_loader(strategy_code, class_name, dest_filename)
            print(f"Strategy loader 업데이트 완료")

            # 5. __init__.py 업데이트
            self._update_init(strategy_code)
            print(f"__init__.py 업데이트 완료")

            print(f"\n전략 '{strategy_code}' 등록 성공!")
            return True

        except Exception as e:
            print(f"전략 등록 실패: {str(e)}")
            return False

    def unregister_strategy(self, strategy_code: str) -> bool:
        """
        전략을 플랫폼에서 제거

        Args:
            strategy_code: 전략 코드

        Returns:
            bool: 제거 성공 여부
        """
        try:
            # 1. 전략 파일 삭제
            strategy_file = self.strategies_path / f"{strategy_code.lower()}.py"
            if strategy_file.exists():
                self._backup_file(strategy_file)
                strategy_file.unlink()
                print(f"전략 파일 삭제: {strategy_file}")

            # 2. strategy_loader.py에서 제거
            self._remove_from_loader(strategy_code)
            print(f"Strategy loader에서 제거 완료")

            # 3. __init__.py에서 제거
            self._remove_from_init(strategy_code)
            print(f"__init__.py에서 제거 완료")

            print(f"\n전략 '{strategy_code}' 제거 성공!")
            return True

        except Exception as e:
            print(f"전략 제거 실패: {str(e)}")
            return False

    def list_registered_strategies(self) -> List[str]:
        """
        등록된 전략 목록 반환

        Returns:
            List[str]: 전략 코드 리스트
        """
        if not self.init_path.exists():
            return []

        try:
            with open(self.init_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # STRATEGY_CODES 리스트 찾기
            match = re.search(r'STRATEGY_CODES\s*=\s*\[(.*?)\]', content, re.DOTALL)
            if match:
                codes_str = match.group(1)
                # 문자열에서 전략 코드 추출
                codes = re.findall(r'["\']([^"\']+)["\']', codes_str)
                return codes

            return []

        except Exception as e:
            print(f"전략 목록 조회 실패: {str(e)}")
            return []

    def _backup_file(self, filepath: Path):
        """
        파일 백업

        Args:
            filepath: 백업할 파일 경로
        """
        if not filepath.exists():
            return

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_filename = f"{filepath.stem}_{timestamp}{filepath.suffix}"
        backup_dest = self.backup_path / backup_filename

        shutil.copy2(filepath, backup_dest)
        print(f"백업 생성: {backup_dest}")

    def _update_loader(self, strategy_code: str, class_name: str, filename: str):
        """
        strategy_loader.py 업데이트

        Args:
            strategy_code: 전략 코드
            class_name: 클래스명
            filename: 파일명
        """
        # strategy_loader.py가 없으면 생성
        if not self.loader_path.exists():
            self._create_loader_file()

        # 기존 파일 백업
        self._backup_file(self.loader_path)

        with open(self.loader_path, 'r', encoding='utf-8') as f:
            content = f.read()

        module_name = filename.replace('.py', '')

        # import 문 추가
        import_line = f"from .{module_name} import {class_name}"
        if import_line not in content:
            # import 섹션 찾기
            import_section_match = re.search(r'(# Strategy imports.*?)(\n\n)', content, re.DOTALL)
            if import_section_match:
                imports = import_section_match.group(1)
                imports += f"\n{import_line}"
                content = content.replace(import_section_match.group(1), imports)
            else:
                # import 섹션이 없으면 생성
                content = f"# Strategy imports\n{import_line}\n\n" + content

        # STRATEGY_REGISTRY에 추가
        registry_entry = f"    '{strategy_code}': {class_name},"
        if registry_entry not in content:
            registry_match = re.search(r'(STRATEGY_REGISTRY\s*=\s*\{)(.*?)(\})', content, re.DOTALL)
            if registry_match:
                registry_content = registry_match.group(2)
                if registry_content.strip():
                    registry_content += f"\n{registry_entry}"
                else:
                    registry_content = f"\n{registry_entry}\n"
                content = content.replace(
                    registry_match.group(0),
                    f"{registry_match.group(1)}{registry_content}{registry_match.group(3)}"
                )
            else:
                # STRATEGY_REGISTRY가 없으면 생성
                content += f"\n\nSTRATEGY_REGISTRY = {{\n{registry_entry}\n}}\n"

        with open(self.loader_path, 'w', encoding='utf-8') as f:
            f.write(content)

    def _update_init(self, strategy_code: str):
        """
        __init__.py 업데이트

        Args:
            strategy_code: 전략 코드
        """
        # __init__.py가 없으면 생성
        if not self.init_path.exists():
            self._create_init_file()

        # 기존 파일 백업
        self._backup_file(self.init_path)

        with open(self.init_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # STRATEGY_CODES 리스트에 추가
        strategy_entry = f"    '{strategy_code}',"
        if strategy_entry not in content:
            codes_match = re.search(r'(STRATEGY_CODES\s*=\s*\[)(.*?)(\])', content, re.DOTALL)
            if codes_match:
                codes_content = codes_match.group(2)
                if codes_content.strip():
                    codes_content += f"\n{strategy_entry}"
                else:
                    codes_content = f"\n{strategy_entry}\n"
                content = content.replace(
                    codes_match.group(0),
                    f"{codes_match.group(1)}{codes_content}{codes_match.group(3)}"
                )
            else:
                # STRATEGY_CODES가 없으면 생성
                content += f"\n\nSTRATEGY_CODES = [\n{strategy_entry}\n]\n"

        with open(self.init_path, 'w', encoding='utf-8') as f:
            f.write(content)

    def _remove_from_loader(self, strategy_code: str):
        """
        strategy_loader.py에서 전략 제거

        Args:
            strategy_code: 전략 코드
        """
        if not self.loader_path.exists():
            return

        self._backup_file(self.loader_path)

        with open(self.loader_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        new_lines = []
        skip_next = False

        for line in lines:
            # import 문 제거
            if f"{strategy_code.lower()}" in line.lower() and "import" in line:
                continue
            # STRATEGY_REGISTRY 엔트리 제거
            if f"'{strategy_code}'" in line or f'"{strategy_code}"' in line:
                continue
            new_lines.append(line)

        with open(self.loader_path, 'w', encoding='utf-8') as f:
            f.writelines(new_lines)

    def _remove_from_init(self, strategy_code: str):
        """
        __init__.py에서 전략 제거

        Args:
            strategy_code: 전략 코드
        """
        if not self.init_path.exists():
            return

        self._backup_file(self.init_path)

        with open(self.init_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        new_lines = []
        for line in lines:
            # STRATEGY_CODES 엔트리 제거
            if f"'{strategy_code}'" in line or f'"{strategy_code}"' in line:
                continue
            new_lines.append(line)

        with open(self.init_path, 'w', encoding='utf-8') as f:
            f.writelines(new_lines)

    def _create_loader_file(self):
        """strategy_loader.py 파일 생성"""
        template = '''"""
Strategy Loader Module

등록된 전략들을 로드하는 모듈
"""

# Strategy imports

STRATEGY_REGISTRY = {
}


def load_strategy(strategy_code: str):
    """
    전략 코드로 전략 클래스 로드

    Args:
        strategy_code: 전략 코드

    Returns:
        Strategy class or None
    """
    return STRATEGY_REGISTRY.get(strategy_code)


def get_available_strategies():
    """
    사용 가능한 전략 목록 반환

    Returns:
        List[str]: 전략 코드 리스트
    """
    return list(STRATEGY_REGISTRY.keys())
'''
        with open(self.loader_path, 'w', encoding='utf-8') as f:
            f.write(template)

    def _create_init_file(self):
        """__init__.py 파일 생성"""
        template = '''"""
Strategies Module

TradingView 전략 모음
"""

from .strategy_loader import load_strategy, get_available_strategies

STRATEGY_CODES = [
]

__all__ = [
    'load_strategy',
    'get_available_strategies',
    'STRATEGY_CODES',
]
'''
        with open(self.init_path, 'w', encoding='utf-8') as f:
            f.write(template)
