## Table 1: PaLM-540B Prompting Results on HotpotQA and Fever

| **Prompt Method** | **HotpotQA (EM)** | **Fever (Acc)** |
|---|---|---|
| `Standard` | 28.7 | 57.1 |
| `CoT` (Wei et al., 2022) | 29.4 | 56.3 |
| `CoT-SC` (Wang et al., 2022a) | 33.4 | 60.4 |
| `Act` | 25.7 | 58.9 |
| `ReAct` | 27.4 | 60.9 |
| `CoT-SC → ReAct` | 34.2 | **64.6** |
| `ReAct → CoT-SC` | **35.1** | 62.0 |
| **Supervised SoTA** | 67.5 | 89.5 |

> **주석 a**: HotpotQA EM은 `Standard`, `CoT`, `CoT-SC`에 대해 Wang et al. (2022b)에서 각각 27.1, 28.9, 33.8로 보고됨.
>
> **주석 b**: (Zhu et al., 2021; Lewis et al., 2020)

---

## Figure 2: PaLM-540B Prompting Results with Respect to Number of `CoT-SC` Samples Used

이 그림은 **두 개의 꺾은선 그래프**로 구성되어 있으며, `CoT-SC` 샘플 수(#CoT-SC trials, x축: 0~21)를 늘려감에 따라 각 방법의 성능 변화를 보여준다.

### 왼쪽 그래프: HotpotQA EM

- **x축**: `#CoT-SC trials` (0부터 약 21까지)
- **y축**: HotpotQA EM (약 26~35)
- **`CoT-SC → ReAct`** (파란 실선): 샘플 수가 증가할수록 꾸준히 상승하여 약 **34~35** 수준에 도달하며, 가장 높은 성능을 보인다.
- **`ReAct → CoT-SC`** (주황 실선): 초기에 급격히 상승한 뒤 약 **34~35** 근처에서 안정화되며, `CoT-SC → ReAct`와 유사한 최종 성능을 달성한다.
- **`CoT-SC`** (초록 실선): 샘플 수 증가에 따라 점진적으로 상승하여 약 **33~34** 수준에 이른다.
- **`ReAct`** (빨간 점선): 샘플 수와 무관하게 약 **27.4** 수준의 수평선으로, `CoT-SC` 샘플을 사용하지 않으므로 일정하다.
- **`CoT`** (보라 점선): 마찬가지로 약 **29.4** 수준의 수평선이다.

### 오른쪽 그래프: Fever Acc

- **x축**: `#CoT-SC trials` (0부터 약 21까지)
- **y축**: Fever Acc (약 47.5~65)
- **`CoT-SC → ReAct`** (파란 실선): 샘플 수 증가에 따라 꾸준히 상승하여 약 **64~65**로 가장 높은 성능을 기록한다.
- **`ReAct → CoT-SC`** (주황 실선): 초기에 빠르게 상승한 뒤 약 **62** 수준에서 안정화된다.
- **`CoT-SC`** (초록 실선): 초기에는 매우 낮은 값(약 47~48)에서 시작하여 급격히 상승한 뒤 약 **60** 수준에 수렴한다.
- **`ReAct`** (빨간 점선): 약 **60.9** 수준의 수평선이다.
- **`CoT`** (보라 점선): 약 **56.3** 수준의 수평선이다.

### 핵심 관찰

- 두 데이터셋 모두에서 **`CoT-SC`와 `ReAct`를 결합한 방법**(`CoT-SC → ReAct`, `ReAct → CoT-SC`)이 개별 방법보다 **일관되게 우수한 성능**을 보인다.
- `CoT-SC` 샘플 수를 늘릴수록 성능이 향상되지만, 약 **10~15회** 이후에는 수렴하는 경향이 있다.
- 특히 `CoT-SC → ReAct`는 Fever에서 가장 높은 최종 성능(**64.6**)을 달성하며, 이는 내부 추론(`CoT-SC`)이 실패할 때 외부 도구 활용(`ReAct`)으로 전환하는 전략의 효과를 입증한다.
