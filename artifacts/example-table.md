## Table 2: Success and Failure Modes of ReAct and CoT on HotpotQA

아래 표는 **ReAct**와 **CoT**의 성공 및 실패 유형과 그 정의, 그리고 무작위로 선택된 예시에 대한 인간 분석 결과 비율을 보여준다.

### Success (성공)

| Type | Definition | ReAct | CoT |
|------|-----------|-------|-----|
| **True positive** | Correct reasoning trace and facts | 94% | 86% |
| **False positive** | Hallucinated reasoning trace or facts | 6% | 14% |

### Failure (실패)

| Type | Definition | ReAct | CoT |
|------|-----------|-------|-----|
| **Reasoning error** | Wrong reasoning trace (including failing to recover from repetitive steps) | 47% | 16% |
| **Search result error** | Search return empty or does not contain useful information | 23% | - |
| **Hallucination** | Hallucinated reasoning trace or facts | 0% | 56% |
| **Label ambiguity** | Right prediction but did not match the label precisely | 29% | 28% |

### 주요 분석

- **성공 사례**에서 ReAct는 **94%**가 올바른 추론과 사실에 기반한 반면, CoT는 **86%**로 다소 낮고 **14%**가 환각(hallucination)에 의한 거짓 긍정이다.
- **실패 사례**에서 가장 두드러진 차이는 **환각(Hallucination)** 항목으로, CoT는 실패의 **56%**가 환각에 기인하지만 ReAct는 **0%**이다. 이는 ReAct가 외부 검색을 통해 사실을 검증하기 때문에 환각을 효과적으로 방지함을 시사한다.
- 반면 ReAct의 주요 실패 원인은 **추론 오류(47%)**와 **검색 결과 오류(23%)**로, 반복적인 단계에서 회복하지 못하거나 검색 결과가 비어 있는 경우에 해당한다.
- **검색 결과 오류**는 CoT에는 해당하지 않는데(`-`), 이는 CoT가 외부 검색 도구를 사용하지 않기 때문이다.
- **라벨 모호성**은 두 방법 모두 유사한 비율(ReAct 29%, CoT 28%)을 보이며, 정답을 맞혔으나 라벨과 정확히 일치하지 않는 경우이다.
