# EUV Pellicle Vision Inspection System — Improvement Plan
> Created: 2026-03-18
> Status: Planning
> Author: Claude (AI Assistant) + EUV Pellicle Process Engineer

---

## Context

현재 시스템은 CLI 기반으로 개발되어 Feature 추출 / Baseline / Judgment 파이프라인이 잘 구축되어 있으나,
실제 운용 관점에서 다음과 같은 핵심 개선이 필요함:

| 현황 | 문제 |
|------|------|
| 카메라 10-bit RGB 출력 | `cv2.IMREAD_COLOR`로 8-bit 강제 → **75% 정보 손실** |
| GUI Feature 표시 | raw 값만 표시, **Pass/Fail 판정 없음** |
| 이미지 포맷 | **BMP만 지원** (TIFF 16-bit 미지원) |
| 성능 | 단일 스레드, GLCM 풀해상도 → 느림 |
| 안정성 | NaN/Inf 미검증, ROI 마스킹 없음, 파라미터 하드코딩 |

### Camera Settings (Preciv Pro / Olympus OM)

| 항목 | 설정값 |
|------|--------|
| Color mode | RGB |
| Bit depth | **10-bit RGB color** |
| Color space | sRGB |
| Gamma | 1 (Linear) |
| Sharpness | 2 |
| Contrast | 0 |
| Shading | Flatfield |
| Color R / G / B | 1.3 / 1.0 / 0.9 |
| Exposure | Peak |
| Resolution | Super High |

---

## Phase 1: 10-bit Data Pipeline (CRITICAL)

> **영향도**: 모든 59개 Feature의 정밀도에 직접 영향
> **핵심**: 카메라 10-bit(1024 level) → 현재 8-bit(256 level) = 75% 정보 손실

### 1A. Multi-Format Image Loading + Bit Depth Preservation

**수정 파일: `core/image_loader.py`**

| 변경 | 내용 |
|------|------|
| 포맷 지원 | `SUPPORTED_EXTENSIONS = {'.bmp', '.tif', '.tiff', '.png'}` |
| TIFF 로딩 | `cv2.IMREAD_UNCHANGED` 플래그 → 16-bit 데이터 보존 |
| BMP/PNG | 기존 `cv2.IMREAD_COLOR` 유지 (8-bit) |
| 메타데이터 | `prepare()` 반환에 `bit_depth` (8/16), `max_value` (255/65535) 추가 |
| 정규화 | 채널을 `[0.0, 1.0]` 범위로 정규화 → bit depth 무관 비교 가능 |

**수정 파일: `batch/processor.py`**

| 변경 | 내용 |
|------|------|
| line 29, 72 | `pattern: str = "*.bmp"` → 다중 확장자 지원 |
| glob | `["*.bmp", "*.tif", "*.tiff", "*.png"]` 순회 |

**수정 파일: `gui/app.py`**

| 변경 | 내용 |
|------|------|
| line 199 | `filetypes`에 TIFF 추가 |
| line 211 | `folder.glob("*.bmp")` → 모든 지원 확장자로 확장 |

### 1B. Bit-Depth Aware Feature Extraction

**수정 파일: `features/glcm.py`**
- 16-bit 입력 시 256 level로 양자화 후 GLCM 계산
- `(gray / max_value * 255).astype(np.uint8)` 변환

**수정 파일: `features/channel_texture.py`**
- line 21: `np.clip(ch_float, 0, 255)` → `max_value` 기반 동적 양자화

**수정 파일: `features/spectral_ratio.py`**
- line 23: `b > 1.0` 임계값 → `b > (max_value * 0.004)` (bit depth 대응)

**수정 파일: `config/settings.py`**
- `DEFAULT_BIT_DEPTH = 8`, `GLCM_QUANTIZE_LEVELS = 256` 추가

### 1C. Backward Compatibility

- 기존 BMP 워크플로우 동일 동작 보장
- 기존 baseline JSON과의 호환 경고 메시지 추가
- **검증**: 기존 BMP 2장 결과가 변경 전과 동일한지 확인

---

## Phase 2: GUI Pass/Fail Integration

> **영향도**: 운용 편의성, 실시간 품질 판정
> **핵심**: Judgment 엔진이 CLI에만 연결 → GUI에서도 판정 결과 표시

### 2A. Process Type Selector + Baseline Loader

**수정 파일: `gui/app.py`**

| 추가 UI | 내용 |
|---------|------|
| `ttk.Combobox` | Reactor / Densification 선택 |
| "Load Baseline" 버튼 | JSON baseline 파일 선택 다이얼로그 |
| 상태 변수 | `self.baseline: Optional[BaselineSpec] = None` |
| File 메뉴 | "Load Baseline..." 항목 추가 |

### 2B. Feature Tree Judgment Color-Coding

**수정 파일: `gui/app.py`**

| 변경 | 내용 |
|------|------|
| `_display_features()` | baseline 로드 시 `JudgmentEngine.judge_all()` 실행 |
| Tree tags | `pass` → 초록(#c8e6c9), `fail` → 빨강(#ffcdd2) |
| 컬럼 확장 | `("feature", "value", "info")` → `("feature", "value", "mean", "spec", "judge", "info")` |

### 2C. Overall PASS/FAIL Badge

**수정 파일: `gui/app.py`**

| 추가 UI | 내용 |
|---------|------|
| 상태 라벨 | Progress bar 아래, PASS=초록 / FAIL=빨강 (대형 폰트) |
| 이미지 리스트 | 판정 아이콘 표시 (✓ PASS / ✗ FAIL) |

### 2D. Sigma Multiplier Control

**수정 파일: `gui/app.py`**

| 추가 UI | 내용 |
|---------|------|
| `ttk.Spinbox` | default 2.0, range 1.0~5.0, step 0.5 |
| 연결 | `JudgmentEngine(sigma_multiplier=...)` |

---

## Phase 3: Performance Optimization

> **영향도**: 배치 처리 속도, 메모리 사용량
> **핵심**: GLCM 풀해상도 + 단일스레드 = 병목

### 3A. GLCM Downsampling

**수정 파일: `features/glcm.py`, `features/channel_texture.py`**

| 변경 | 내용 |
|------|------|
| 다운샘플 | `GLCM_DOWNSAMPLE = 1024` 활성화 (settings.py line 16에 예약됨) |
| 적용 | GLCM 계산 전 `cv2.resize(gray, (1024, 1024), cv2.INTER_AREA)` |
| 효과 | 3504x3504 → 1024x1024 = **~12배 속도 향상** |
| 정확도 | GLCM 통계값은 1024x1024에서 충분히 수렴 |

### 3B. Parallel Batch Processing

**수정 파일: `batch/processor.py`**

| 변경 | 내용 |
|------|------|
| 엔진 | `concurrent.futures.ProcessPoolExecutor` |
| Workers | `max_workers = min(os.cpu_count(), 4)` |
| 조건 | 이미지 간 독립적 → embarrassingly parallel |

### 3C. GUI Cache Optimization

**수정 파일: `gui/app.py` (line 267-271), `gui/phase_renderer.py`**

| 변경 | 내용 |
|------|------|
| 문제 | `extract()` + `render_all_phases()` 가 동일 이미지를 **2번 로딩** |
| 해결 | `prepare()` 결과를 공유하여 I/O 중복 제거 |
| 방법 | `render_all_phases()`에 optional `image_data` 파라미터 추가 |

---

## Phase 4: Robustness + Extensibility

> **영향도**: 장기 안정성, 유지보수성
> **핵심**: 엣지 케이스 처리, 설정 외부화

### 4A. ROI Masking

**수정 파일: `core/image_loader.py` + 16개 feature extractor**

| 변경 | 내용 |
|------|------|
| `create_roi_mask()` | 원형 또는 사각 마진 마스크 생성 |
| `prepare()` | `roi_mask` 키 추가 |
| 각 extractor | 글로벌 통계 시 `roi_mask` 적용 (예: `np.mean(gray[roi_mask])`) |
| 하위호환 | mask 없으면 전체 이미지 (기본값) |

### 4B. Numerical Validation

**수정 파일: `core/feature_engine.py`**

| 변경 | 내용 |
|------|------|
| 검증 | 각 extractor 반환값 `np.isfinite()` 체크 |
| 처리 | NaN/Inf → 0.0 대체 + warning 로깅 |

### 4C. Image Dimension Validation

**수정 파일: `core/image_loader.py`**

| 변경 | 내용 |
|------|------|
| 검증 | 로딩 후 `DEFAULT_IMAGE_SIZE (3504x3504)` 비교 |
| 처리 | 불일치 시 warning (비표준 크기 허용하되 경고) |

### 4D. External Configuration File

**신규 파일: `config/user_settings.json`**
**수정 파일: `config/settings.py`**

| 변경 | 내용 |
|------|------|
| JSON 파일 | 모든 tunable 파라미터 외부화 |
| 로드 로직 | JSON 존재 시 override, 없으면 기본값 |
| 포함 항목 | sigma levels, kernel sizes, grid sizes, camera gains, GLCM downsample |

---

## Implementation Sequence

```
Phase 1 & 2 (병렬 진행 가능)
│
├── Step 1: 멀티포맷 로더 ─────────── [중] 의존: 없음
├── Step 2: Bit-depth aware 추출 ──── [중] 의존: Step 1
├── Step 3: 하위호환 검증 ──────────── [하] 의존: Step 1-2
│
├── Step 4: 공정타입 + Baseline GUI ── [하] 의존: 없음
├── Step 5: 판정 색상 표시 ──────────── [중] 의존: Step 4
├── Step 6: PASS/FAIL 배지 ─────────── [하] 의존: Step 5
├── Step 7: Sigma 조절 ────────────── [하] 의존: Step 4
│
Phase 3 (독립적)
├── Step 8: GLCM 다운샘플 ──────────── [하] 의존: 없음
├── Step 9: 배치 병렬화 ────────────── [중] 의존: 없음
├── Step 10: GUI 캐시 ──────────────── [하] 의존: 없음
│
Phase 4 (시간 여유에 따라)
├── Step 11: ROI 마스킹 ────────────── [상] 의존: 없음
├── Step 12: 수치 검증 ────────────── [하] 의존: 없음
├── Step 13: 크기 검증 ────────────── [하] 의존: 없음
└── Step 14: 설정 외부화 ──────────── [중] 의존: 없음
```

---

## Critical Files Summary

| 파일 | Phase | 수정 내용 |
|------|-------|----------|
| `core/image_loader.py` | 1, 4 | TIFF 16-bit, bit_depth 메타, ROI 마스크, 크기 검증 |
| `gui/app.py` | 2, 3 | Baseline 로더, 공정타입, 판정 색상, PASS/FAIL, sigma, 캐시 |
| `features/glcm.py` | 1, 3 | 16-bit 양자화, 다운샘플링 |
| `features/channel_texture.py` | 1, 3 | max_value 대응, 다운샘플링 |
| `features/spectral_ratio.py` | 1 | b > 1.0 임계값 동적화 |
| `config/settings.py` | 1, 4 | bit depth, GLCM downsample, user settings |
| `batch/processor.py` | 1, 3 | 멀티포맷 glob, ProcessPoolExecutor |
| `gui/phase_renderer.py` | 3 | image_data 파라미터 추가 |
| `core/feature_engine.py` | 4 | NaN/Inf 검증 |

---

## Verification Plan

| Phase | 검증 방법 |
|-------|----------|
| Phase 1 | 기존 BMP 2장(R20-11377 Reactor/Densification) 추출 결과가 변경 전과 동일 |
| Phase 2 | Baseline JSON 로드 → GUI 색상 판정 → CSV/Excel judgment 포함 확인 |
| Phase 3 | GLCM 다운샘플 전후 feature 값 차이 < 5%, 배치 처리 시간 비교 |
| Phase 4 | ROI 마스크 전후 edge artifact 감소, NaN 발생 시 graceful 처리 |

---

## Notes

- **이미지 포맷 권장**: 16-bit TIFF > BMP(8-bit) > PNG >> JPG (JPG 사용 금지)
- **Gamma=1 (Linear)**: 어두운 영역에서 10bit→8bit 정보 손실이 더 큼
- **gray_mean 주의**: Exposure: Peak 설정으로 샷마다 자동노출 보정 → 촬영 조건 변동 반영 가능성
- **분류 핵심 Feature 6종**: anomaly_count(3σ), anomaly_area_pct, max_anomaly_area, grid_uniformity_std, gray_std, gray_skewness
