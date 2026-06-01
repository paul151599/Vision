# EUV Pellicle Vision Inspection System — 인계 문서 (Handover)

> 작성일: 2026-05-29
> 대상: 본 프로젝트를 인계받는 개발자/엔지니어
> 범위: `run_gui.py` GUI 프로그램을 중심으로 한 전체 시스템

---

## 0. TL;DR (5줄 요약)

1. EUV 펠리클(CNT 멤브레인) 표면 BMP 이미지에서 **정량 특징 60개**를 자동 추출하는 머신비전 시스템.
2. 진입점은 둘 — **GUI(`run_gui.py`)** 는 *추출 + 시각화 + 내보내기* 전용, **CLI(`main.py`)** 는 *기준선 생성 + Pass/Fail 판정* 전용.
3. 모든 feature는 `config/feature_registry.py` 한 곳에 메타데이터(추출법/물리의미/분류가이드)와 함께 선언됨 — **여기가 시스템의 단일 진실 공급원(Single Source of Truth).**
4. 추출 엔진(`core/feature_engine.py`)이 16개 추출기를 캐시 공유 순서로 실행.
5. **⚠️ 가장 큰 공백: GUI에는 정상/불량 판정 기능이 없다.** 판정 로직(`core/judgment.py`, `core/baseline.py`)은 구현되어 있으나 CLI에서만 호출된다. (자세한 내용은 §7)

---

## 1. 시스템 개요

EUV 리소그래피용 펠리클은 CNT(탄소나노튜브) 멤브레인으로, 표면의 두께/밀도 균일성과 결함(파티클, 핀홀, 크랙)이 수율에 직결된다. 본 시스템은 광학 현미경으로 촬영한 표면 이미지를 분석하여:

- 결함(이상점) 탐지 — 개수, 면적, 형태
- 공간 균일성 — 코팅 두께/밀도 편차
- 텍스처 품질 — CNT 네트워크 구조 건전성
- 분광/광학 특성 — 파장 의존적 R/G/B 분석
- 결함 형태 분류 — 원인 추정(파티클 vs 스크래치)

을 정량화한다. 공정은 **Reactor**와 **Densification** 두 단계로 나뉘며, 두 공정은 광학 특성이 크게 다르므로 **기준선을 반드시 독립적으로 관리**한다.

---

## 2. 디렉터리 / 모듈 구조

```
Vision/
├── run_gui.py               ★ GUI 진입점 (이 프로그램)
├── main.py                  CLI 진입점 (extract/baseline/inspect/import-excel)
│
├── gui/
│   ├── app.py               Tkinter 3-panel GUI 본체
│   └── phase_renderer.py    10단계 시각화 이미지 생성
│
├── core/
│   ├── feature_engine.py    ★ 16개 추출기 오케스트레이션 + 공유 캐시
│   ├── image_loader.py      BMP 로드 + gain 역보정 + 채널 분리
│   ├── baseline.py          기준선 생성/저장/로드/Excel import
│   ├── judgment.py          Pass/Fail 판정 (CLI 전용)
│   └── data_models.py       dataclass 정의 (FeatureResult, BaselineSpec 등)
│
├── features/                실제 알고리즘 (16개 추출기 모듈)
│   ├── base.py              추출기 추상 베이스 클래스
│   ├── intensity.py  color.py  glcm.py  lbp.py  fft.py
│   ├── anomaly.py  uniformity.py  entropy.py  local_contrast.py
│   ├── channel_texture.py  spectral_ratio.py  cross_channel.py
│   ├── channel_fft.py  channel_anomaly.py  cielab.py  morphological.py
│
├── config/
│   ├── feature_registry.py  ★ 60개 feature 명세 (단일 진실 공급원)
│   ├── camera.py            카메라 gain (R=1.3, G=1.0, B=0.9)
│   └── settings.py          알고리즘 상수 (커널 크기, 시그마, 그리드 등)
│
├── reporting/               Excel/CSV/시각화 리포트 (CLI inspect용)
│   ├── excel_report.py  csv_report.py  visualization.py
│
├── batch/processor.py       폴더 일괄 검사 (CLI inspect용)
│
├── baselines/               생성된 기준선 JSON 저장 위치
├── output/                  리포트 출력 위치
└── tests/                   (현재 비어 있음 — 테스트 미작성)
```

---

## 3. 실행 방법

### GUI
```bash
python run_gui.py
```
1. 좌측 **+ Files / + Folder** 로 BMP 이미지 로드
2. **▶ Extract Features** 클릭 → 백그라운드 스레드에서 추출 + 시각화
3. 중앙 탭에서 10단계 시각화 확인, 우측에서 feature 값/비교/요약 확인
4. **File → Export CSV / Excel** 로 결과 내보내기

### CLI
```bash
# 단일 이미지 특징 추출 (콘솔 출력)
python main.py extract path/to/image.bmp

# 기준선 생성 (정상품 여러 장 → 평균/표준편차 JSON)
python main.py baseline ./normal_imgs --sample-id LOT001 --process-type Densification

# 검사 (기준선 대비 Pass/Fail + 리포트)
python main.py inspect ./test_imgs --baseline LOT001_Densification.json \
    --process-type Densification --sigma 2.0 --excel --csv

# 기존 Excel 스펙을 기준선으로 import
python main.py import-excel spec.xlsx --sample-id LOT001 --process-type Reactor
```

### 의존성
`numpy`, `opencv-python`(cv2), `scikit-image`(skimage), `scipy`, `Pillow`(PIL), `openpyxl`, `tkinter`(표준 라이브러리).

---

## 4. 핵심 데이터 흐름

```
BMP 파일
  │ ImageLoader.prepare()
  ▼
image_data dict {
    bgr, gray,                       # 원본
    R, G, B,                         # raw 채널 (float64)
    R_corr, G_corr, B_corr           # gain 역보정 채널 (= raw / gain)
}
  │ FeatureEngine.extract() — 16개 추출기를 순서대로 실행
  │   (extractor 간 무거운 중간결과는 cache dict로 공유)
  ▼
results dict { feature_id: FeatureResult(value) }   # 60개
  │
  ├─[GUI]──→ 표시/시각화/CSV·Excel 내보내기 (여기서 끝)
  │
  └─[CLI]──→ JudgmentEngine.judge_all(results, baseline)
               │ feature별 μ±nσ 스펙 비교
               ▼
             InspectionResult { overall: PASS/FAIL, fail_reasons[] }
               │
               ▼
             Excel/CSV 리포트
```

**Gain 역보정의 의미**: 카메라가 채널별 아날로그 gain(R=1.3, G=1.0, B=0.9)을 적용한 상태로 촬영하므로, `corrected = raw / gain` 으로 되돌려 물리적으로 의미 있는 분광 응답을 복원한다. Group B(광학물리) feature들은 보정 채널(`*_corr`)을 사용한다.

**공유 캐시 최적화**: 추출기 실행 순서는 캐시 재사용에 최적화됨 — GLCM(glcm 행렬) → Color(R/G/B) → LocalContrast(local std map) → Anomaly(mask/labels/stats) → SpectralRatio(rb/gb ratio map) → 나머지. 예: Morphological은 Anomaly가 캐시한 `anomaly_mask_3sigma`를 재사용한다.

---

## 5. 전체 Feature 목록 (60개)

> 표시 순서는 **품질 분류 우선순위(QualityPhase 1→6)** 를 따른다.
> 그룹: A=레거시(그레이스케일 기반), B=광학물리(채널/분광, gain 보정), C=형태학.
> GC = gain-corrected 채널 사용. ★ = critical feature(판정 시 하나라도 FAIL이면 전체 FAIL).

### Phase 1 — Defect Detection (결함 직접 탐지)

| # | ID | 이름 | 그룹 | 모듈 | 산출 방법 |
|---|----|------|------|------|-----------|
| 1 | `anomaly_count` | Total Anomaly Count | A | anomaly | 3σ 연결요소(≥5px) 총 개수 |
| 2 | `anomaly_area_pct` ★ | Anomaly Area % | A | anomaly | 3σ 이상점 총면적 / 전체 ×100 |
| 3 | `max_anomaly_area` ★ | Max Anomaly Area | A | anomaly | 최대 단일 결함 면적(px) |
| 4 | `texture_anomaly_2sigma` | Texture Anomaly 2σ | A | anomaly | x>μ+2σ 픽셀 수 (밝은 쪽) |
| 5 | `texture_anomaly_3sigma` | Texture Anomaly 3σ | A | anomaly | x>μ+3σ 픽셀 수 |
| 6 | `texture_anomaly_4sigma` | Texture Anomaly 4σ | A | anomaly | x>μ+4σ 픽셀 수 |
| 7 | `texture_anomaly_5sigma` | Texture Anomaly 5σ | A | anomaly | x>μ+5σ 픽셀 수 |
| 8 | `mean_anomaly_size` | Mean Anomaly Size | A | anomaly | 3σ 연결요소 평균 면적 |
| 9 | `std_anomaly_size` | Std Anomaly Size | A | anomaly | 3σ 연결요소 면적 표준편차 |
| 10 | `median_anomaly_size` | Median Anomaly Size | A | anomaly | 3σ 연결요소 면적 중앙값 |
| 11 | `chanom_b_3sigma_count` ★ | B-ch 3σ Count | B | channel_anomaly | GC B채널 3σ 연결요소 수 (GC) |

### Phase 2 — Uniformity (공간 균일성)

| # | ID | 이름 | 그룹 | 모듈 | 산출 방법 |
|---|----|------|------|------|-----------|
| 12 | `grid_uniformity_std` | Grid Uniformity Std | A | uniformity | 8×8 그리드 셀 평균의 std |
| 13 | `grid_uniformity_range` | Grid Uniformity Range | A | uniformity | 8×8 셀 평균 max-min |
| 14 | `local_contrast_mean` | Local Contrast Mean | A | local_contrast | 15×15 local std map의 평균 |
| 15 | `local_contrast_std` | Local Contrast Std | A | local_contrast | local std map의 표준편차 |

### Phase 3 — Distribution Shape (밝기 분포 형태)

| # | ID | 이름 | 그룹 | 모듈 | 산출 방법 |
|---|----|------|------|------|-----------|
| 16 | `gray_std` | Gray Std | A | intensity | 그레이 전체 표준편차 |
| 17 | `gray_skewness` | Gray Skewness | A | intensity | 히스토그램 왜도 (scipy) |
| 18 | `gray_kurtosis` | Gray Kurtosis | A | intensity | 히스토그램 첨도 (Fisher) |
| 19 | `gray_mean` | Gray Mean | A | intensity | 그레이 전체 평균 |
| 20 | `gray_entropy` | Gray Entropy | A | entropy | 히스토그램 Shannon 엔트로피 |
| 21 | `local_entropy_mean` | Local Entropy Mean | A | entropy | rank entropy(disk r=5) 맵 8×8 평균 |
| 22 | `local_entropy_std` | Local Entropy Std | A | entropy | local entropy 맵 8×8 std |

### Phase 4 — Texture Quality (CNT 네트워크 구조)

| # | ID | 이름 | 그룹 | 모듈 | 산출 방법 |
|---|----|------|------|------|-----------|
| 23 | `glcm_contrast` | GLCM Contrast | A | glcm | GLCM 대비 (d=1, θ=0) |
| 24 | `glcm_homogeneity` | GLCM Homogeneity | A | glcm | GLCM 균질성 |
| 25 | `glcm_energy` | GLCM Energy | A | glcm | GLCM 에너지(ASM) |
| 26 | `glcm_correlation` | GLCM Correlation | A | glcm | GLCM 상관 |
| 27 | `lbp_entropy` | LBP Entropy | A | lbp | LBP uniform 히스토그램 엔트로피 |
| 28 | `fft_low_freq_ratio` | FFT Low-freq Ratio | A | fft | 반경 ≤max/3 에너지 비율 |
| 29 | `fft_mid_freq_ratio` | FFT Mid-freq Ratio | A | fft | max/3~2max/3 에너지 비율 |
| 30 | `fft_high_freq_ratio` | FFT High-freq Ratio | A | fft | 반경 >2max/3 에너지 비율 |

### Phase 5 — Spectral / Optical (파장 의존 분석)

| # | ID | 이름 | 그룹 | 모듈 | 산출 방법 |
|---|----|------|------|------|-----------|
| 31 | `red_mean` | Red Mean | A | color | R채널 평균 |
| 32 | `green_mean` | Green Mean | A | color | G채널 평균 |
| 33 | `blue_mean` | Blue Mean | A | color | B채널 평균 |
| 34 | `rg_diff_mean` | RG Diff Mean | A | color | R평균 - G평균 |
| 35 | `rb_diff_mean` | RB Diff Mean | A | color | R평균 - B평균 |
| 36 | `gb_diff_mean` | GB Diff Mean | A | color | G평균 - B평균 |
| 37 | `saturation_mean` | Saturation Mean | A | color | HSV S채널 평균 |
| 38 | `saturation_std` | Saturation Std | A | color | HSV S채널 std |
| 39 | `spratio_rb_mean` | R/B Ratio Mean | B | spectral_ratio | GC R/B 비율맵 평균 (GC) |
| 40 | `spratio_rb_std` | R/B Ratio Std | B | spectral_ratio | R/B 비율맵 std (GC) |
| 41 | `spratio_rb_skew` | R/B Ratio Skew | B | spectral_ratio | R/B 비율맵 왜도 (GC) |
| 42 | `spratio_gb_mean` | G/B Ratio Mean | B | spectral_ratio | GC G/B 비율맵 평균 (GC) |
| 43 | `spratio_gb_std` | G/B Ratio Std | B | spectral_ratio | G/B 비율맵 std (GC) |
| 44 | `spratio_gb_skew` | G/B Ratio Skew | B | spectral_ratio | G/B 비율맵 왜도 (GC) |
| 45 | `chtex_r_contrast` | R GLCM Contrast | B | channel_texture | GC R채널 GLCM 대비 (GC) |
| 46 | `chtex_r_homogeneity` | R GLCM Homogeneity | B | channel_texture | GC R채널 GLCM 균질성 (GC) |
| 47 | `chtex_g_contrast` | G GLCM Contrast | B | channel_texture | GC G채널 GLCM 대비 (GC) |
| 48 | `chtex_g_homogeneity` | G GLCM Homogeneity | B | channel_texture | GC G채널 GLCM 균질성 (GC) |
| 49 | `chtex_b_contrast` | B GLCM Contrast | B | channel_texture | GC B채널 GLCM 대비 (GC) |
| 50 | `chtex_b_homogeneity` | B GLCM Homogeneity | B | channel_texture | GC B채널 GLCM 균질성 (GC) |
| 51 | `xchan_pearson_rb` | Pearson(R,B) | B | cross_channel | GC R/B 채널 Pearson 상관 (GC) |
| 52 | `xchan_local_rb_std` | Local R/B Std | B | cross_channel | R/B 비율맵 8×8 평균의 std (GC) |
| 53 | `xchan_coherence` | Channel Coherence | B | cross_channel | 1 - mean(픽셀별 CV) (GC) |
| 54 | `chfft_b_high_ratio` | B High-freq Ratio | B | channel_fft | GC B채널 고주파 에너지 비율 (GC) |
| 55 | `chfft_r_high_ratio` | R High-freq Ratio | B | channel_fft | GC R채널 고주파 에너지 비율 (GC) |
| 56 | `cielab_de_mean` | ΔE Mean | B | cielab | GC 이미지 CIE76 ΔE 평균 (GC) |
| 57 | `cielab_local_de_std` | Local ΔE Std | B | cielab | ΔE 맵 8×8 평균의 std (GC) |

### Phase 6 — Defect Morphology (결함 형태 → 원인 분류)

| # | ID | 이름 | 그룹 | 모듈 | 산출 방법 |
|---|----|------|------|------|-----------|
| 58 | `morph_circularity` | Mean Circularity | C | morphological | 3σ contour의 4πA/P² 평균 |
| 59 | `morph_aspect_ratio` | Mean Aspect Ratio | C | morphological | bounding rect W/H 평균 |
| 60 | `morph_solidity` | Mean Solidity | C | morphological | 면적/볼록껍질면적 평균 |

> **각 feature의 물리적 의미 / 품질판정 노트 / 정상·불량 분류 가이드**는 `config/feature_registry.py`에 한글로 상세히 기술되어 있으며, GUI의 feature 값 표에서 `[i]` 아이콘 클릭 시 팝업으로 확인 가능하다.

---

## 6. 알고리즘 설명 (모듈별)

### 6.1 ImageLoader (`core/image_loader.py`)
- `np.fromfile + cv2.imdecode` 로 BMP 로드 → **한글 경로 지원**(cv2.imread는 한글 경로 실패).
- BGR uint8 로드 → gray 변환 → R/G/B 분리(float64) → gain 역보정(`raw / gain`).
- `prepare()` 가 raw 채널과 보정 채널을 모두 담은 dict 반환.

### 6.2 Anomaly (`features/anomaly.py`) — Phase 1 핵심
- 그레이 전역 μ, σ 계산.
- **시그마 카운트**: `|x-μ| > nσ` (n=2,3,4,5) 픽셀 수 — **양방향(밝은+어두운 이상점)**. anomaly = 멤브레인의 전형적 광학응답에서의 편차(방향 무관)로 정의.
- **연결요소 분석**: 양방향 3σ 마스크에 `cv2.connectedComponentsWithStats(8-연결)` → 5px 이상 컴포넌트만 필터링 → count, area%, max/mean/std/median 면적 산출.
- mask/labels/stats를 캐시하여 Morphological이 재사용.
- ✅ 시각화(phase_renderer)·Morphological·B채널 anomaly와 모두 **양방향**(`|gray-μ|>3σ`)으로 일관됨. (2026-05-29 통일 완료 — 이전엔 본 모듈만 단방향이었음)

### 6.3 Intensity (`features/intensity.py`) — Phase 3
- 그레이 전체에 대해 평균/표준편차(ddof=0)/왜도/첨도(scipy, Fisher) 산출.
- skewness 부호로 결함 방향 추정(양수=밝은 파티클, 음수=어두운 보이드/핀홀).

### 6.4 Color (`features/color.py`) — Phase 5
- R/G/B 평균 및 채널차(R-G, R-B, G-B). **raw 채널 사용**.
- Saturation: 원본 BGR → HSV 변환 후 S채널 평균/std.

### 6.5 GLCM (`features/glcm.py`) — Phase 4
- `skimage.graycomatrix(distance=1, angle=0, levels=256, symmetric, normed)`.
- Contrast / Homogeneity / Energy / Correlation 산출. **원본 전체 해상도**에서 계산.

### 6.6 LBP (`features/lbp.py`) — Phase 4
- `local_binary_pattern(R=1, P=8, method='uniform')` → uniform 히스토그램(10 bin) → Shannon 엔트로피.

### 6.7 FFT (`features/fft.py`) — Phase 4
- 2D FFT → fftshift → magnitude. 중심 기준 반경 맵 생성.
- 반경을 max/3, 2max/3 로 3등분하여 저/중/고주파 에너지 비율(에너지=magnitude²).

### 6.8 Uniformity (`features/uniformity.py`) — Phase 2
- 이미지를 8×8 그리드로 분할, 각 셀 평균 계산 → 셀 평균들의 std와 range.

### 6.9 Entropy (`features/entropy.py`) — Phase 3
- 전역 엔트로피(256-bin 히스토그램).
- 국소 엔트로피: `skimage rank.entropy(disk r=5)` 맵 → 8×8 그리드 평균/std.

### 6.10 Local Contrast (`features/local_contrast.py`) — Phase 2
- box filter로 국소 평균/제곱평균 → `local_std = sqrt(E[X²]-E[X]²)` (15×15 커널).
- local std map의 평균/std.

### 6.11 Channel Texture (`features/channel_texture.py`) — Phase 5 (GC)
- gain 보정 R/G/B 각각에 GLCM Contrast/Homogeneity (총 6개).

### 6.12 Spectral Ratio (`features/spectral_ratio.py`) — Phase 5 (GC)
- 픽셀별 R/B, G/B 비율맵 (B<1 픽셀 제외하여 0나눗셈 방지).
- 각 비율맵의 평균/std/왜도. 비율맵은 cross_channel이 재사용하도록 캐시.

### 6.13 Cross-Channel (`features/cross_channel.py`) — Phase 5 (GC)
- Pearson(R,B): 전체 픽셀 평탄화 후 상관계수.
- Local R/B std: R/B 비율맵 8×8 그리드 평균들의 std.
- Coherence: 픽셀별 CV=std(R,G,B)/mean(R,G,B) → `1 - mean(CV)`.

### 6.14 Channel FFT (`features/channel_fft.py`) — Phase 5 (GC)
- 보정 B/R 채널의 고주파(반경>2max/3) 에너지 비율.

### 6.15 Channel Anomaly (`features/channel_anomaly.py`) — Phase 1 (GC)
- 보정 B채널 **양방향** 3σ 마스크 → 연결요소 5px 이상 개수.

### 6.16 CIELAB (`features/cielab.py`) — Phase 5 (GC)
- 보정 채널 → BGR 재조합(0~255 clip) → CIE L\*a\*b\* 변환.
- 전역 평균을 기준으로 픽셀별 CIE76 ΔE → 평균, 8×8 국소 std.

### 6.17 Morphological (`features/morphological.py`) — Phase 6
- 3σ anomaly 마스크의 contour별: Circularity(4πA/P²), Aspect Ratio(W/H), Solidity(면적/볼록껍질).
- 5px 이상만, 각 지표의 평균.

### 6.18 Judgment (`core/judgment.py`) — CLI 전용
- 기준선 stats(μ, σ)로 스펙 경계 계산:
  - `UPPER` 방향: 상한만 = μ + nσ
  - `BILATERAL`: μ ± nσ (기본 n=2.0)
- feature별 PASS/FAIL → **critical feature가 하나라도 FAIL이면 전체 FAIL**.
- critical: `anomaly_area_pct`, `max_anomaly_area`, `chanom_b_3sigma_count`.

### 6.19 Phase Renderer (`gui/phase_renderer.py`) — GUI 시각화
- 10개 단계 이미지를 PIL로 생성: Original, Grayscale, Channels(2×2), GainCorrected(2×2), FFT(밴드 원 표시), Anomaly(3σ overlay), LocalContrast(HOT colormap), Entropy(VIRIDIS), CIELAB(MAGMA), Morphology(circularity 색상 코딩).
- ⚠️ **추출 엔진과 별개로 시각화용 계산을 재수행**한다(중복 연산). 또한 Anomaly 시각화는 양방향 3σ라 feature 값(단방향)과 표시가 다를 수 있다.

---

## 7. 보완점 / 개선 리포트

> 우선순위: 🔴 높음(인계 직후 고려) / 🟡 중간 / 🟢 낮음(품질 향상)

### 🔴 A. GUI에 판정(Pass/Fail) 기능 부재 — 최우선 공백
- 현 GUI는 *추출 + 시각화 + 내보내기*까지만. `judgment.py`/`baseline.py`/`ProcessType`을 전혀 호출하지 않음.
- 실사용에서 "정상/불량 판정"을 GUI에서 하려면:
  - 공정 타입(Reactor/Densification) 선택 UI,
  - 기준선 JSON 로드/생성 UI,
  - feature별 PASS/FAIL 색상 표시 + overall 판정 배지,
  - σ multiplier 조정 슬라이더
  를 추가해야 함. (백엔드 로직은 이미 존재하므로 GUI 연결만 하면 됨)

### ✅ B. Anomaly 마스크 단방향/양방향 불일치 — **해결됨 (2026-05-29)**
- (이전) `anomaly.py`만 단방향(`gray > μ+3σ`)이고 시각화·형태학·B채널은 양방향이라, Anomaly 탭 표시와 `anomaly_count` 값이 불일치했음.
- (조치) `anomaly.py`를 **양방향**(`|x-μ| > nσ`)으로 통일. 시그마 카운트·연결요소 마스크 모두 적용. 레지스트리 method/physical_meaning 텍스트도 정정. 합성 이미지로 밝은+어두운 블롭 동시 검출 검증 완료.
- ⚠️ **기준선 재생성 필요**: anomaly 계열 feature 값이 바뀌었으므로 기존 baseline JSON은 무효 → `python main.py baseline ...` 재실행 요망.

### 🔴 C. 추출기 예외 처리 부재 — 견고성
- `FeatureEngine.extract()`는 추출기별 try/except가 없어, 한 추출기가 실패하면(손상 이미지 등) **이미지 전체 처리가 중단**됨.
- GUI 워커 스레드에서 예외 발생 시 사용자에게 표시되지 않고 진행바가 멈춘 채 "Processing..." 상태로 고착됨. → 추출기별 예외 격리 + GUI에 에러 surfacing 필요.

### 🟡 D. 성능 — 대용량/배치
- 입력이 3504×3504(`settings.DEFAULT_IMAGE_SIZE`)인데:
  - GLCM(levels=256)을 **전체 해상도에서 4회**(gray + R/G/B) 계산 — 매우 무거움.
  - 2D FFT를 **3회**(gray + B + R), rank entropy, LBP도 전체 해상도.
  - `GLCM_DOWNSAMPLE=1024` 상수가 정의돼 있으나 **미사용**(reserved) — 다운샘플 적용 시 큰 속도 향상 여지.
- 이미지 간 병렬 처리 없음(단일 워커 스레드 순차). 배치 검사 시 멀티프로세싱 고려.

### 🟡 E. GUI 메모리 — 대량 배치
- `phase_images`가 **모든 이미지의 10개 PIL 이미지를 메모리 상주**시킴. 수십~수백 장 로드 시 메모리 증가. 지연 렌더링(선택 시 생성) 또는 LRU 캐시 권장.

### 🟡 F. 시각화 중복 연산
- `phase_renderer`가 추출 엔진과 별도로 FFT/anomaly/entropy/CIELAB를 재계산. 추출 시 캐시한 중간결과를 시각화에 재사용하면 처리 시간 절감 + §B 불일치 해소.

### 🟡 G. 처리 취소 불가
- "Extract Features" 실행 후 중단 버튼 없음. 긴 배치 작업 중 취소 기능 필요.

### 🟢 H. 문서/카운트 불일치
- `feature_registry.py` 주석 "Registry of all 60 features" vs `FeatureGroup.A="Legacy 36 features"` — 실제 Group A는 **37개**(총 60개). 주석을 37로 정정 권장.
- (auto-memory의 "59 features" 기록도 60으로 갱신 필요 — 본 인계 시 반영.)

### 🟢 I. 테스트 부재
- `tests/`에 `__init__.py`만 있고 실제 테스트 없음. 최소한 각 추출기의 출력 키/형상/범위 검증, 합성 이미지 회귀 테스트 권장.

### 🟢 J. 카메라 설정 GUI 노출 없음
- gain(R/G/B)이 `CameraConfig` 기본값으로 하드코딩. 장비/렌즈 변경 시 GUI에서 조정 불가. 설정 패널 추가 고려.

### 🟢 K. 판정 STABLE vs MODERATE 동일 처리
- `judgment.py` docstring은 MODERATE에 "wider tolerance"라 하나 실제 코드는 STABLE/MODERATE 모두 동일하게 μ±nσ 적용. 의도대로 차등 적용하거나 문서 정정 필요.

### 🟢 L. Gain 보정 시 clip 손실
- CIELAB/시각화에서 보정 채널을 0~255로 clip 후 uint8. B는 /0.9로 값이 커져 255 초과분이 잘림 → 밝은 영역 정보 손실 가능. 정규화 방식 재검토 여지.

---

## 8. 인계 체크리스트

- [ ] `python run_gui.py` 정상 실행 확인 (의존성 설치 필요 시 §3 참조)
- [ ] 샘플 BMP로 추출 → 60개 feature 값 + 10개 시각화 탭 확인
- [ ] CSV/Excel 내보내기 동작 확인
- [ ] CLI `baseline` → `inspect` 흐름으로 Pass/Fail 판정 동작 확인
- [ ] `config/feature_registry.py`에서 feature 메타데이터 구조 숙지 (수정 시 이 파일만)
- [ ] 보완점 §7 중 A/B/C(🔴)를 다음 작업 후보로 검토
```
