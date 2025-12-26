"""
Strategy Deployer Module

전략 서버 배포 및 핫 리로드 모듈
"""

import os
import sys
import importlib
import subprocess
import time
from pathlib import Path
from typing import Dict, Optional, List
import psutil


class StrategyDeployer:
    """전략 배포 클래스"""

    def __init__(self, server_path: Optional[str] = None):
        """
        Args:
            server_path: 서버 루트 경로 (기본값: 자동 탐지)
        """
        if server_path:
            self.server_path = Path(server_path)
        else:
            # 기본 서버 경로 설정
            self.server_path = Path(__file__).parent.parent.parent.parent / 'platform'

        self.strategies_path = self.server_path / 'strategies'
        self.server_script = self.server_path / 'server.py'

        # 서버 프로세스 정보
        self.server_process = None

    def hot_reload_strategy(self, strategy_module: str) -> bool:
        """
        전략 모듈을 핫 리로드 (서버 재시작 없이)

        Args:
            strategy_module: 전략 모듈명 (예: 'strategies.sma_cross')

        Returns:
            bool: 리로드 성공 여부
        """
        try:
            # 1. 모듈이 이미 로드되어 있는지 확인
            if strategy_module in sys.modules:
                # 기존 모듈 리로드
                module = sys.modules[strategy_module]
                importlib.reload(module)
                print(f"모듈 '{strategy_module}' 핫 리로드 완료")
            else:
                # 새로운 모듈 import
                importlib.import_module(strategy_module)
                print(f"모듈 '{strategy_module}' 로드 완료")

            # 2. strategy_loader도 리로드
            loader_module = 'strategies.strategy_loader'
            if loader_module in sys.modules:
                importlib.reload(sys.modules[loader_module])
                print(f"Strategy loader 리로드 완료")

            return True

        except Exception as e:
            print(f"핫 리로드 실패: {str(e)}")
            return False

    def restart_server(self, python_executable: str = 'python') -> bool:
        """
        서버 재시작

        Args:
            python_executable: Python 실행 파일 경로

        Returns:
            bool: 재시작 성공 여부
        """
        try:
            # 1. 기존 서버 프로세스 종료
            self._stop_server()

            # 2. 잠시 대기
            time.sleep(2)

            # 3. 새로운 서버 프로세스 시작
            if not self.server_script.exists():
                print(f"서버 스크립트를 찾을 수 없습니다: {self.server_script}")
                return False

            print(f"서버 시작 중: {self.server_script}")

            # 서버를 백그라운드 프로세스로 시작
            self.server_process = subprocess.Popen(
                [python_executable, str(self.server_script)],
                cwd=str(self.server_path),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

            # 서버가 정상적으로 시작되었는지 확인
            time.sleep(3)
            if self.server_process.poll() is None:
                print(f"서버 시작 완료 (PID: {self.server_process.pid})")
                return True
            else:
                stdout, stderr = self.server_process.communicate()
                print(f"서버 시작 실패:")
                print(f"STDOUT: {stdout}")
                print(f"STDERR: {stderr}")
                return False

        except Exception as e:
            print(f"서버 재시작 실패: {str(e)}")
            return False

    def check_deployment_status(self) -> Dict:
        """
        배포 상태 확인

        Returns:
            Dict: 배포 상태 정보
        """
        status = {
            'server_running': False,
            'server_pid': None,
            'server_path': str(self.server_path),
            'strategies_path': str(self.strategies_path),
            'strategies_count': 0,
            'registered_strategies': [],
            'server_accessible': False,
        }

        try:
            # 1. 서버 프로세스 확인
            if self.server_process and self.server_process.poll() is None:
                status['server_running'] = True
                status['server_pid'] = self.server_process.pid
            else:
                # 실행 중인 Python 프로세스에서 서버 찾기
                for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                    try:
                        if proc.info['name'] and 'python' in proc.info['name'].lower():
                            cmdline = proc.info['cmdline']
                            if cmdline and any('server.py' in cmd for cmd in cmdline):
                                status['server_running'] = True
                                status['server_pid'] = proc.info['pid']
                                break
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        continue

            # 2. 등록된 전략 확인
            if self.strategies_path.exists():
                strategy_files = list(self.strategies_path.glob('*.py'))
                strategy_files = [f for f in strategy_files
                                if f.name not in ['__init__.py', 'strategy_loader.py']]
                status['strategies_count'] = len(strategy_files)
                status['registered_strategies'] = [f.stem.upper() for f in strategy_files]

            # 3. 서버 접근성 확인 (간단한 health check)
            # 실제 환경에서는 HTTP 요청으로 확인 가능
            status['server_accessible'] = status['server_running']

        except Exception as e:
            print(f"상태 확인 중 오류 발생: {str(e)}")

        return status

    def validate_strategy(self, strategy_code: str) -> Dict:
        """
        전략 유효성 검증

        Args:
            strategy_code: 전략 코드

        Returns:
            Dict: 검증 결과
        """
        result = {
            'valid': False,
            'exists': False,
            'importable': False,
            'has_required_methods': False,
            'errors': [],
            'warnings': [],
        }

        try:
            # 1. 전략 파일 존재 확인
            strategy_file = self.strategies_path / f"{strategy_code.lower()}.py"
            if not strategy_file.exists():
                result['errors'].append(f"전략 파일을 찾을 수 없습니다: {strategy_file}")
                return result

            result['exists'] = True

            # 2. 모듈 import 가능 여부 확인
            try:
                module_name = f"strategies.{strategy_code.lower()}"

                # sys.path에 서버 경로 추가
                if str(self.server_path) not in sys.path:
                    sys.path.insert(0, str(self.server_path))

                # 모듈 import 시도
                if module_name in sys.modules:
                    module = importlib.reload(sys.modules[module_name])
                else:
                    module = importlib.import_module(module_name)

                result['importable'] = True

                # 3. 필수 메서드 확인
                # 전략 클래스 찾기
                strategy_class = None
                for attr_name in dir(module):
                    attr = getattr(module, attr_name)
                    if (isinstance(attr, type) and
                        attr_name.endswith('Strategy') and
                        attr.__module__ == module_name):
                        strategy_class = attr
                        break

                if strategy_class:
                    required_methods = ['__init__', 'generate_signals']
                    missing_methods = []

                    for method in required_methods:
                        if not hasattr(strategy_class, method):
                            missing_methods.append(method)

                    if missing_methods:
                        result['errors'].append(
                            f"필수 메서드 누락: {', '.join(missing_methods)}"
                        )
                    else:
                        result['has_required_methods'] = True
                else:
                    result['warnings'].append("전략 클래스를 찾을 수 없습니다")

            except ImportError as e:
                result['errors'].append(f"모듈 import 실패: {str(e)}")
            except Exception as e:
                result['errors'].append(f"모듈 검증 중 오류: {str(e)}")

            # 4. 전체 유효성 판단
            result['valid'] = (
                result['exists'] and
                result['importable'] and
                result['has_required_methods'] and
                len(result['errors']) == 0
            )

        except Exception as e:
            result['errors'].append(f"검증 중 오류 발생: {str(e)}")

        return result

    def _stop_server(self):
        """서버 프로세스 종료"""
        try:
            # 저장된 프로세스가 있으면 종료
            if self.server_process and self.server_process.poll() is None:
                print(f"서버 프로세스 종료 중 (PID: {self.server_process.pid})")
                self.server_process.terminate()

                # 종료 대기
                try:
                    self.server_process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    print("서버가 정상 종료되지 않아 강제 종료합니다")
                    self.server_process.kill()

                self.server_process = None
                print("서버 프로세스 종료 완료")

            # 실행 중인 모든 서버 프로세스 찾아서 종료
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    if proc.info['name'] and 'python' in proc.info['name'].lower():
                        cmdline = proc.info['cmdline']
                        if cmdline and any('server.py' in cmd for cmd in cmdline):
                            print(f"실행 중인 서버 프로세스 발견 (PID: {proc.info['pid']})")
                            proc.terminate()
                            proc.wait(timeout=5)
                            print(f"서버 프로세스 종료 완료 (PID: {proc.info['pid']})")
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.TimeoutExpired):
                    continue

        except Exception as e:
            print(f"서버 종료 중 오류 발생: {str(e)}")

    def get_server_logs(self, lines: int = 50) -> List[str]:
        """
        서버 로그 조회

        Args:
            lines: 조회할 라인 수

        Returns:
            List[str]: 로그 라인들
        """
        log_file = self.server_path / 'server.log'

        if not log_file.exists():
            return ["로그 파일이 존재하지 않습니다"]

        try:
            with open(log_file, 'r', encoding='utf-8') as f:
                all_lines = f.readlines()
                return all_lines[-lines:] if len(all_lines) > lines else all_lines
        except Exception as e:
            return [f"로그 읽기 실패: {str(e)}"]

    def cleanup(self):
        """리소스 정리"""
        self._stop_server()


# 사용 예시
if __name__ == '__main__':
    # Deployer 초기화
    deployer = StrategyDeployer()

    # 배포 상태 확인
    status = deployer.check_deployment_status()
    print("\n=== 배포 상태 ===")
    print(f"서버 실행 중: {status['server_running']}")
    print(f"서버 PID: {status['server_pid']}")
    print(f"등록된 전략 수: {status['strategies_count']}")
    print(f"전략 목록: {status['registered_strategies']}")

    # 전략 검증
    if status['registered_strategies']:
        strategy_code = status['registered_strategies'][0]
        validation = deployer.validate_strategy(strategy_code)
        print(f"\n=== {strategy_code} 검증 결과 ===")
        print(f"유효성: {validation['valid']}")
        print(f"오류: {validation['errors']}")
        print(f"경고: {validation['warnings']}")

    # 정리
    deployer.cleanup()
