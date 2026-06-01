"""Registry of all 60 inspection features.

Feature display order follows quality classification priority:
  Phase 1 — Defect Detection (direct defect indicators)
  Phase 2 — Uniformity (process stability)
  Phase 3 — Distribution Shape (anomaly pattern detection)
  Phase 4 — Texture Quality (CNT network structure)
  Phase 5 — Spectral / Optical (wavelength-dependent analysis)
  Phase 6 — Defect Morphology (root cause classification)
"""
from dataclasses import dataclass
from enum import Enum
from typing import List, Optional


class FeatureGroup(str, Enum):
    A = "A"  # Legacy 36 features
    B = "B"  # Optical-physics 20 features
    C = "C"  # Morphological 3 features


class Variability(str, Enum):
    STABLE = "STABLE"
    MODERATE = "MODERATE"
    VARIABLE = "VARIABLE"


class SpecDirection(str, Enum):
    BILATERAL = "BILATERAL"   # μ ± nσ
    UPPER = "UPPER"           # upper limit only


class QualityPhase(str, Enum):
    """Classification priority phase for good/bad separation."""
    PHASE1_DEFECT = "Phase 1: Defect Detection"
    PHASE2_UNIFORMITY = "Phase 2: Uniformity"
    PHASE3_DISTRIBUTION = "Phase 3: Distribution Shape"
    PHASE4_TEXTURE = "Phase 4: Texture Quality"
    PHASE5_SPECTRAL = "Phase 5: Spectral / Optical"
    PHASE6_MORPHOLOGY = "Phase 6: Defect Morphology"


@dataclass
class FeatureSpec:
    id: str
    name: str
    category: str
    group: FeatureGroup
    module: str
    variability: Variability
    direction: SpecDirection
    unit: str = ""
    description: str = ""
    is_critical: bool = False
    gain_corrected: bool = False  # True = use gain-corrected image
    method: str = ""              # how the feature is computed (extraction method)
    physical_meaning: str = ""    # physical meaning of the value
    quality_note: str = ""        # considerations for quality judgment use
    quality_phase: QualityPhase = QualityPhase.PHASE5_SPECTRAL  # classification priority
    classification_guide: str = ""  # practical guide for good/bad separation


# ── Feature definitions (ordered by Quality Phase priority) ──
FEATURE_REGISTRY: List[FeatureSpec] = [

    # ═══════════════════════════════════════════════════════════════════
    # Phase 1: Defect Detection — 결함 탐지 직접 지표 (가장 먼저 확인)
    # ═══════════════════════════════════════════════════════════════════

    # ─── Anomaly (10) ───
    FeatureSpec("anomaly_count", "Total Anomaly Count", "Anomaly", FeatureGroup.A, "anomaly", Variability.VARIABLE, SpecDirection.UPPER, "",
                method="3σ Connected Component 총 개수 (5px 이상)",
                physical_meaning="결함 후보 영역의 총 수",
                quality_note="Count 증가는 산발적 결함 증가. Area%와 함께 해석",
                quality_phase=QualityPhase.PHASE1_DEFECT,
                classification_guide="[분류 핵심] 정상품은 결함 수가 일정 범위 내에 몰려 있고, 불량은 튀어나옴. "
                                     "분포 분리가 가장 명확할 가능성이 높아 1차 스크리닝 지표로 최우선 권장. "
                                     "공정별(Reactor/Densification) 독립적으로 baseline 설정 필요"),
    FeatureSpec("anomaly_area_pct", "Anomaly Area %", "Anomaly", FeatureGroup.A, "anomaly", Variability.VARIABLE, SpecDirection.UPPER, "%", is_critical=True,
                method="3σ 이상점의 총 면적 / 전체 면적 × 100 (%)",
                physical_meaning="이상점이 차지하는 면적 비율. Noise floor 수준 반영",
                quality_note="면적비 상한 관리. Critical feature 후보. 증가 시 전반적 품질 저하",
                quality_phase=QualityPhase.PHASE1_DEFECT,
                classification_guide="[분류 핵심] 결함 개수보다 면적 비율이 실제 수율과 더 직결됨. "
                                     "작은 결함 100개 < 큰 결함 1개. Spec 기반 Pass/Fail 기준을 "
                                     "가장 먼저 설정할 수 있는 Feature"),
    FeatureSpec("max_anomaly_area", "Max Anomaly Area", "Anomaly", FeatureGroup.A, "anomaly", Variability.VARIABLE, SpecDirection.UPPER, "px", is_critical=True,
                method="3σ Connected Component 중 최대 면적 (px). 최소 5px 이상 필터링",
                physical_meaning="가장 큰 단일 결함 크기. Upper Limit 관리 대상",
                quality_note="Critical feature. 대형 결함 1개가 제품 불량 직결. 상한값 엄격 관리",
                quality_phase=QualityPhase.PHASE1_DEFECT,
                classification_guide="[분류 핵심] 치명적 단일 결함 탐지. 정상품은 이 값에 상한이 있을 것이고, "
                                     "불량은 한 개만 커도 걸림. EUV 펠리클에서 대형 결함은 "
                                     "패턴 전사 불량 직결이므로 Zero-tolerance에 가까운 관리 필요"),
    FeatureSpec("texture_anomaly_2sigma", "Texture Anomaly 2\u03c3", "Anomaly", FeatureGroup.A, "anomaly", Variability.VARIABLE, SpecDirection.UPPER, "px",
                method="|x-μ| > 2σ 인 픽셀 수 (양방향, 밝은+어두운 이상점)",
                physical_meaning="느슨한 기준의 이상점 수(양방향). 배경 대비 밝거나 어두운 영역 포함",
                quality_note="2σ는 민감하지만 false positive 높음. 트렌드 모니터링용",
                quality_phase=QualityPhase.PHASE1_DEFECT,
                classification_guide="[보조] 2σ는 민감도가 높아 false positive 포함. "
                                     "단독 판정보다는 3σ/4σ/5σ와 함께 트렌드 변화 모니터링에 활용"),
    FeatureSpec("texture_anomaly_3sigma", "Texture Anomaly 3\u03c3", "Anomaly", FeatureGroup.A, "anomaly", Variability.VARIABLE, SpecDirection.UPPER, "px",
                method="|x-μ| > 3σ 인 픽셀 수 (양방향)",
                physical_meaning="표준적 이상점 수(양방향). 핵심 Baseline 지표",
                quality_note="3σ 기준이 가장 범용적. 공정 관리 기본 지표로 권장",
                quality_phase=QualityPhase.PHASE1_DEFECT,
                classification_guide="[Baseline] 3σ가 가장 범용적인 결함 기준. "
                                     "정상/불량 데이터 축적 후 이 값의 분포를 기반으로 "
                                     "최초 Pass/Fail threshold를 설정하는 것을 권장"),
    FeatureSpec("texture_anomaly_4sigma", "Texture Anomaly 4\u03c3", "Anomaly", FeatureGroup.A, "anomaly", Variability.VARIABLE, SpecDirection.UPPER, "px",
                method="|x-μ| > 4σ 인 픽셀 수 (양방향)",
                physical_meaning="엄격 기준의 이상점 수(양방향)",
                quality_note="실제 결함에 가까운 영역만 카운트. Critical 판정 후보",
                quality_phase=QualityPhase.PHASE1_DEFECT,
                classification_guide="[엄격 기준] 실제 결함에 가까운 영역만 카운트. "
                                     "3σ count가 높더라도 4σ count가 낮으면 미세 noise일 가능성"),
    FeatureSpec("texture_anomaly_5sigma", "Texture Anomaly 5\u03c3", "Anomaly", FeatureGroup.A, "anomaly", Variability.VARIABLE, SpecDirection.UPPER, "px",
                method="|x-μ| > 5σ 인 픽셀 수 (양방향)",
                physical_meaning="최엄격 기준의 이상점 수(양방향). 확실한 이상 영역",
                quality_note="5σ 초과는 거의 확실한 결함. 0이 아니면 주의 필요",
                quality_phase=QualityPhase.PHASE1_DEFECT,
                classification_guide="[확정 결함] 5σ 초과는 거의 확실한 결함. "
                                     "이 값이 0이 아니면 즉시 주의 필요. "
                                     "불량 판정의 최종 확인 지표로 활용"),
    FeatureSpec("mean_anomaly_size", "Mean Anomaly Size", "Anomaly", FeatureGroup.A, "anomaly", Variability.VARIABLE, SpecDirection.UPPER, "px",
                method="3σ Connected Component 평균 면적 (px)",
                physical_meaning="이상점 평균 크기. 결함 스케일 추정",
                quality_note="Mean 증가는 결함이 커지는 추세. Max와 함께 모니터링",
                quality_phase=QualityPhase.PHASE1_DEFECT,
                classification_guide="[트렌드] Mean 증가 추세는 공정 열화 신호. "
                                     "Lot 간 트렌드로 모니터링하면 불량 발생 사전 감지 가능"),
    FeatureSpec("std_anomaly_size", "Std Anomaly Size", "Anomaly", FeatureGroup.A, "anomaly", Variability.VARIABLE, SpecDirection.UPPER, "px",
                method="3σ Connected Component 면적의 표준편차 (px)",
                physical_meaning="이상점 크기 산포. 결함 크기 분포의 균일성",
                quality_note="Std가 크면 결함 크기가 불균일(소수 대형 결함 존재 가능)",
                quality_phase=QualityPhase.PHASE1_DEFECT,
                classification_guide="[보조] Std가 mean보다 훨씬 크면 소수 대형 결함 존재 의미. "
                                     "max_anomaly_area와 교차 확인"),
    FeatureSpec("median_anomaly_size", "Median Anomaly Size (3σ)", "Anomaly", FeatureGroup.A, "anomaly", Variability.VARIABLE, SpecDirection.UPPER, "px",
                method="3σ Connected Component 면적의 중앙값 (px)",
                physical_meaning="이상점 크기 중앙값. 극단값에 강건한 대표값",
                quality_note="Mean 대비 이상치에 덜 민감. 전형적 결함 크기 파악에 적합",
                quality_phase=QualityPhase.PHASE1_DEFECT,
                classification_guide="[보조] Mean보다 이상치에 강건한 대표값. "
                                     "Mean과 Median 괴리가 크면 대형 결함 소수 존재를 의미"),

    # ─── Channel Anomaly (1) ───
    FeatureSpec("chanom_b_3sigma_count", "B-ch 3\u03c3 Count", "Channel Anomaly", FeatureGroup.B, "channel_anomaly", Variability.VARIABLE, SpecDirection.UPPER, "px", gain_corrected=True, is_critical=True,
                method="Gain 보정 B채널에서 |x-μ| > 3σ Connected Component 수 (5px 이상, 양방향)",
                physical_meaning="B 채널 전용 이상점 수(양방향). 나노구조 변화에 가장 민감",
                quality_note="Critical feature 후보. B 채널이 나노 스케일 결함 감지에 최적",
                quality_phase=QualityPhase.PHASE1_DEFECT,
                classification_guide="[분류 핵심] B 채널(~470nm)은 짧은 파장이라 나노구조 변화에 가장 민감. "
                                     "Gray 3σ에서 못 잡는 미세 결함을 B채널에서 추가 포착 가능. "
                                     "Gray anomaly_count와 병행하여 결함 검출률(recall) 향상"),

    # ═══════════════════════════════════════════════════════════════════
    # Phase 2: Uniformity — 공간적 균일성 (공정 안정성 판별)
    # ═══════════════════════════════════════════════════════════════════

    # ─── Uniformity (2) ───
    FeatureSpec("grid_uniformity_std", "Grid Uniformity Std", "Uniformity", FeatureGroup.A, "uniformity", Variability.MODERATE, SpecDirection.UPPER, "DN",
                method="8×8 그리드 각 셀 평균의 표준편차",
                physical_meaning="공간적 밝기 균일성. 낮을수록 균일한 표면",
                quality_note="Upper limit 관리. 코팅 두께 편차, 조명 불균일 모두 영향",
                quality_phase=QualityPhase.PHASE2_UNIFORMITY,
                classification_guide="[분류 핵심] CNT 멤브레인은 두께/밀도 균일성이 핵심 품질. "
                                     "이미지를 8×8 그리드로 쪼개서 각 영역 밝기 편차를 측정하므로 "
                                     "코팅 두께 불균일 = 불량일 때 이 값이 가장 직접적인 지표. "
                                     "주의: Shading=Flatfield 보정이 적용된 상태이므로 조명 불균일 영향은 이미 보정됨"),
    FeatureSpec("grid_uniformity_range", "Grid Uniformity Range", "Uniformity", FeatureGroup.A, "uniformity", Variability.MODERATE, SpecDirection.UPPER, "DN",
                method="8×8 그리드 각 셀 평균의 최대-최소 차이",
                physical_meaning="최대 밝기 편차. 가장 밝은 영역과 어두운 영역 차이",
                quality_note="Range가 크면 국소적 두께 차이 존재. Grid Std와 함께 해석",
                quality_phase=QualityPhase.PHASE2_UNIFORMITY,
                classification_guide="[보조] Grid Std와 함께 사용. Range가 크면 극단적 불균일 영역이 존재. "
                                     "Std는 전체적 불균일, Range는 worst-case 불균일"),

    # ─── Local Contrast (2) ───
    FeatureSpec("local_contrast_mean", "Local Contrast Mean", "Local Contrast", FeatureGroup.A, "local_contrast", Variability.STABLE, SpecDirection.BILATERAL, "DN",
                method="15×15 box filter 기반 local std map의 평균",
                physical_meaning="배경 대비 국소 밝기 변동 평균. 텍스처 강도",
                quality_note="CNT 네트워크의 전형적 텍스처 수준 반영. 급변 시 표면 상태 변화",
                quality_phase=QualityPhase.PHASE2_UNIFORMITY,
                classification_guide="[분류 유효] 국소 밝기 변동의 전체 평균. "
                                     "정상은 전체적으로 고른 값을 보이고, "
                                     "코팅 불균일이나 오염 시 이 값이 정상 범위를 벗어남"),
    FeatureSpec("local_contrast_std", "Local Contrast Std", "Local Contrast", FeatureGroup.A, "local_contrast", Variability.MODERATE, SpecDirection.BILATERAL, "DN",
                method="Local std map의 표준편차",
                physical_meaning="국소 밝기 변동의 공간적 편차",
                quality_note="Std 증가 시 일부 영역의 텍스처가 다름(결함 후보 영역)",
                quality_phase=QualityPhase.PHASE2_UNIFORMITY,
                classification_guide="[보조] Local Contrast의 편차. 정상은 전체적으로 고른 local contrast를 보이고, "
                                     "불량은 특정 영역만 튀는 패턴. Mean보다 공간적 이상 탐지에 민감"),

    # ═══════════════════════════════════════════════════════════════════
    # Phase 3: Distribution Shape — 밝기 분포 형태 (이상 패턴 감지)
    # ═══════════════════════════════════════════════════════════════════

    # ─── Intensity (4) ───
    FeatureSpec("gray_std", "Gray Std", "Intensity", FeatureGroup.A, "intensity", Variability.STABLE, SpecDirection.BILATERAL, "DN", "Std dev of gray values",
                method="전체 픽셀의 그레이스케일 표준편차",
                physical_meaning="표면 밝기 균일성 직접 측정. 높으면 밝기 편차가 큰(불균일한) 표면",
                quality_note="균일성 관리 핵심. Std 증가 시 코팅 불균일 또는 오염 의심",
                quality_phase=QualityPhase.PHASE3_DISTRIBUTION,
                classification_guide="[분류 핵심] 정상품끼리는 std가 좁은 범위에 몰림. "
                                     "gray_mean은 카메라 Exposure(Peak) 자동노출에 따라 샷마다 흔들릴 수 있지만, "
                                     "std는 멤브레인 자체 특성을 더 잘 반영. 균일성 관리의 1차 지표"),
    FeatureSpec("gray_skewness", "Gray Skewness", "Intensity", FeatureGroup.A, "intensity", Variability.MODERATE, SpecDirection.BILATERAL, "", "Skewness of gray histogram",
                method="그레이 히스토그램의 비대칭도 (scipy.stats.skew)",
                physical_meaning="양수=밝은 이상치 존재(파티클), 음수=어두운 이상치(보이드/핀홀)",
                quality_note="비대칭 방향으로 결함 유형 추정 가능. 양의 skew 증가 시 파티클 오염 점검",
                quality_phase=QualityPhase.PHASE3_DISTRIBUTION,
                classification_guide="[분류 핵심] 0에 가까우면 대칭 분포(정상 가능성 높음). "
                                     "양수로 크면 밝은 이상점 존재(핀홀/파티클), "
                                     "음수로 크면 어두운 이상점(오염/두께 이상). "
                                     "결함 유형까지 추정 가능하여 분류와 원인 분석 동시 활용"),
    FeatureSpec("gray_kurtosis", "Gray Kurtosis", "Intensity", FeatureGroup.A, "intensity", Variability.MODERATE, SpecDirection.BILATERAL, "", "Kurtosis of gray histogram",
                method="그레이 히스토그램의 첨도 (scipy.stats.kurtosis, fisher=True)",
                physical_meaning="양수=극단값 많음(결함 시사), 0=정규분포, 음수=플랫",
                quality_note="Kurtosis 급증 시 국소적 밝은/어두운 결함 존재 가능성 높음",
                quality_phase=QualityPhase.PHASE3_DISTRIBUTION,
                classification_guide="[분류 유효] 극단적으로 높으면 소수의 극단값(=결함) 존재. "
                                     "정상은 낮고 안정적. Skewness와 함께 해석하면 "
                                     "결함 유무(kurtosis) + 결함 방향(skewness) 동시 파악 가능"),
    FeatureSpec("gray_mean", "Gray Mean", "Intensity", FeatureGroup.A, "intensity", Variability.STABLE, SpecDirection.BILATERAL, "DN", "Mean gray value",
                method="전체 픽셀의 그레이스케일 평균값 (0~255)",
                physical_meaning="조명·멤브레인 두께·반사율의 종합 지표. 값이 높으면 밝은(얇거나 반사율 높은) 영역",
                quality_note="공정 간 변동 모니터링 핵심 지표. Lot 간 평균 밝기 drift 추적에 활용",
                quality_phase=QualityPhase.PHASE3_DISTRIBUTION,
                classification_guide="[주의] 카메라 Exposure=Peak 설정이므로 자동노출 보정이 걸려 "
                                     "샷마다 mean이 흔들릴 수 있음. 멤브레인 자체 특성보다 "
                                     "촬영 조건 변동을 반영할 수 있으므로 분류보다는 "
                                     "Lot 간 drift 트렌드 모니터링에 활용 권장"),

    # ─── Entropy (3) ───
    FeatureSpec("gray_entropy", "Gray Entropy", "Entropy", FeatureGroup.A, "entropy", Variability.STABLE, SpecDirection.BILATERAL, "bits",
                method="전체 히스토그램의 Shannon Entropy (bits)",
                physical_meaning="밝기 분포의 정보량/복잡성. 높으면 다양한 밝기가 존재",
                quality_note="Entropy 안정성이 높아(CoV < 1%) 미세 변화 감지에 유리",
                quality_phase=QualityPhase.PHASE3_DISTRIBUTION,
                classification_guide="[보조] CoV < 1%로 안정성이 매우 높아 미세 변화 감지에 유리. "
                                     "정상 범위가 매우 좁으므로 조금만 벗어나도 이상 신호"),
    FeatureSpec("local_entropy_mean", "Local Entropy Mean", "Entropy", FeatureGroup.A, "entropy", Variability.STABLE, SpecDirection.BILATERAL, "bits",
                method="skimage rank entropy (disk r=5) 맵의 8×8 그리드 평균",
                physical_meaning="국소 정보량 평균. 미세 결함에 민감",
                quality_note="Local entropy 증가는 국소적 텍스처 변화(결함) 존재 시사",
                quality_phase=QualityPhase.PHASE3_DISTRIBUTION,
                classification_guide="[보조] 미세 결함에 민감한 보조 지표"),
    FeatureSpec("local_entropy_std", "Local Entropy Std", "Entropy", FeatureGroup.A, "entropy", Variability.MODERATE, SpecDirection.BILATERAL, "bits",
                method="Local entropy 맵의 8×8 그리드 표준편차",
                physical_meaning="국소 정보량의 공간적 편차. 결함 분포 균일성",
                quality_note="Std 증가는 일부 영역에만 집중된 결함 패턴 의미",
                quality_phase=QualityPhase.PHASE3_DISTRIBUTION,
                classification_guide="[보조] 일부 영역에만 집중된 결함 패턴 탐지"),

    # ═══════════════════════════════════════════════════════════════════
    # Phase 4: Texture Quality — 텍스처 품질 (CNT 네트워크 구조 반영)
    # ═══════════════════════════════════════════════════════════════════

    # ─── GLCM (4) ───
    FeatureSpec("glcm_contrast", "GLCM Contrast", "GLCM", FeatureGroup.A, "glcm", Variability.STABLE, SpecDirection.BILATERAL, "",
                method="GLCM(Gray-Level Co-occurrence Matrix) Contrast. 인접 픽셀 밝기차의 제곱합. distance=1, angle=0, 원본 해상도",
                physical_meaning="표면 거칠기(roughness) 지표. 높으면 인접 픽셀 간 밝기 변화가 큼",
                quality_note="CNT 네트워크 밀도/균일성 반영. Contrast 증가 시 fiber 분포 불균일 의심",
                quality_phase=QualityPhase.PHASE4_TEXTURE,
                classification_guide="[분류 유효] 인접 픽셀 관계를 보므로 CNT 섬유 네트워크 구조의 건전성을 직접 반영. "
                                     "불량(찢김, 뭉침, 두께 이상)은 이 값이 정상 범위를 벗어남. "
                                     "Homogeneity와 역상관이므로 두 값을 함께 보면 양방향으로 텍스처 이상 포착"),
    FeatureSpec("glcm_homogeneity", "GLCM Homogeneity", "GLCM", FeatureGroup.A, "glcm", Variability.STABLE, SpecDirection.BILATERAL, "",
                method="GLCM Homogeneity. 인접 픽셀 유사도 (1에 가까울수록 균일)",
                physical_meaning="텍스처 균일성. 1=완전 균일, 낮으면 거친 텍스처",
                quality_note="Homogeneity 감소는 표면 거칠기 증가 의미. Contrast와 역상관",
                quality_phase=QualityPhase.PHASE4_TEXTURE,
                classification_guide="[분류 유효] Contrast와 역상관. 두 값을 함께 보면 텍스처 이상을 양방향으로 잡음"),
    FeatureSpec("glcm_energy", "GLCM Energy", "GLCM", FeatureGroup.A, "glcm", Variability.STABLE, SpecDirection.BILATERAL, "",
                method="GLCM Energy (Angular Second Moment). 텍스처 규칙성",
                physical_meaning="높으면 규칙적 패턴, 낮으면 랜덤 텍스처",
                quality_note="CNT 멤브레인은 적당히 낮은 Energy가 정상. 급변 시 이물질/패턴 이상",
                quality_phase=QualityPhase.PHASE4_TEXTURE,
                classification_guide="[보조] 텍스처 규칙성 보조 지표"),
    FeatureSpec("glcm_correlation", "GLCM Correlation", "GLCM", FeatureGroup.A, "glcm", Variability.STABLE, SpecDirection.BILATERAL, "",
                method="GLCM Correlation. 인접 픽셀 선형 상관계수",
                physical_meaning="CNT 네트워크 구조의 공간적 일관성. 높으면 구조가 일정",
                quality_note="공정 안정 시 높은 Correlation 유지. 감소 시 네트워크 구조 변화",
                quality_phase=QualityPhase.PHASE4_TEXTURE,
                classification_guide="[보조] 공정 안정성 모니터링. 감소 추세는 네트워크 구조 열화 신호"),

    # ─── LBP (1) ───
    FeatureSpec("lbp_entropy", "LBP Entropy", "LBP", FeatureGroup.A, "lbp", Variability.STABLE, SpecDirection.BILATERAL, "bits",
                method="LBP(Local Binary Pattern) uniform 히스토그램의 Shannon Entropy. R=1, P=8, 원본 해상도",
                physical_meaning="국소 패턴 다양성. 높으면 다양한 텍스처 존재",
                quality_note="전체 Feature 중 CoV가 가장 낮아 공정 안정성 지표로 우수. 미세 변동 감지",
                quality_phase=QualityPhase.PHASE4_TEXTURE,
                classification_guide="[보조] 전체 60개 Feature 중 CoV가 가장 낮아 정상 범위가 극히 좁음. "
                                     "조금만 벗어나도 이상 신호. 미세 구조 변화 감지의 민감한 지표"),

    # ─── FFT (3) ───
    FeatureSpec("fft_low_freq_ratio", "FFT Low-freq Ratio", "FFT", FeatureGroup.A, "fft", Variability.STABLE, SpecDirection.BILATERAL, "",
                method="2D FFT 후 반경 ≤ max/3 영역의 에너지 비율",
                physical_meaning="저주파 비율. 전체 밝기 구배/비네팅 반영. DC 성분 포함",
                quality_note="대부분의 에너지가 저주파에 집중됨. Mid/High 변화가 더 민감한 지표",
                quality_phase=QualityPhase.PHASE4_TEXTURE,
                classification_guide="[참고] 대부분의 에너지가 집중되어 변동이 작음. Mid/High가 더 유효"),
    FeatureSpec("fft_mid_freq_ratio", "FFT Mid-freq Ratio", "FFT", FeatureGroup.A, "fft", Variability.STABLE, SpecDirection.BILATERAL, "",
                method="2D FFT 후 반경 max/3 ~ 2max/3 영역의 에너지 비율",
                physical_meaning="중주파 비율. 중간 크기 구조물/파티클 군집 반영",
                quality_note="Mid-freq 증가 시 수십~수백 px 스케일의 구조적 변화 존재",
                quality_phase=QualityPhase.PHASE4_TEXTURE,
                classification_guide="[보조] 수십~수백 px 스케일 구조 변화 감지"),
    FeatureSpec("fft_high_freq_ratio", "FFT High-freq Ratio", "FFT", FeatureGroup.A, "fft", Variability.STABLE, SpecDirection.BILATERAL, "",
                method="2D FFT 후 반경 > 2max/3 영역의 에너지 비율",
                physical_meaning="고주파 비율. 미세 텍스처/노이즈/엣지 성분",
                quality_note="High-freq 증가 시 미세 결함이나 노이즈 수준 변화. 카메라 포커스 이상도 영향",
                quality_phase=QualityPhase.PHASE4_TEXTURE,
                classification_guide="[보조] 미세 구조/노이즈 수준. 카메라 포커스 이상 시에도 변화하므로 "
                                     "촬영 품질 검증 용도로도 활용 가능"),

    # ═══════════════════════════════════════════════════════════════════
    # Phase 5: Spectral / Optical — 분광·광학 특성 (파장 의존적 분석)
    # ═══════════════════════════════════════════════════════════════════

    # ─── Color (8) ───
    FeatureSpec("red_mean", "Red Mean", "Color", FeatureGroup.A, "color", Variability.STABLE, SpecDirection.BILATERAL, "DN",
                method="R 채널 픽셀 평균값",
                physical_meaning="Red 파장(~620nm) 응답. CNT fiber 간극과 상호작용하는 장파장 성분",
                quality_note="R/G/B 채널 비율 변화로 나노구조 변화 감지. R 단독보다 채널 간 비율이 더 유의미",
                quality_phase=QualityPhase.PHASE5_SPECTRAL,
                classification_guide="[참고] 단독보다 채널 간 비율(R/B, G/B)이 더 유의미. "
                                     "카메라 Color gain R=1.3 적용 상태"),
    FeatureSpec("green_mean", "Green Mean", "Color", FeatureGroup.A, "color", Variability.STABLE, SpecDirection.BILATERAL, "DN",
                method="G 채널 픽셀 평균값",
                physical_meaning="Green 파장(~530nm) 응답. 중간 파장 대역의 광학 특성 반영",
                quality_note="G 채널은 인간 시각 민감도와 가장 유사. 전체 밝기 변화 추적에 유리",
                quality_phase=QualityPhase.PHASE5_SPECTRAL,
                classification_guide="[참고] 카메라 Color gain G=1.0 (기준 채널)"),
    FeatureSpec("blue_mean", "Blue Mean", "Color", FeatureGroup.A, "color", Variability.STABLE, SpecDirection.BILATERAL, "DN",
                method="B 채널 픽셀 평균값",
                physical_meaning="Blue 파장(~470nm) 응답. 짧은 파장이라 나노구조 변화에 가장 민감",
                quality_note="Densification 후 B>R>G 패턴이 정상. B 채널 변동이 공정 변화 지표로 가장 유효",
                quality_phase=QualityPhase.PHASE5_SPECTRAL,
                classification_guide="[참고] 카메라 Color gain B=0.9 적용 상태. "
                                     "짧은 파장이라 나노구조에 가장 민감"),
    FeatureSpec("rg_diff_mean", "RG Diff Mean", "Color", FeatureGroup.A, "color", Variability.STABLE, SpecDirection.BILATERAL, "DN",
                method="R채널 평균 - G채널 평균",
                physical_meaning="R-G 차이. 재료 조성/코팅 상태 반영",
                quality_note="공정 안정 시 일정한 값 유지. 급변 시 코팅 조건 변화 의심",
                quality_phase=QualityPhase.PHASE5_SPECTRAL,
                classification_guide="[보조] 공정 안정 시 일정한 값 유지. 급변 시 공정 조건 변화 의심"),
    FeatureSpec("rb_diff_mean", "RB Diff Mean", "Color", FeatureGroup.A, "color", Variability.STABLE, SpecDirection.BILATERAL, "DN",
                method="R채널 평균 - B채널 평균",
                physical_meaning="R-B 차이. 음수값은 Blue shift로 Densification 공정 지표",
                quality_note="Densification 정도에 따라 R-B 값이 변화. 공정 제어 파라미터로 활용 가능",
                quality_phase=QualityPhase.PHASE5_SPECTRAL,
                classification_guide="[보조] Densification 정도 반영. 공정별 baseline이 다를 수 있음"),
    FeatureSpec("gb_diff_mean", "GB Diff Mean", "Color", FeatureGroup.A, "color", Variability.STABLE, SpecDirection.BILATERAL, "DN",
                method="G채널 평균 - B채널 평균",
                physical_meaning="G-B 차이. 채널차 중 가장 안정적(CoV 최소)",
                quality_note="안정성이 높아 기준선 설정에 적합. 변동 시 시스템 이상(조명 등) 점검",
                quality_phase=QualityPhase.PHASE5_SPECTRAL,
                classification_guide="[보조] 채널차 중 가장 안정적. 변동 시 시스템 이상(조명 등) 점검"),
    FeatureSpec("saturation_mean", "Saturation Mean", "Color", FeatureGroup.A, "color", Variability.MODERATE, SpecDirection.BILATERAL, "",
                method="HSV 색공간 변환 후 S채널 평균",
                physical_meaning="채도 평균. 오염/변색 시 국소 증가",
                quality_note="Saturation 국소 증가는 이물질이나 변색 지표. 전체 평균보다 분포가 중요",
                quality_phase=QualityPhase.PHASE5_SPECTRAL,
                classification_guide="[보조] 오염/변색 시 국소 채도 변화. 전체 평균보다 분포 해석이 중요"),
    FeatureSpec("saturation_std", "Saturation Std", "Color", FeatureGroup.A, "color", Variability.MODERATE, SpecDirection.BILATERAL, "",
                method="HSV S채널 표준편차",
                physical_meaning="채도 산포. 색 불균일성 측정",
                quality_note="Std 증가 시 국소적 색상 변화 존재. 오염 영역 탐지 보조 지표",
                quality_phase=QualityPhase.PHASE5_SPECTRAL,
                classification_guide="[보조] 오염 영역 탐지 보조 지표"),

    # ─── Spectral Ratio (6) ───
    FeatureSpec("spratio_rb_mean", "R/B Ratio Mean", "Spectral Ratio", FeatureGroup.B, "spectral_ratio", Variability.STABLE, SpecDirection.BILATERAL, "", gain_corrected=True,
                method="Gain 보정 후 (R/B) 비율 맵의 평균. B<1 픽셀 제외",
                physical_meaning="R/B 스펙트럼 비율. 멤브레인 광학 특성의 파장 의존성",
                quality_note="핵심 차별화 Feature. Densification 정도에 따라 민감하게 변화",
                quality_phase=QualityPhase.PHASE5_SPECTRAL,
                classification_guide="[분류 유효] 카메라 Color gain (R=1.3, B=0.9)을 보정한 후의 순수 R/B 비율. "
                                     "멤브레인 광학 특성의 파장 의존성을 직접 반영. "
                                     "공정별로 baseline이 크게 다르므로 반드시 공정 단계별 독립 관리"),
    FeatureSpec("spratio_rb_std", "R/B Ratio Std", "Spectral Ratio", FeatureGroup.B, "spectral_ratio", Variability.MODERATE, SpecDirection.BILATERAL, "", gain_corrected=True,
                method="R/B 비율 맵의 표준편차",
                physical_meaning="R/B 비율의 공간적 편차. 광학 균일성",
                quality_note="Std 증가 시 광학적으로 불균일한 영역 존재",
                quality_phase=QualityPhase.PHASE5_SPECTRAL,
                classification_guide="[보조] Std 증가 시 광학적으로 불균일한 영역 존재"),
    FeatureSpec("spratio_rb_skew", "R/B Ratio Skew", "Spectral Ratio", FeatureGroup.B, "spectral_ratio", Variability.MODERATE, SpecDirection.BILATERAL, "", gain_corrected=True,
                method="R/B 비율 맵의 왜도",
                physical_meaning="R/B 비율 분포의 비대칭성",
                quality_note="Skew 증가 시 국소적 R/B 이상 영역 존재",
                quality_phase=QualityPhase.PHASE5_SPECTRAL,
                classification_guide="[보조] 비정상적 분광 영역 존재 여부. "
                                     "카메라 10bit→8bit 변환 시 양자화 오차가 이 값에 영향을 줄 수 있음"),
    FeatureSpec("spratio_gb_mean", "G/B Ratio Mean", "Spectral Ratio", FeatureGroup.B, "spectral_ratio", Variability.STABLE, SpecDirection.BILATERAL, "", gain_corrected=True,
                method="Gain 보정 후 (G/B) 비율 맵의 평균",
                physical_meaning="G/B 스펙트럼 비율",
                quality_note="R/B와 함께 2차원 스펙트럼 특성 맵핑에 활용",
                quality_phase=QualityPhase.PHASE5_SPECTRAL,
                classification_guide="[보조] R/B와 함께 2차원 스펙트럼 특성 맵핑에 활용"),
    FeatureSpec("spratio_gb_std", "G/B Ratio Std", "Spectral Ratio", FeatureGroup.B, "spectral_ratio", Variability.MODERATE, SpecDirection.BILATERAL, "", gain_corrected=True,
                method="G/B 비율 맵의 표준편차",
                physical_meaning="G/B 비율의 공간적 편차",
                quality_note="R/B Std와 함께 해석. 채널 간 불균일성 종합 평가",
                quality_phase=QualityPhase.PHASE5_SPECTRAL,
                classification_guide="[보조] 채널 간 불균일성 종합 평가"),
    FeatureSpec("spratio_gb_skew", "G/B Ratio Skew", "Spectral Ratio", FeatureGroup.B, "spectral_ratio", Variability.MODERATE, SpecDirection.BILATERAL, "", gain_corrected=True,
                method="G/B 비율 맵의 왜도",
                physical_meaning="G/B 비율 분포의 비대칭성",
                quality_note="Skew 이상은 국소 오염이나 코팅 결함 시사",
                quality_phase=QualityPhase.PHASE5_SPECTRAL,
                classification_guide="[보조] 국소 오염이나 코팅 결함 시사"),

    # ─── Channel Texture (6) ───
    FeatureSpec("chtex_r_contrast", "R GLCM Contrast", "Channel Texture", FeatureGroup.B, "channel_texture", Variability.STABLE, SpecDirection.BILATERAL, "", gain_corrected=True,
                method="Gain 보정된 R채널의 GLCM Contrast",
                physical_meaning="R 파장 대역의 텍스처 거칠기",
                quality_note="채널별 GLCM 비교로 파장 의존적 표면 변화 감지",
                quality_phase=QualityPhase.PHASE5_SPECTRAL,
                classification_guide="[보조] 채널별 GLCM 비교로 파장 의존적 표면 변화 감지"),
    FeatureSpec("chtex_r_homogeneity", "R GLCM Homogeneity", "Channel Texture", FeatureGroup.B, "channel_texture", Variability.STABLE, SpecDirection.BILATERAL, "", gain_corrected=True,
                method="Gain 보정된 R채널의 GLCM Homogeneity",
                physical_meaning="R 파장 대역의 텍스처 균일성",
                quality_note="R 균일성 변화는 장파장 스케일의 구조 변화",
                quality_phase=QualityPhase.PHASE5_SPECTRAL,
                classification_guide="[보조] 장파장 스케일 구조 변화"),
    FeatureSpec("chtex_g_contrast", "G GLCM Contrast", "Channel Texture", FeatureGroup.B, "channel_texture", Variability.STABLE, SpecDirection.BILATERAL, "", gain_corrected=True,
                method="Gain 보정된 G채널의 GLCM Contrast",
                physical_meaning="G 파장 대역의 텍스처 거칠기",
                quality_note="G 채널은 중간 파장. R/B 사이의 전환점 역할",
                quality_phase=QualityPhase.PHASE5_SPECTRAL,
                classification_guide="[보조] 중간 파장 전환점"),
    FeatureSpec("chtex_g_homogeneity", "G GLCM Homogeneity", "Channel Texture", FeatureGroup.B, "channel_texture", Variability.STABLE, SpecDirection.BILATERAL, "", gain_corrected=True,
                method="Gain 보정된 G채널의 GLCM Homogeneity",
                physical_meaning="G 파장 대역의 텍스처 균일성",
                quality_note="G Homogeneity 변화는 중간 스케일 구조 변화",
                quality_phase=QualityPhase.PHASE5_SPECTRAL,
                classification_guide="[보조] 중간 스케일 구조 변화"),
    FeatureSpec("chtex_b_contrast", "B GLCM Contrast", "Channel Texture", FeatureGroup.B, "channel_texture", Variability.STABLE, SpecDirection.BILATERAL, "", gain_corrected=True,
                method="Gain 보정된 B채널의 GLCM Contrast",
                physical_meaning="B 파장 대역의 텍스처 거칠기. 나노구조에 가장 민감",
                quality_note="B Contrast가 가장 민감한 채널. 나노 스케일 변화 우선 감지",
                quality_phase=QualityPhase.PHASE5_SPECTRAL,
                classification_guide="[보조] B 채널이 나노 스케일 변화에 가장 민감"),
    FeatureSpec("chtex_b_homogeneity", "B GLCM Homogeneity", "Channel Texture", FeatureGroup.B, "channel_texture", Variability.STABLE, SpecDirection.BILATERAL, "", gain_corrected=True,
                method="Gain 보정된 B채널의 GLCM Homogeneity",
                physical_meaning="B 파장 대역의 텍스처 균일성",
                quality_note="B Homogeneity 급변은 나노구조 변화의 1차 지표",
                quality_phase=QualityPhase.PHASE5_SPECTRAL,
                classification_guide="[보조] 나노구조 변화의 1차 지표"),

    # ─── Cross-Channel (3) ───
    FeatureSpec("xchan_pearson_rb", "Pearson(R,B)", "Cross-Channel", FeatureGroup.B, "cross_channel", Variability.STABLE, SpecDirection.BILATERAL, "", gain_corrected=True,
                method="Gain 보정된 R/B 채널 간 Pearson 상관계수",
                physical_meaning="R-B 채널 상관성. 높으면 두 채널이 유사한 패턴",
                quality_note="상관계수 급변은 특정 파장에만 영향을 주는 결함(간섭/코팅 결함) 시사",
                quality_phase=QualityPhase.PHASE5_SPECTRAL,
                classification_guide="[보조] 상관계수 급변은 파장 선택적 결함 존재 의미"),
    FeatureSpec("xchan_local_rb_std", "Local R/B Std", "Cross-Channel", FeatureGroup.B, "cross_channel", Variability.MODERATE, SpecDirection.UPPER, "", gain_corrected=True,
                method="R/B 비율 맵의 8×8 그리드 평균의 Std",
                physical_meaning="R/B 비율의 공간적 편차. 국소 광학 불균일성",
                quality_note="Upper limit 관리. 증가 시 국소적 광학 특성 변화",
                quality_phase=QualityPhase.PHASE5_SPECTRAL,
                classification_guide="[보조] 국소적 광학 특성 변화 감지"),
    FeatureSpec("xchan_coherence", "Channel Coherence", "Cross-Channel", FeatureGroup.B, "cross_channel", Variability.STABLE, SpecDirection.BILATERAL, "", gain_corrected=True,
                method="1 - mean(CV per pixel). CV = std(R,G,B)/mean(R,G,B)",
                physical_meaning="채널 간 일관성. 1에 가까울수록 R/G/B 비율이 균일",
                quality_note="Coherence 감소는 특정 채널에만 영향을 주는 이상 발생",
                quality_phase=QualityPhase.PHASE5_SPECTRAL,
                classification_guide="[보조] 특정 채널에만 영향을 주는 이상 발생 감지"),

    # ─── Channel FFT (2) ───
    FeatureSpec("chfft_b_high_ratio", "B High-freq Ratio", "Channel FFT", FeatureGroup.B, "channel_fft", Variability.STABLE, SpecDirection.BILATERAL, "", gain_corrected=True,
                method="Gain 보정 B채널 2D FFT의 고주파(r>2max/3) 에너지 비율",
                physical_meaning="B 채널 고주파 성분. 나노 스케일 텍스처/노이즈",
                quality_note="B 고주파 증가는 미세 결함 증가. R 고주파와 비교하여 파장 의존성 확인",
                quality_phase=QualityPhase.PHASE5_SPECTRAL,
                classification_guide="[보조] B 채널 미세 구조/노이즈 수준"),
    FeatureSpec("chfft_r_high_ratio", "R High-freq Ratio", "Channel FFT", FeatureGroup.B, "channel_fft", Variability.STABLE, SpecDirection.BILATERAL, "", gain_corrected=True,
                method="Gain 보정 R채널 2D FFT의 고주파(r>2max/3) 에너지 비율",
                physical_meaning="R 채널 고주파 성분",
                quality_note="R vs B 고주파 비교로 결함의 파장 의존성 분석",
                quality_phase=QualityPhase.PHASE5_SPECTRAL,
                classification_guide="[보조] R vs B 고주파 비교로 결함의 파장 의존성 분석"),

    # ─── CIELAB (2) ───
    FeatureSpec("cielab_de_mean", "\u0394E Mean", "CIELAB", FeatureGroup.B, "cielab", Variability.STABLE, SpecDirection.BILATERAL, "", gain_corrected=True,
                method="Gain 보정 이미지를 CIE L*a*b* 변환 후 각 픽셀의 ΔE(CIE76) 평균",
                physical_meaning="전체 평균 대비 색차. 색상 균일성의 종합 지표",
                quality_note="ΔE는 인간 시각 기반 색차. 산업 표준 색상 관리 지표",
                quality_phase=QualityPhase.PHASE5_SPECTRAL,
                classification_guide="[보조] 산업 표준 색차 지표. 색상 불균일 종합 평가"),
    FeatureSpec("cielab_local_de_std", "Local \u0394E Std", "CIELAB", FeatureGroup.B, "cielab", Variability.MODERATE, SpecDirection.UPPER, "", gain_corrected=True,
                method="ΔE 맵의 8×8 그리드 평균의 Std",
                physical_meaning="색차의 공간적 편차",
                quality_note="Upper limit 관리. 국소적 색상 이상 영역 탐지",
                quality_phase=QualityPhase.PHASE5_SPECTRAL,
                classification_guide="[보조] 국소적 색상 이상 영역 탐지"),

    # ═══════════════════════════════════════════════════════════════════
    # Phase 6: Defect Morphology — 결함 형태 분석 (불량 원인 분류)
    # ═══════════════════════════════════════════════════════════════════

    # ─── Morphological (3) ───
    FeatureSpec("morph_circularity", "Mean Circularity", "Morphological", FeatureGroup.C, "morphological", Variability.VARIABLE, SpecDirection.BILATERAL, "",
                method="3σ anomaly contour의 4πA/P² 평균. A=면적, P=둘레",
                physical_meaning="결함 형상의 원형도. 1=완전한 원, 낮으면 불규칙 형상",
                quality_note="파티클(원형)과 스크래치(비원형) 구분에 활용",
                quality_phase=QualityPhase.PHASE6_MORPHOLOGY,
                classification_guide="[원인 분류] Good/Bad 이진 분류보다는 Bad의 원인 분석(root cause)에 유용. "
                                     "원형에 가까운 결함(~1.0) = 파티클/이물질, "
                                     "비원형(<0.5) = 크랙/찢어짐/스크래치. "
                                     "불량 판정 후 결함 유형 분류 및 공정 피드백에 활용"),
    FeatureSpec("morph_aspect_ratio", "Mean Aspect Ratio", "Morphological", FeatureGroup.C, "morphological", Variability.VARIABLE, SpecDirection.BILATERAL, "",
                method="3σ anomaly bounding rect의 W/H 평균",
                physical_meaning="결함 종횡비. 1=정사각, 높으면 길쭉한 형상",
                quality_note="높은 aspect ratio는 선형 결함(스크래치, 접힘) 시사",
                quality_phase=QualityPhase.PHASE6_MORPHOLOGY,
                classification_guide="[원인 분류] 길쭉한 결함(>2.0) = 스크래치/접힘/fiber 방향성 결함, "
                                     "정방형(~1.0) = 이물질/파티클. Circularity와 함께 해석"),
    FeatureSpec("morph_solidity", "Mean Solidity", "Morphological", FeatureGroup.C, "morphological", Variability.VARIABLE, SpecDirection.BILATERAL, "",
                method="3σ anomaly의 면적/볼록껍질면적 평균",
                physical_meaning="결함의 밀도. 1=볼록, 낮으면 오목하거나 분기된 형상",
                quality_note="낮은 solidity는 복잡한 형상의 결함. 클러스터링된 다중 결함 가능",
                quality_phase=QualityPhase.PHASE6_MORPHOLOGY,
                classification_guide="[원인 분류] 낮은 solidity(<0.7) = 가지 뻗는 형태의 복잡한 결함 "
                                     "(클러스터, 네트워크 손상). 높은 solidity(>0.9) = 단순 형태(파티클). "
                                     "Circularity, Aspect Ratio와 3종 세트로 결함 유형 종합 분류"),
]

# ── Lookup helpers ──
_REGISTRY_MAP = {f.id: f for f in FEATURE_REGISTRY}


def get_feature(feature_id: str) -> FeatureSpec:
    return _REGISTRY_MAP[feature_id]


def get_features_by_group(group: FeatureGroup) -> List[FeatureSpec]:
    return [f for f in FEATURE_REGISTRY if f.group == group]


def get_features_by_module(module: str) -> List[FeatureSpec]:
    return [f for f in FEATURE_REGISTRY if f.module == module]


def get_critical_features() -> List[FeatureSpec]:
    return [f for f in FEATURE_REGISTRY if f.is_critical]


def get_gain_corrected_features() -> List[FeatureSpec]:
    return [f for f in FEATURE_REGISTRY if f.gain_corrected]


def get_features_by_phase(phase: QualityPhase) -> List[FeatureSpec]:
    return [f for f in FEATURE_REGISTRY if f.quality_phase == phase]
