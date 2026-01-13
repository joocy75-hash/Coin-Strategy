#!/usr/bin/env python3
"""
FinBERT 금융 감성 분석기

전략 설명문의 과대광고 및 감성을 분석합니다.
Hugging Face의 ProsusAI/finbert 모델을 사용합니다.

Model: https://huggingface.co/ProsusAI/finbert
"""

import re
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum

# Transformers 임포트 시도
try:
    from transformers import AutoTokenizer, AutoModelForSequenceClassification
    import torch
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False
    torch = None


class SentimentLabel(Enum):
    """감성 레이블"""
    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"


@dataclass
class SentimentResult:
    """감성 분석 결과"""
    label: SentimentLabel
    confidence: float
    scores: Dict[str, float] = field(default_factory=dict)


@dataclass
class HypeAnalysisResult:
    """과대광고 분석 결과"""
    success: bool
    
    # 과대광고 점수 (0-100, 높을수록 과대광고)
    hype_score: float = 0.0
    hype_level: str = "low"  # low, medium, high, extreme
    
    # 감성 분석
    overall_sentiment: SentimentLabel = SentimentLabel.NEUTRAL
    sentiment_confidence: float = 0.0
    
    # 세부 분석
    hype_phrases: List[str] = field(default_factory=list)
    warning_signs: List[str] = field(default_factory=list)
    positive_claims: List[str] = field(default_factory=list)
    
    # 문장별 분석
    sentence_analysis: List[Dict[str, Any]] = field(default_factory=list)
    
    # 권장사항
    recommendations: List[str] = field(default_factory=list)
    
    # 에러
    error: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "hype_score": round(self.hype_score, 1),
            "hype_level": self.hype_level,
            "sentiment": {
                "label": self.overall_sentiment.value,
                "confidence": round(self.sentiment_confidence, 3),
            },
            "analysis": {
                "hype_phrases": self.hype_phrases[:10],
                "warning_signs": self.warning_signs[:10],
                "positive_claims": self.positive_claims[:10],
            },
            "sentence_analysis": self.sentence_analysis[:20],
            "recommendations": self.recommendations,
            "error": self.error,
        }


class FinBERTAnalyzer:
    """
    FinBERT 기반 금융 감성 분석기
    
    Features:
    - 전략 설명문 감성 분석
    - 과대광고 탐지
    - 경고 신호 식별
    """
    
    # 과대광고 키워드 (영어)
    HYPE_KEYWORDS_EN = [
        # 수익 관련
        "guaranteed", "100%", "never lose", "always win", "risk-free",
        "easy money", "get rich", "millionaire", "fortune", "wealth",
        "profit machine", "money printer", "cash cow", "gold mine",
        
        # 성과 과장
        "best ever", "unbeatable", "perfect", "flawless", "incredible",
        "amazing", "revolutionary", "breakthrough", "game changer",
        "holy grail", "secret", "hidden", "exclusive",
        
        # 긴급성
        "limited time", "act now", "don't miss", "last chance",
        "hurry", "urgent", "before it's too late",
        
        # 비현실적 수치
        "1000%", "500%", "10x", "100x", "exponential",
    ]
    
    # 과대광고 키워드 (한국어)
    HYPE_KEYWORDS_KR = [
        # 수익 관련
        "보장", "100%", "무손실", "항상 수익", "리스크 없는",
        "쉬운 돈", "부자", "백만장자", "대박", "떼돈",
        
        # 성과 과장
        "최고", "무적", "완벽", "놀라운", "혁명적",
        "비밀", "숨겨진", "독점", "특별한",
        
        # 긴급성
        "한정", "지금 바로", "놓치지", "마지막 기회",
        "서두르", "급함",
    ]
    
    # 경고 신호
    WARNING_SIGNS = [
        # 비현실적 주장
        (r'\b(\d{3,})\s*%', "비현실적인 수익률 주장"),
        (r'never\s+lose|무손실', "손실 없음 주장"),
        (r'guaranteed|보장', "수익 보장 주장"),
        (r'risk[\s-]*free|리스크\s*없', "무위험 주장"),
        
        # 과장된 표현
        (r'best\s+(strategy|indicator)|최고의?\s*(전략|지표)', "최고 주장"),
        (r'holy\s+grail|성배', "성배 표현"),
        (r'secret|비밀', "비밀 전략 주장"),
        
        # 긴급성 유도
        (r'limited\s+time|한정\s*시간', "긴급성 유도"),
        (r'act\s+now|지금\s*바로', "즉시 행동 유도"),
    ]
    
    # 긍정적 주장 패턴
    POSITIVE_CLAIM_PATTERNS = [
        (r'(\d+)\s*%\s*(win|profit|return|수익|승률)', "수익률 주장"),
        (r'(backtest|백테스트).*(\d+)\s*%', "백테스트 결과"),
        (r'(proven|검증)', "검증됨 주장"),
        (r'(tested|테스트).*(\d+)', "테스트 결과"),
    ]
    
    MODEL_NAME = "ProsusAI/finbert"
    
    def __init__(self, use_gpu: bool = False):
        """
        Args:
            use_gpu: GPU 사용 여부
        """
        self.model = None
        self.tokenizer = None
        self.device = "cuda" if use_gpu and torch and torch.cuda.is_available() else "cpu"
        self._model_loaded = False
        
    def _load_model(self):
        """모델 로드 (지연 로딩)"""
        if self._model_loaded or not TRANSFORMERS_AVAILABLE:
            return
            
        try:
            self.tokenizer = AutoTokenizer.from_pretrained(self.MODEL_NAME)
            self.model = AutoModelForSequenceClassification.from_pretrained(self.MODEL_NAME)
            self.model.to(self.device)
            self.model.eval()
            self._model_loaded = True
        except Exception as e:
            print(f"FinBERT 모델 로드 실패: {e}")
    
    def analyze_sentiment(self, text: str) -> SentimentResult:
        """
        텍스트 감성 분석
        
        Args:
            text: 분석할 텍스트
            
        Returns:
            SentimentResult: 감성 분석 결과
        """
        if not TRANSFORMERS_AVAILABLE:
            return SentimentResult(
                label=SentimentLabel.NEUTRAL,
                confidence=0.0,
                scores={"error": "transformers not installed"},
            )
        
        self._load_model()
        
        if not self._model_loaded:
            return SentimentResult(
                label=SentimentLabel.NEUTRAL,
                confidence=0.0,
                scores={"error": "model not loaded"},
            )
        
        try:
            # 토큰화
            inputs = self.tokenizer(
                text,
                return_tensors="pt",
                truncation=True,
                max_length=512,
                padding=True,
            ).to(self.device)
            
            # 추론
            with torch.no_grad():
                outputs = self.model(**inputs)
                probs = torch.softmax(outputs.logits, dim=-1)
            
            # 결과 추출
            scores = probs[0].cpu().numpy()
            labels = ["positive", "negative", "neutral"]
            
            score_dict = {label: float(score) for label, score in zip(labels, scores)}
            max_idx = scores.argmax()
            
            return SentimentResult(
                label=SentimentLabel(labels[max_idx]),
                confidence=float(scores[max_idx]),
                scores=score_dict,
            )
            
        except Exception as e:
            return SentimentResult(
                label=SentimentLabel.NEUTRAL,
                confidence=0.0,
                scores={"error": str(e)},
            )
    
    def analyze_hype(self, text: str) -> HypeAnalysisResult:
        """
        과대광고 분석
        
        Args:
            text: 전략 설명문
            
        Returns:
            HypeAnalysisResult: 과대광고 분석 결과
        """
        if not text or len(text.strip()) < 10:
            return HypeAnalysisResult(
                success=False,
                error="텍스트가 너무 짧습니다."
            )
        
        result = HypeAnalysisResult(success=True)
        
        # 1. 과대광고 키워드 탐지
        text_lower = text.lower()
        
        for keyword in self.HYPE_KEYWORDS_EN + self.HYPE_KEYWORDS_KR:
            if keyword.lower() in text_lower:
                result.hype_phrases.append(keyword)
        
        # 2. 경고 신호 탐지
        for pattern, description in self.WARNING_SIGNS:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                result.warning_signs.append(f"{description}: {matches[0] if isinstance(matches[0], str) else matches[0][0]}")
        
        # 3. 긍정적 주장 탐지
        for pattern, description in self.POSITIVE_CLAIM_PATTERNS:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                result.positive_claims.append(f"{description}")
        
        # 4. 문장별 감성 분석 (FinBERT 사용 가능한 경우)
        sentences = self._split_sentences(text)
        
        positive_count = 0
        negative_count = 0
        neutral_count = 0
        total_confidence = 0
        
        for sentence in sentences[:20]:  # 최대 20문장
            if len(sentence.strip()) < 10:
                continue
                
            sentiment = self.analyze_sentiment(sentence)
            
            result.sentence_analysis.append({
                "text": sentence[:100],
                "sentiment": sentiment.label.value,
                "confidence": round(sentiment.confidence, 3),
            })
            
            if sentiment.label == SentimentLabel.POSITIVE:
                positive_count += 1
            elif sentiment.label == SentimentLabel.NEGATIVE:
                negative_count += 1
            else:
                neutral_count += 1
            
            total_confidence += sentiment.confidence
        
        # 5. 전체 감성 결정
        total_sentences = positive_count + negative_count + neutral_count
        if total_sentences > 0:
            if positive_count > negative_count and positive_count > neutral_count:
                result.overall_sentiment = SentimentLabel.POSITIVE
            elif negative_count > positive_count and negative_count > neutral_count:
                result.overall_sentiment = SentimentLabel.NEGATIVE
            else:
                result.overall_sentiment = SentimentLabel.NEUTRAL
            
            result.sentiment_confidence = total_confidence / total_sentences
        
        # 6. 과대광고 점수 계산
        result.hype_score = self._calculate_hype_score(result)
        result.hype_level = self._get_hype_level(result.hype_score)
        
        # 7. 권장사항 생성
        result.recommendations = self._generate_recommendations(result)
        
        return result
    
    def _split_sentences(self, text: str) -> List[str]:
        """문장 분리"""
        # 간단한 문장 분리 (마침표, 느낌표, 물음표 기준)
        sentences = re.split(r'[.!?]\s+', text)
        return [s.strip() for s in sentences if s.strip()]
    
    def _calculate_hype_score(self, result: HypeAnalysisResult) -> float:
        """과대광고 점수 계산 (0-100)"""
        score = 0.0
        
        # 과대광고 키워드 (각 10점, 최대 40점)
        score += min(len(result.hype_phrases) * 10, 40)
        
        # 경고 신호 (각 15점, 최대 45점)
        score += min(len(result.warning_signs) * 15, 45)
        
        # 과도한 긍정 감성 (최대 15점)
        if result.overall_sentiment == SentimentLabel.POSITIVE:
            if result.sentiment_confidence > 0.8:
                score += 15
            elif result.sentiment_confidence > 0.6:
                score += 10
            else:
                score += 5
        
        return min(score, 100)
    
    def _get_hype_level(self, score: float) -> str:
        """과대광고 수준 결정"""
        if score >= 70:
            return "extreme"
        elif score >= 50:
            return "high"
        elif score >= 25:
            return "medium"
        return "low"
    
    def _generate_recommendations(self, result: HypeAnalysisResult) -> List[str]:
        """권장사항 생성"""
        recommendations = []
        
        if result.hype_score >= 70:
            recommendations.append("⚠️ 이 전략 설명은 과대광고 위험이 매우 높습니다. 신중하게 검토하세요.")
        elif result.hype_score >= 50:
            recommendations.append("⚠️ 과장된 표현이 다수 포함되어 있습니다. 실제 성과를 확인하세요.")
        elif result.hype_score >= 25:
            recommendations.append("ℹ️ 일부 과장된 표현이 있습니다. 백테스트 결과를 확인하세요.")
        
        if "보장" in str(result.hype_phrases) or "guaranteed" in str(result.hype_phrases).lower():
            recommendations.append("❌ '보장'이라는 표현은 투자에서 불가능합니다. 주의하세요.")
        
        if any("100%" in s or "무손실" in s for s in result.warning_signs):
            recommendations.append("❌ 100% 수익률이나 무손실은 불가능합니다.")
        
        if result.overall_sentiment == SentimentLabel.POSITIVE and result.sentiment_confidence > 0.8:
            recommendations.append("ℹ️ 매우 긍정적인 설명입니다. 객관적인 데이터로 검증하세요.")
        
        if not recommendations:
            recommendations.append("✅ 설명문이 비교적 객관적입니다.")
        
        return recommendations


# 싱글톤 인스턴스
_analyzer: Optional[FinBERTAnalyzer] = None


def get_sentiment_analyzer() -> FinBERTAnalyzer:
    """FinBERT 분석기 싱글톤 인스턴스"""
    global _analyzer
    if _analyzer is None:
        _analyzer = FinBERTAnalyzer()
    return _analyzer


def analyze_strategy_description(text: str) -> Dict[str, Any]:
    """
    전략 설명문 분석 (편의 함수)
    
    Args:
        text: 전략 설명문
        
    Returns:
        분석 결과 딕셔너리
    """
    analyzer = get_sentiment_analyzer()
    result = analyzer.analyze_hype(text)
    return result.to_dict()


# ============================================================
# 규칙 기반 분석기 (FinBERT 없이도 동작)
# ============================================================

class RuleBasedHypeAnalyzer:
    """
    규칙 기반 과대광고 분석기
    
    FinBERT 없이도 기본적인 과대광고 탐지가 가능합니다.
    """
    
    def analyze(self, text: str) -> HypeAnalysisResult:
        """규칙 기반 분석"""
        if not text or len(text.strip()) < 10:
            return HypeAnalysisResult(
                success=False,
                error="텍스트가 너무 짧습니다."
            )
        
        result = HypeAnalysisResult(success=True)
        text_lower = text.lower()
        
        # 과대광고 키워드 탐지
        for keyword in FinBERTAnalyzer.HYPE_KEYWORDS_EN + FinBERTAnalyzer.HYPE_KEYWORDS_KR:
            if keyword.lower() in text_lower:
                result.hype_phrases.append(keyword)
        
        # 경고 신호 탐지
        for pattern, description in FinBERTAnalyzer.WARNING_SIGNS:
            if re.search(pattern, text, re.IGNORECASE):
                result.warning_signs.append(description)
        
        # 점수 계산
        result.hype_score = min(
            len(result.hype_phrases) * 10 + len(result.warning_signs) * 15,
            100
        )
        result.hype_level = "extreme" if result.hype_score >= 70 else \
                           "high" if result.hype_score >= 50 else \
                           "medium" if result.hype_score >= 25 else "low"
        
        # 권장사항
        if result.hype_score >= 50:
            result.recommendations.append("⚠️ 과대광고 위험이 있습니다. 신중하게 검토하세요.")
        else:
            result.recommendations.append("✅ 설명문이 비교적 객관적입니다.")
        
        return result


def quick_hype_check(text: str) -> Dict[str, Any]:
    """
    빠른 과대광고 체크 (규칙 기반)
    
    FinBERT 모델 없이도 동작합니다.
    """
    analyzer = RuleBasedHypeAnalyzer()
    result = analyzer.analyze(text)
    return result.to_dict()


if __name__ == "__main__":
    print("FinBERT 감성 분석기 테스트")
    print("=" * 50)
    print(f"Transformers 사용 가능: {TRANSFORMERS_AVAILABLE}")
    
    # 테스트 텍스트
    test_texts = [
        # 과대광고 예시
        """
        🚀 GUARANTEED 100% WIN RATE! This is the BEST strategy ever created!
        Never lose money again with this revolutionary trading system.
        Make $10,000 per day with our secret algorithm. Limited time offer!
        """,
        
        # 객관적 설명 예시
        """
        This strategy uses a simple moving average crossover system.
        Backtested on BTC/USDT from 2020-2023 with 55% win rate.
        Average profit per trade: 2.3%. Maximum drawdown: 15%.
        Please test thoroughly before using with real capital.
        """,
        
        # 한국어 과대광고
        """
        🔥 100% 수익 보장! 최고의 전략입니다!
        이 비밀 전략으로 매일 100만원 벌 수 있습니다.
        지금 바로 시작하세요! 한정 시간 제공!
        """,
    ]
    
    print("\n1. 규칙 기반 분석 (빠름)")
    for i, text in enumerate(test_texts, 1):
        result = quick_hype_check(text)
        print(f"\n테스트 {i}:")
        print(f"  과대광고 점수: {result['hype_score']}")
        print(f"  수준: {result['hype_level']}")
        print(f"  경고: {result['analysis']['warning_signs'][:3]}")
    
    if TRANSFORMERS_AVAILABLE:
        print("\n" + "=" * 50)
        print("2. FinBERT 분석 (정확함)")
        
        analyzer = get_sentiment_analyzer()
        for i, text in enumerate(test_texts, 1):
            result = analyzer.analyze_hype(text)
            print(f"\n테스트 {i}:")
            print(f"  과대광고 점수: {result.hype_score}")
            print(f"  감성: {result.overall_sentiment.value} ({result.sentiment_confidence:.2f})")
            print(f"  권장: {result.recommendations[0] if result.recommendations else '-'}")
    else:
        print("\nFinBERT 사용하려면: pip install transformers torch")
