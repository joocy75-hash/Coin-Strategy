# TradingView Strategy Research Lab - Implementation Roadmap

**프로젝트 상태**: Phase 3 완료 (2026-01-04)
**다음 단계**: Phase 4 및 시스템 통합

---

## 📋 작업 체크리스트 필수 지침

**⚠️ 중요: 모든 작업자는 다음 원칙을 반드시 준수**

### 작업 시작 전
- [ ] 이전 작업자의 완료 보고서 읽기 (`PHASE*_SUMMARY.md`)
- [ ] 현재 코드베이스 상태 확인 (`git status`, 최근 커밋)
- [ ] 관련 테스트 실행하여 현재 동작 확인
- [ ] 작업 브랜치 생성 (예: `feature/phase4-llm-converter`)

### 작업 중
- [ ] 코드 작성 시 즉시 docstring 및 type hints 추가
- [ ] 30분마다 작업 내용 간단 메모
- [ ] 새 함수/클래스 작성 시 즉시 간단한 테스트 코드 작성
- [ ] 막히는 부분은 TODO 주석으로 표시하고 문서화

### 작업 완료 후 (필수!)
- [ ] **테스트 작성 및 실행** (최소 2개 이상)
- [ ] **문서 업데이트** (README, API 문서)
- [ ] **`__init__.py` 업데이트** (새로운 모듈 export)
- [ ] **작업 완료 보고서 작성** (`PHASE*_SUMMARY.md` 또는 `WORK_LOG_YYYYMMDD.md`)
- [ ] **Git 커밋 및 푸시**
  ```bash
  git add .
  git commit -m "feat: [작업 내용 요약]"
  git push origin [브랜치명]
  ```
- [ ] **인수인계 문서 작성** (다음 작업자를 위한 가이드)

---

## 🎯 Phase 4: LLM 기반 복잡한 전략 변환

**목표**: 복잡도 0.3 이상의 전략을 LLM을 사용하여 변환
**우선순위**: 높음
**예상 소요 시간**: 2-3주
**담당자**: [미지정]

### 4.1 LLM Converter 기본 구조 (Week 1, Day 1-3)

**목표**: Claude API를 사용한 기본 LLM 변환기 구현

#### 파일 생성
```
strategy-research-lab/src/converter/
├── llm_converter.py              [NEW] 메인 LLM 변환기
├── llm_prompt_builder.py         [NEW] 프롬프트 생성
├── llm_response_parser.py        [NEW] LLM 응답 파싱
└── llm_validator.py              [NEW] LLM 출력 검증
```

#### 4.1.1 작업: LLM Converter 기본 클래스 구현

**파일**: `src/converter/llm_converter.py`

**구현 내용**:
```python
class LLMConverter:
    """
    LLM 기반 Pine Script to Python 변환기.

    복잡도 0.3-1.0 전략에 사용.
    """

    def __init__(self, api_key: str = None, model: str = "claude-sonnet-4-5"):
        """
        Args:
            api_key: Anthropic API key (환경변수에서 가져올 수도 있음)
            model: 사용할 Claude 모델
        """
        pass

    async def convert(self, ast: PineAST) -> GeneratedCode:
        """
        LLM을 사용하여 Pine Script AST를 Python으로 변환.

        Steps:
        1. AST 정보를 LLM 프롬프트로 변환
        2. Claude API 호출
        3. 응답 파싱 및 검증
        4. Python 코드 반환
        """
        pass

    async def _call_llm(self, prompt: str) -> str:
        """Claude API 호출"""
        pass

    def _validate_output(self, code: str) -> ValidationResult:
        """생성된 코드 검증"""
        pass
```

**체크리스트**:
- [ ] `LLMConverter` 클래스 기본 구조 구현
- [ ] Anthropic SDK 통합 (`pip install anthropic`)
- [ ] 환경변수에서 API 키 읽기 (`ANTHROPIC_API_KEY`)
- [ ] 기본 프롬프트 템플릿 작성
- [ ] 간단한 테스트 (mock API 응답 사용)
- [ ] 에러 핸들링 (API 실패, 타임아웃 등)
- [ ] 문서화: docstring 작성
- [ ] **테스트 파일 작성**: `test_llm_converter.py`
- [ ] **Git 커밋**: `git commit -m "feat: implement LLM converter base class"`

#### 4.1.2 작업: Prompt Builder 구현

**파일**: `src/converter/llm_prompt_builder.py`

**구현 내용**:
```python
class LLMPromptBuilder:
    """LLM을 위한 프롬프트 생성기"""

    def build_conversion_prompt(self, ast: PineAST) -> str:
        """
        AST 정보를 LLM 프롬프트로 변환.

        프롬프트 구조:
        1. 작업 설명 (Pine → Python 변환)
        2. Pine Script 원본 코드
        3. AST 메타데이터 (복잡도, 인디케이터 등)
        4. 출력 형식 지정 (Python class 구조)
        5. 제약사항 및 요구사항
        """
        pass

    def build_verification_prompt(self, original_pine: str, python_code: str) -> str:
        """검증용 프롬프트 생성"""
        pass
```

**프롬프트 템플릿 예시**:
```
You are an expert in converting TradingView Pine Script to Python.

Convert the following Pine Script strategy to Python:

Pine Script Code:
```pine
[원본 코드]
```

Strategy Metadata:
- Name: [이름]
- Complexity: [복잡도]
- Indicators: [사용된 인디케이터]
- Inputs: [입력 파라미터]

Requirements:
1. Generate a Python class that inherits from Strategy
2. Implement __init__ and generate_signal methods
3. Use IndicatorMapper for technical indicators
4. Include proper error handling
5. Add type hints and docstrings

Output only the Python code, no explanations.
```

**체크리스트**:
- [ ] `LLMPromptBuilder` 클래스 구현
- [ ] 기본 변환 프롬프트 템플릿 작성
- [ ] AST 메타데이터 포맷팅 함수
- [ ] 검증 프롬프트 템플릿
- [ ] 프롬프트 최적화 (토큰 수 최소화)
- [ ] 테스트: 다양한 AST로 프롬프트 생성 확인
- [ ] **Git 커밋**: `git commit -m "feat: implement LLM prompt builder"`

#### 4.1.3 작업: Response Parser 구현

**파일**: `src/converter/llm_response_parser.py`

**구현 내용**:
```python
class LLMResponseParser:
    """LLM 응답 파싱 및 정리"""

    def parse_python_code(self, llm_response: str) -> str:
        """
        LLM 응답에서 Python 코드만 추출.

        처리:
        1. ```python ... ``` 코드 블록 추출
        2. 불필요한 설명 제거
        3. 코드 포매팅
        """
        pass

    def extract_metadata(self, llm_response: str) -> Dict:
        """응답에서 메타데이터 추출 (있다면)"""
        pass
```

**체크리스트**:
- [ ] 코드 블록 추출 로직 구현
- [ ] 정규표현식 패턴 작성
- [ ] 다양한 응답 형식 처리
- [ ] 에러 케이스 처리 (코드 없음, 잘못된 형식 등)
- [ ] 테스트: 실제 Claude 응답 샘플로 테스트
- [ ] **Git 커밋**: `git commit -m "feat: implement LLM response parser"`

#### 4.1.4 작업: LLM Validator 구현

**파일**: `src/converter/llm_validator.py`

**구현 내용**:
```python
class LLMValidator:
    """LLM 생성 코드 검증"""

    def validate(self, python_code: str, original_ast: PineAST) -> ValidationResult:
        """
        생성된 코드 검증.

        검증 항목:
        1. Python 문법 검증 (ast.parse)
        2. 필수 메서드 존재 확인 (__init__, generate_signal)
        3. 인디케이터 사용 확인
        4. 입력 파라미터 일치 확인
        """
        pass

    def check_required_methods(self, code: str) -> List[str]:
        """필수 메서드 존재 확인"""
        pass

    def check_indicators(self, code: str, expected: List[str]) -> bool:
        """인디케이터 사용 확인"""
        pass
```

**체크리스트**:
- [ ] 문법 검증 구현
- [ ] 필수 메서드 체크
- [ ] 인디케이터 매핑 확인
- [ ] 파라미터 일치 확인
- [ ] 상세한 에러 메시지
- [ ] 테스트: 유효/무효 코드 샘플
- [ ] **Git 커밋**: `git commit -m "feat: implement LLM validator"`

**Week 1 완료 시 체크**:
- [ ] 4개 파일 모두 생성 및 구현
- [ ] 통합 테스트 작성 및 실행
- [ ] 간단한 전략으로 end-to-end 테스트
- [ ] API 사용량 모니터링 코드 추가
- [ ] `PHASE4_WEEK1_SUMMARY.md` 작성
- [ ] **Git 푸시**: `git push origin feature/phase4-llm-converter`

---

### 4.2 Hybrid Converter (Week 1, Day 4-5)

**목표**: Rule-based + LLM 하이브리드 변환

#### 파일 생성
```
strategy-research-lab/src/converter/
├── hybrid_converter.py           [NEW] 하이브리드 변환기
└── conversion_strategy.py        [NEW] 변환 전략 선택 로직
```

#### 4.2.1 작업: Conversion Strategy 구현

**파일**: `src/converter/conversion_strategy.py`

**구현 내용**:
```python
class ConversionStrategy(Enum):
    """변환 전략"""
    RULE_BASED = "rule_based"      # 복잡도 < 0.3
    HYBRID = "hybrid"              # 복잡도 0.3-0.7
    LLM_ONLY = "llm_only"          # 복잡도 > 0.7

class StrategySelector:
    """최적 변환 전략 선택"""

    def select_strategy(self, ast: PineAST) -> ConversionStrategy:
        """
        AST 복잡도 기반 변환 전략 선택.

        규칙:
        - < 0.3: RULE_BASED (빠르고 저렴)
        - 0.3-0.7: HYBRID (Rule + LLM 검증)
        - > 0.7: LLM_ONLY (완전 LLM)
        """
        pass
```

**체크리스트**:
- [ ] `ConversionStrategy` enum 정의
- [ ] `StrategySelector` 클래스 구현
- [ ] 복잡도 임계값 설정 (config)
- [ ] 테스트: 다양한 복잡도 전략 테스트
- [ ] **Git 커밋**: `git commit -m "feat: implement conversion strategy selector"`

#### 4.2.2 작업: Hybrid Converter 구현

**파일**: `src/converter/hybrid_converter.py`

**구현 내용**:
```python
class HybridConverter:
    """Rule-based + LLM 하이브리드 변환기"""

    def __init__(self):
        self.rule_converter = RuleBasedConverter()
        self.llm_converter = LLMConverter()
        self.validator = LLMValidator()

    async def convert(self, ast: PineAST) -> GeneratedCode:
        """
        하이브리드 변환 전략.

        Steps:
        1. Rule-based로 시도
        2. 실패하면 LLM으로 재시도
        3. 성공하면 LLM으로 검증
        4. 검증 실패 시 LLM으로 재생성
        """
        pass
```

**체크리스트**:
- [ ] `HybridConverter` 클래스 구현
- [ ] Rule-based 우선 시도 로직
- [ ] 실패 시 LLM fallback
- [ ] 성공 시 LLM 검증
- [ ] 재시도 로직 (최대 3회)
- [ ] 비용/시간 메트릭 수집
- [ ] 테스트: 중간 복잡도 전략
- [ ] **Git 커밋**: `git commit -m "feat: implement hybrid converter"`

**Week 1 Day 4-5 완료 시 체크**:
- [ ] 하이브리드 변환 파이프라인 작동
- [ ] 실제 전략으로 테스트 (복잡도 0.3-0.7)
- [ ] 비용 효율성 분석
- [ ] **Git 푸시**

---

### 4.3 통합 Converter Facade (Week 2, Day 1-2)

**목표**: 사용자가 복잡도 신경 안 쓰고 사용할 수 있는 통합 인터페이스

#### 파일 수정
```
strategy-research-lab/src/converter/
├── unified_converter.py          [NEW] 통합 변환기 facade
└── __init__.py                   [MODIFY] unified_converter export
```

#### 4.3.1 작업: Unified Converter 구현

**파일**: `src/converter/unified_converter.py`

**구현 내용**:
```python
class UnifiedConverter:
    """
    모든 변환 전략을 통합한 Facade 클래스.

    사용자는 복잡도를 신경 쓰지 않고 이 클래스만 사용.
    """

    def __init__(self, api_key: str = None):
        self.strategy_selector = StrategySelector()
        self.rule_converter = RuleBasedConverter()
        self.llm_converter = LLMConverter(api_key)
        self.hybrid_converter = HybridConverter()

    async def convert(
        self,
        pine_code: str,
        force_strategy: ConversionStrategy = None
    ) -> GeneratedCode:
        """
        Pine Script를 Python으로 변환.

        자동으로 최적 전략 선택하여 변환.

        Args:
            pine_code: Pine Script 소스 코드
            force_strategy: 강제로 특정 전략 사용 (테스트용)

        Returns:
            GeneratedCode with metadata (사용된 전략, 비용 등)
        """
        # 1. Parse to AST
        ast = parse_pine_script(pine_code)

        # 2. Select strategy
        strategy = force_strategy or self.strategy_selector.select_strategy(ast)

        # 3. Convert
        if strategy == ConversionStrategy.RULE_BASED:
            return self.rule_converter.convert(ast)
        elif strategy == ConversionStrategy.HYBRID:
            return await self.hybrid_converter.convert(ast)
        else:  # LLM_ONLY
            return await self.llm_converter.convert(ast)

    def get_conversion_cost_estimate(self, pine_code: str) -> Dict:
        """변환 비용 예상"""
        pass
```

**체크리스트**:
- [ ] `UnifiedConverter` 클래스 구현
- [ ] 자동 전략 선택 로직
- [ ] 비용 예측 기능
- [ ] 진행 상황 콜백 (선택적)
- [ ] 에러 핸들링 및 재시도
- [ ] **`__init__.py` 업데이트**
- [ ] 테스트: 다양한 복잡도 전략 자동 선택
- [ ] **사용 예제 작성** (README)
- [ ] **Git 커밋**: `git commit -m "feat: implement unified converter facade"`

**사용 예제**:
```python
from converter import UnifiedConverter

converter = UnifiedConverter(api_key="...")
result = await converter.convert(pine_code)

print(f"Strategy used: {result.strategy_used}")
print(f"Cost: ${result.cost:.4f}")
print(f"Code length: {len(result.full_code)}")
```

**Week 2 Day 1-2 완료 시 체크**:
- [ ] 통합 인터페이스 완성
- [ ] 모든 전략 통합 테스트
- [ ] 사용 예제 및 문서 작성
- [ ] **Git 푸시**

---

### 4.4 캐싱 및 최적화 (Week 2, Day 3-5)

**목표**: 중복 변환 방지 및 성능 최적화

#### 파일 생성
```
strategy-research-lab/src/converter/
├── conversion_cache.py           [NEW] 변환 결과 캐싱
└── cost_optimizer.py             [NEW] 비용 최적화
```

#### 4.4.1 작업: Conversion Cache 구현

**파일**: `src/converter/conversion_cache.py`

**구현 내용**:
```python
class ConversionCache:
    """변환 결과 캐싱"""

    def __init__(self, cache_dir: str = ".cache/conversions"):
        """
        Args:
            cache_dir: 캐시 파일 저장 디렉토리
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def get_cache_key(self, pine_code: str) -> str:
        """Pine 코드의 해시 생성 (SHA256)"""
        return hashlib.sha256(pine_code.encode()).hexdigest()

    def get(self, pine_code: str) -> Optional[GeneratedCode]:
        """캐시에서 결과 가져오기"""
        pass

    def set(self, pine_code: str, result: GeneratedCode):
        """결과를 캐시에 저장"""
        pass

    def clear(self, older_than_days: int = 30):
        """오래된 캐시 정리"""
        pass
```

**체크리스트**:
- [ ] `ConversionCache` 클래스 구현
- [ ] 파일 기반 캐싱 (JSON)
- [ ] 해시 기반 중복 검사
- [ ] TTL (Time To Live) 기능
- [ ] 캐시 통계 (hit rate)
- [ ] 테스트: 캐시 hit/miss
- [ ] **Git 커밋**: `git commit -m "feat: implement conversion cache"`

#### 4.4.2 작업: Cost Optimizer 구현

**파일**: `src/converter/cost_optimizer.py`

**구현 내용**:
```python
class CostOptimizer:
    """LLM API 비용 최적화"""

    def optimize_prompt(self, prompt: str) -> str:
        """
        프롬프트 최적화하여 토큰 수 감소.

        방법:
        1. 불필요한 공백 제거
        2. 주석 제거
        3. 중복 설명 제거
        """
        pass

    def estimate_cost(self, prompt: str, model: str) -> float:
        """
        API 호출 예상 비용 계산.

        토큰 수 * 모델별 가격
        """
        pass

    def get_cheapest_strategy(self, ast: PineAST) -> ConversionStrategy:
        """
        비용이 가장 저렴한 전략 선택.

        고려사항:
        - Rule-based: $0 (무료)
        - LLM: 토큰 수 기반
        - Hybrid: Rule 실패 확률 * LLM 비용
        """
        pass
```

**체크리스트**:
- [ ] 토큰 수 계산 (`tiktoken` 사용)
- [ ] 모델별 가격표 (`claude-sonnet-4-5`: $3/MTok 입력)
- [ ] 비용 예측 함수
- [ ] 최적 전략 추천
- [ ] 비용 추적 로깅
- [ ] 테스트: 다양한 프롬프트 비용 계산
- [ ] **Git 커밋**: `git commit -m "feat: implement cost optimizer"`

**Week 2 Day 3-5 완료 시 체크**:
- [ ] 캐싱 시스템 작동
- [ ] 비용 최적화 적용
- [ ] 성능 벤치마크 (변환 속도, 캐시 hit rate)
- [ ] **`PHASE4_WEEK2_SUMMARY.md` 작성**
- [ ] **Git 푸시**

---

### 4.5 통합 테스트 및 문서화 (Week 3)

#### 4.5.1 작업: 종합 테스트 작성

**파일**: `test_phase4_complete.py`

**테스트 시나리오**:
1. LOW 복잡도 → Rule-based
2. MEDIUM 복잡도 → Hybrid
3. HIGH 복잡도 → LLM
4. 캐시 hit/miss
5. 비용 추적
6. 에러 핸들링

**체크리스트**:
- [ ] 10개 이상의 실제 전략으로 테스트
- [ ] 각 전략별 성공률 측정
- [ ] 비용 및 시간 메트릭 수집
- [ ] 에러 케이스 테스트
- [ ] **테스트 결과 문서화**
- [ ] **Git 커밋**: `git commit -m "test: add comprehensive Phase 4 tests"`

#### 4.5.2 작업: API 문서 작성

**파일**: `PHASE4_README.md`

**내용**:
- 개요 및 아키텍처
- 설치 및 설정 (API 키 등)
- 사용 예제 (코드 샘플)
- API 레퍼런스
- 비용 가이드
- FAQ 및 문제 해결

**체크리스트**:
- [ ] README 작성
- [ ] 코드 예제 10개 이상
- [ ] API 레퍼런스 (모든 클래스/메서드)
- [ ] 비용 계산 예제
- [ ] 문제 해결 가이드
- [ ] **Git 커밋**: `git commit -m "docs: add Phase 4 comprehensive documentation"`

#### 4.5.3 작업: Phase 4 Summary

**파일**: `PHASE4_SUMMARY.md`

**내용**:
- 구현 개요
- 아키텍처 다이어그램
- 성능 벤치마크
- 비용 분석
- 알려진 이슈
- 향후 개선 사항

**Week 3 완료 시 체크**:
- [ ] 모든 테스트 통과 (90% 이상)
- [ ] 문서 완성
- [ ] 코드 리뷰 및 리팩토링
- [ ] **`PHASE4_COMPLETE.md` 작성**
- [ ] **Git 푸시 및 PR 생성**

---

## 🔗 Phase 5: 백테스트 시스템 통합

**목표**: 변환된 전략을 자동으로 백테스트
**우선순위**: 중간
**예상 소요 시간**: 2주

### 5.1 백테스트 엔진 통합 (Week 1)

#### 파일 생성
```
strategy-research-lab/src/
├── backtest/
│   ├── __init__.py
│   ├── backtest_engine.py        [NEW] 백테스트 엔진
│   ├── data_provider.py          [NEW] 데이터 제공
│   └── performance_metrics.py    [NEW] 성능 지표 계산
```

#### 5.1.1 작업: Backtest Engine 구현

**파일**: `src/backtest/backtest_engine.py`

**구현 내용**:
```python
class BacktestEngine:
    """전략 백테스트 엔진"""

    def __init__(self, initial_capital: float = 10000):
        self.initial_capital = initial_capital

    def run(
        self,
        strategy_code: str,  # 생성된 Python 코드
        symbol: str = "BTC/USDT",
        timeframe: str = "1h",
        start_date: str = "2023-01-01",
        end_date: str = "2024-01-01"
    ) -> BacktestResult:
        """
        전략 백테스트 실행.

        Steps:
        1. 전략 코드를 동적으로 로드
        2. 과거 데이터 가져오기
        3. 시뮬레이션 실행
        4. 성능 지표 계산
        """
        pass
```

**체크리스트**:
- [ ] 동적 코드 실행 (exec/importlib)
- [ ] 안전한 샌드박스 환경
- [ ] 포지션 관리
- [ ] 주문 실행 시뮬레이션
- [ ] 슬리피지 및 수수료 계산
- [ ] 테스트: 간단한 MA 전략
- [ ] **Git 커밋**: `git commit -m "feat: implement backtest engine"`

#### 5.1.2 작업: Data Provider 구현

**파일**: `src/backtest/data_provider.py`

**구현 내용**:
```python
class DataProvider:
    """백테스트용 과거 데이터 제공"""

    def get_ohlcv(
        self,
        symbol: str,
        timeframe: str,
        start: str,
        end: str
    ) -> pd.DataFrame:
        """
        OHLCV 데이터 가져오기.

        소스:
        1. 로컬 캐시 확인
        2. 없으면 Binance API에서 다운로드
        3. 캐시에 저장
        """
        pass
```

**체크리스트**:
- [ ] Binance API 통합 (`ccxt`)
- [ ] 데이터 캐싱 (parquet)
- [ ] 타임프레임 변환
- [ ] 데이터 검증
- [ ] 테스트: 실제 데이터 다운로드
- [ ] **Git 커밋**: `git commit -m "feat: implement data provider"`

#### 5.1.3 작업: Performance Metrics 구현

**파일**: `src/backtest/performance_metrics.py`

**구현 내용**:
```python
class PerformanceMetrics:
    """백테스트 성능 지표 계산"""

    def calculate(self, trades: List[Dict], equity_curve: pd.Series) -> Dict:
        """
        성능 지표 계산.

        지표:
        - Total Return (%)
        - Sharpe Ratio
        - Max Drawdown (%)
        - Win Rate (%)
        - Profit Factor
        - Average Trade (%)
        - Number of Trades
        """
        pass
```

**체크리스트**:
- [ ] 수익률 계산
- [ ] 샤프 비율
- [ ] 최대 낙폭 (MDD)
- [ ] 승률
- [ ] 손익비
- [ ] 테스트: 샘플 거래로 계산
- [ ] **Git 커밋**: `git commit -m "feat: implement performance metrics"`

**Week 1 완료 시 체크**:
- [ ] 백테스트 파이프라인 작동
- [ ] 실제 전략으로 백테스트 실행
- [ ] 성능 지표 정확성 검증
- [ ] **`PHASE5_WEEK1_SUMMARY.md` 작성**
- [ ] **Git 푸시**

---

### 5.2 자동 백테스트 파이프라인 (Week 2)

#### 파일 생성
```
strategy-research-lab/src/
├── pipeline/
│   ├── __init__.py
│   ├── auto_backtest.py          [NEW] 자동 백테스트
│   └── report_generator.py       [NEW] 리포트 생성
```

#### 5.2.1 작업: Auto Backtest 구현

**파일**: `src/pipeline/auto_backtest.py`

**구현 내용**:
```python
class AutoBacktest:
    """변환 후 자동 백테스트 파이프라인"""

    async def convert_and_backtest(
        self,
        pine_code: str,
        symbol: str = "BTC/USDT",
        timeframe: str = "1h"
    ) -> BacktestReport:
        """
        Pine Script를 변환하고 즉시 백테스트.

        Steps:
        1. Pine → Python 변환 (UnifiedConverter)
        2. 백테스트 실행 (BacktestEngine)
        3. 리포트 생성 (ReportGenerator)
        4. 결과 저장 (DB 및 파일)
        """
        pass
```

**체크리스트**:
- [ ] Converter + Backtest 통합
- [ ] 병렬 백테스트 (여러 타임프레임)
- [ ] 결과 DB 저장
- [ ] 에러 핸들링
- [ ] 진행 상황 로깅
- [ ] 테스트: end-to-end 파이프라인
- [ ] **Git 커밋**: `git commit -m "feat: implement auto backtest pipeline"`

#### 5.2.2 작업: Report Generator 구현

**파일**: `src/pipeline/report_generator.py`

**구현 내용**:
```python
class ReportGenerator:
    """백테스트 리포트 생성"""

    def generate_html(self, result: BacktestResult) -> str:
        """HTML 리포트 생성"""
        pass

    def generate_pdf(self, result: BacktestResult) -> bytes:
        """PDF 리포트 생성"""
        pass

    def plot_equity_curve(self, equity: pd.Series) -> str:
        """자본 곡선 플롯 (base64 이미지)"""
        pass
```

**체크리스트**:
- [ ] HTML 템플릿 (Jinja2)
- [ ] 차트 생성 (plotly/matplotlib)
- [ ] PDF 생성 (weasyprint)
- [ ] 성능 지표 테이블
- [ ] 거래 내역 테이블
- [ ] 테스트: 샘플 리포트 생성
- [ ] **Git 커밋**: `git commit -m "feat: implement report generator"`

**Week 2 완료 시 체크**:
- [ ] 완전 자동화 파이프라인 완성
- [ ] 리포트 생성 작동
- [ ] 10개 전략으로 테스트
- [ ] **`PHASE5_SUMMARY.md` 작성**
- [ ] **Git 푸시**

---

## 🚀 Phase 6: 프로덕션 배포 준비

**목표**: 실제 서비스 배포 가능한 상태
**우선순위**: 높음
**예상 소요 시간**: 1주

### 6.1 Docker 컨테이너화

#### 파일 생성
```
strategy-research-lab/
├── Dockerfile                    [MODIFY] Phase 3/4/5 포함
├── docker-compose.yml            [MODIFY] 서비스 추가
└── .dockerignore                 [MODIFY]
```

**체크리스트**:
- [ ] Dockerfile 업데이트 (새 의존성)
- [ ] docker-compose 서비스 추가 (converter, backtest)
- [ ] 환경변수 설정 (API 키 등)
- [ ] 헬스체크 엔드포인트
- [ ] 테스트: 로컬 Docker 빌드 및 실행
- [ ] **Git 커밋**: `git commit -m "chore: update Docker configuration"`

### 6.2 API 엔드포인트 추가

#### 파일 수정
```
strategy-research-lab/src/api/
├── main.py                       [MODIFY] 새 엔드포인트 추가
└── routes/
    └── converter.py              [NEW] 변환 API
```

**새 API 엔드포인트**:
```python
@app.post("/api/convert")
async def convert_strategy(pine_code: str):
    """Pine Script를 Python으로 변환"""
    pass

@app.post("/api/convert-and-backtest")
async def convert_and_backtest(
    pine_code: str,
    symbol: str = "BTC/USDT",
    timeframe: str = "1h"
):
    """변환 후 즉시 백테스트"""
    pass

@app.get("/api/conversion-status/{task_id}")
async def get_status(task_id: str):
    """변환 작업 상태 조회"""
    pass
```

**체크리스트**:
- [ ] FastAPI 라우터 추가
- [ ] 비동기 처리 (Celery or background tasks)
- [ ] 요청 검증 (Pydantic models)
- [ ] 에러 핸들링
- [ ] API 문서 업데이트
- [ ] 테스트: Postman/curl
- [ ] **Git 커밋**: `git commit -m "feat: add converter API endpoints"`

### 6.3 모니터링 및 로깅

#### 파일 생성
```
strategy-research-lab/src/
├── monitoring/
│   ├── __init__.py
│   ├── metrics.py                [NEW] 메트릭 수집
│   └── logger.py                 [NEW] 로깅 설정
```

**체크리스트**:
- [ ] Prometheus 메트릭 (변환 수, 성공률, 비용)
- [ ] 구조화된 로깅 (JSON)
- [ ] 에러 추적 (Sentry)
- [ ] 성능 프로파일링
- [ ] 테스트: 메트릭 수집 확인
- [ ] **Git 커밯**: `git commit -m "feat: add monitoring and logging"`

**Phase 6 완료 시 체크**:
- [ ] Docker 빌드 성공
- [ ] API 엔드포인트 작동
- [ ] 모니터링 대시보드 구성
- [ ] **`DEPLOYMENT_GUIDE.md` 업데이트**
- [ ] **Git 푸시**

---

## 🧪 Phase 7: 품질 보증 및 최적화

**목표**: 코드 품질 및 성능 최적화
**우선순위**: 중간
**예상 소요 시간**: 1주

### 7.1 코드 품질 개선

**체크리스트**:
- [ ] **Linting**: `ruff` 또는 `pylint` 실행 및 수정
- [ ] **Type Checking**: `mypy` 실행, 모든 경고 해결
- [ ] **Code Coverage**: 80% 이상 달성
- [ ] **Docstring Coverage**: 100% (모든 public API)
- [ ] **Security Scan**: `bandit` 실행
- [ ] **Dependency Audit**: `safety check`
- [ ] **Git 커밋**: `git commit -m "refactor: improve code quality"`

### 7.2 성능 최적화

**체크리스트**:
- [ ] 프로파일링 (`cProfile`, `line_profiler`)
- [ ] 병목 지점 식별 및 최적화
- [ ] 메모리 사용량 최적화
- [ ] 데이터베이스 쿼리 최적화 (인덱스)
- [ ] 캐싱 전략 개선
- [ ] 벤치마크 결과 문서화
- [ ] **Git 커밋**: `git commit -m "perf: optimize critical paths"`

### 7.3 문서화 완성

**체크리스트**:
- [ ] **Architecture Guide**: 시스템 아키텍처 다이어그램
- [ ] **Developer Guide**: 새 개발자를 위한 가이드
- [ ] **API Documentation**: OpenAPI/Swagger 완성
- [ ] **User Guide**: 최종 사용자 가이드
- [ ] **FAQ**: 자주 묻는 질문 20개 이상
- [ ] **Changelog**: 모든 변경사항 기록
- [ ] **Git 커밋**: `git commit -m "docs: complete documentation"`

**Phase 7 완료 시 체크**:
- [ ] 모든 품질 메트릭 목표 달성
- [ ] 성능 벤치마크 개선 (20% 이상)
- [ ] 문서 완성도 100%
- [ ] **`QUALITY_REPORT.md` 작성**
- [ ] **Git 푸시**

---

## 📊 Phase 8: 데이터 분석 및 인사이트

**목표**: 수집된 전략 분석 및 인사이트 도출
**우선순위**: 낮음
**예상 소요 시간**: 2주

### 8.1 전략 통계 분석

#### 파일 생성
```
strategy-research-lab/src/analysis/
├── __init__.py
├── strategy_analyzer.py          [NEW] 전략 통계
├── indicator_popularity.py       [NEW] 인디케이터 인기도
└── performance_correlation.py    [NEW] 성능 상관관계
```

**분석 항목**:
- 가장 많이 사용되는 인디케이터
- 복잡도 분포
- 승률 vs 복잡도 상관관계
- 타임프레임별 성능
- 인디케이터 조합 패턴

**체크리스트**:
- [ ] 데이터 집계 쿼리
- [ ] 통계 분석 (pandas, numpy)
- [ ] 시각화 (matplotlib, seaborn)
- [ ] 인사이트 도출
- [ ] 리포트 생성
- [ ] **Git 커밋**: `git commit -m "feat: add strategy analysis"`

### 8.2 ML 기반 전략 추천 (선택적)

**목표**: 유사한 성공 전략 추천

**체크리스트**:
- [ ] 특징 벡터 생성 (인디케이터, 복잡도 등)
- [ ] 유사도 계산 (cosine similarity)
- [ ] 추천 알고리즘 구현
- [ ] API 엔드포인트 추가
- [ ] 테스트 및 검증
- [ ] **Git 커밋**: `git commit -m "feat: add strategy recommendation"`

---

## 🔄 지속적 유지보수 체크리스트

### 매주 수행
- [ ] 의존성 업데이트 확인 (`pip list --outdated`)
- [ ] 보안 취약점 스캔 (`safety check`)
- [ ] 로그 검토 (에러, 경고)
- [ ] 성능 메트릭 확인
- [ ] 백업 확인 (DB, 코드)

### 매월 수행
- [ ] 전체 테스트 스위트 실행
- [ ] 코드 커버리지 확인
- [ ] 문서 업데이트
- [ ] 리팩토링 기회 식별
- [ ] 기술 부채 정리

### 분기별 수행
- [ ] 아키텍처 리뷰
- [ ] 성능 벤치마크
- [ ] 사용자 피드백 반영
- [ ] 로드맵 업데이트

---

## 📝 작업 완료 보고서 템플릿

매 작업 완료 시 다음 형식으로 보고서 작성:

**파일명**: `WORK_LOG_YYYYMMDD_[작업명].md`

**내용**:
```markdown
# 작업 완료 보고서

**날짜**: YYYY-MM-DD
**작업자**: [이름]
**작업 시간**: [시작 - 종료]

## 작업 내용

### 구현한 기능
- [기능 1]
- [기능 2]
- ...

### 생성/수정한 파일
- `파일명1` - [설명]
- `파일명2` - [설명]
- ...

### 테스트 결과
- 테스트 파일: `test_xxx.py`
- 통과/실패: X/Y
- 커버리지: ZZ%

## 이슈 및 해결

### 발생한 문제
1. [문제 1] - [해결 방법]
2. [문제 2] - [해결 방법]

### 미해결 이슈
- [ ] [이슈 1] - [다음 작업자를 위한 힌트]

## 다음 작업자를 위한 메모

- [중요한 사항 1]
- [중요한 사항 2]
- [참고 문서 링크]

## Git 정보

- 브랜치: [브랜치명]
- 커밋 해시: [커밋 해시]
- PR: [PR 링크]

## 체크리스트

- [x] 코드 작성 완료
- [x] 테스트 작성 및 실행
- [x] 문서 업데이트
- [x] Git 커밋 및 푸시
- [ ] 코드 리뷰 요청
```

---

## 🎯 최종 목표 및 성공 지표

### Phase 4 성공 기준
- [ ] 복잡도 0.3-1.0 전략 변환 성공률 > 85%
- [ ] LLM API 비용 < $0.10 per conversion
- [ ] 평균 변환 시간 < 30초
- [ ] 캐시 hit rate > 60%

### Phase 5 성공 기준
- [ ] 백테스트 성공률 > 90%
- [ ] 백테스트 속도 < 5초 (1년 데이터)
- [ ] 성능 지표 정확도 > 95%

### Phase 6 성공 기준
- [ ] API 응답 시간 < 2초 (P95)
- [ ] 시스템 가용성 > 99%
- [ ] Docker 빌드 < 5분

### 전체 프로젝트 성공 기준
- [ ] 1000개 이상의 전략 수집
- [ ] 100개 이상의 전략 변환 및 백테스트
- [ ] 상위 10개 전략 식별
- [ ] 완전 자동화 파이프라인 구축

---

**작성일**: 2026-01-04
**최종 업데이트**: 2026-01-04
**작성자**: Claude Sonnet 4.5

**다음 업데이트 예정일**: Phase 4 완료 후
