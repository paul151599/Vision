"""Generate visualization images for each processing phase."""
import numpy as np
import cv2
from pathlib import Path
from typing import Dict, Optional
from PIL import Image

from config.camera import CameraConfig
from config.settings import (
    LOCAL_CONTRAST_KERNEL, ANOMALY_MIN_AREA_PX,
    MORPH_SIGMA,
    ENTROPY_DISK_RADIUS,
)
from core.image_loader import ImageLoader


# ──────────────────────────────────────────────────────────────────────────
# Per-tab image-processing explanations (shown via the GUI "ⓘ 처리 설명" button).
# Keys MUST match the tab_id values used in gui/app.py and the result keys
# produced by render_all_phases() below. Keep these in sync when changing the
# rendering logic.
# ──────────────────────────────────────────────────────────────────────────
PHASE_DESCRIPTIONS = {
    "Original": {
        "title": "Original (원본)",
        "purpose": "촬영된 원본 BMP를 그대로 확인하는 화면. 어떤 이미지 처리도 적용되지 않은 입력 기준점이며, 모든 후속 분석은 이 원본에서 출발한다.",
        "method": "BMP를 BGR(uint8)로 로드 → 화면 표시를 위해 긴 변이 1200px가 되도록 축소(INTER_AREA) → BGR을 RGB로 변환하여 표시. (색/밝기 값 자체는 변형하지 않음, 단순 리사이즈만)",
        "interpret": "초점·노출·전체적인 밝기/색감, 눈에 보이는 큰 오염이나 결함을 1차로 확인한다.",
        "related": "전체 60개 feature의 입력 원본",
    },
    "Grayscale": {
        "title": "Grayscale (그레이스케일)",
        "purpose": "색 정보를 제거하고 밝기(휘도)만 남긴 영상. 형태/텍스처/결함 분석의 공통 입력.",
        "method": "cv2.COLOR_BGR2GRAY 변환 (휘도 = 0.299·R + 0.587·G + 0.114·B). 표시는 원본과 동일 비율로 축소.",
        "interpret": "밝기 분포·균일성·텍스처를 색의 방해 없이 본다. Group A의 거의 모든 feature가 이 영상에서 계산된다.",
        "related": "gray_mean/std/skewness/kurtosis, GLCM, LBP, FFT, anomaly, 균일성, entropy, local contrast",
    },
    "Channels": {
        "title": "Channels (R/G/B 채널 분리)",
        "purpose": "원본을 파장별 3개 센서(R≈620nm, G≈530nm, B≈470nm)로 나눠 본다. CNT 나노구조는 가시광과 같은 스케일이라 채널별 응답이 다르다.",
        "method": "원본을 R/G/B로 분리 → 2×2 그리드(Original + R + G + B)로 배치. 각 채널은 보기 편하도록 ① 그레이로 변환 후 ② 히스토그램 평활화(대비 강조) ③ 채널 색조를 30% 블렌딩하여 표시.",
        "interpret": "⚠️ 시각화는 '대비 강조된 보기용'이라 실제 픽셀값과 다르다(평활화됨). 채널 간 구조/밝기 차이의 정성적 비교용이며, 정량값은 Color/Spectral feature를 참조.",
        "related": "red/green/blue_mean, rg/rb/gb_diff_mean (raw 채널 기반)",
    },
    "GainCorrected": {
        "title": "Gain Corrected (gain 역보정 채널)",
        "purpose": "카메라가 채널별로 먹인 아날로그 gain(R=1.3, G=1.0, B=0.9)을 제거해 물리적으로 의미 있는 분광 응답을 복원한 채널.",
        "method": "보정값 = raw 픽셀 / gain (채널별). 보정된 R/G/B를 Channels 탭과 동일한 2×2 그리드로 표시('Corrected' 라벨). 시각화는 동일하게 대비 강조 처리.",
        "interpret": "Group B(광학물리) feature는 모두 이 보정 채널에서 계산된다. 장비/촬영 조건의 gain 영향을 제거한 '순수' 분광 특성을 본다.",
        "related": "spratio_*, chtex_*, xchan_*, chfft_*, chanom_b_3sigma_count, cielab_* (모두 gain 보정 사용)",
    },
    "FFT": {
        "title": "FFT Spectrum (주파수 스펙트럼)",
        "purpose": "이미지를 공간 주파수 영역으로 변환해, 구조가 '얼마나 크고 미세한 스케일'로 분포하는지 본다.",
        "method": "그레이 영상 2D FFT → fftshift(저주파를 중앙으로 이동) → 크기에 log(1+|F|) → INFERNO 컬러맵. 중심에서 반경 max/3, 2max/3 위치에 원(녹색=Low/Mid 경계, 노랑=Mid/High 경계)을 표시.",
        "interpret": "중앙(저주파)=전체 밝기 구배·비네팅, 중간=수십~수백 px 구조, 바깥(고주파)=미세 텍스처·노이즈·엣지. 별 모양/직선은 규칙적 패턴을 의미. 포커스 이상 시 고주파가 약해진다.",
        "related": "fft_low_freq_ratio, fft_mid_freq_ratio, fft_high_freq_ratio",
    },
    "Anomaly": {
        "title": "Anomaly Map (이상점 맵)",
        "purpose": "이미지 자체의 통계에서 크게 벗어난 픽셀(이상점)을 표시. '절대 기준'이 아니라 그 이미지 내부의 상대적 편차임에 유의.",
        "method": "그레이의 평균 μ, 표준편차 σ 계산 → |픽셀 − μ| > 3σ 인 영역(밝거나 어두운 양방향)을 빨강으로 오버레이(원본과 0.6:0.4 블렌딩) → 윤곽선 노랑. 상단에 5px 이상 영역 수와 면적%를 표시.",
        "interpret": "여기 보이는 영역 수/면적이 anomaly_count·anomaly_area_pct feature와 일치한다(양방향 기준으로 통일됨). 밝은 점=파티클 후보, 어두운 점=핀홀/보이드 후보.",
        "related": "anomaly_count, anomaly_area_pct, max_anomaly_area, texture_anomaly_2~5sigma 외",
    },
    "LocalContrast": {
        "title": "Local Contrast (국소 대비 맵)",
        "purpose": "각 위치 주변의 밝기 변동(텍스처 강도)이 얼마나 큰지를 공간 맵으로 본다.",
        "method": "그레이에 15×15 box filter로 국소 평균과 국소 제곱평균을 구해 국소 표준편차 = √(E[X²] − E[X]²) 계산 → HOT 컬러맵. 상단에 맵의 평균/표준편차 표시.",
        "interpret": "밝을수록(붉을수록) 국소 변동이 큰 영역=텍스처가 거칠거나 경계가 많은 곳. 정상 표면은 전체적으로 고르게 나타나고, 오염/불균일 영역만 튀어 보인다.",
        "related": "local_contrast_mean, local_contrast_std",
    },
    "Entropy": {
        "title": "Entropy Map (국소 엔트로피 맵)",
        "purpose": "각 위치 주변의 밝기 분포가 얼마나 복잡(다양)한지를 정보량으로 본다.",
        "method": "그레이에 skimage rank.entropy(반경 5 원형 윈도)를 적용 — 각 픽셀 주변 원형 영역의 Shannon 엔트로피 → VIRIDIS 컬러맵. 상단에 평균/표준편차 표시.",
        "interpret": "밝을수록 국소 정보량이 높음=다양한 밝기가 섞인 복잡한 텍스처. 균일한 면은 낮고, 미세 결함·구조 변화 영역은 높게 나타난다.",
        "related": "local_entropy_mean, local_entropy_std (gray_entropy는 전역값)",
    },
    "CIELAB": {
        "title": "CIELAB ΔE (색차 맵)",
        "purpose": "인간 시각 기반 색공간에서 '이미지 평균색 대비 각 위치의 색차'를 본다. 색 균일성 평가.",
        "method": "gain 보정 채널을 BGR로 재조합 → CIE L*a*b* 변환 → 이미지 전체 평균색(L,a,b)을 기준으로 픽셀별 ΔE(CIE76: L·a·b 차이의 유클리드 거리) 계산 → MAGMA 컬러맵. 상단에 평균 ΔE 표시.",
        "interpret": "밝을수록 평균색에서 멀리 벗어난(색이 다른) 영역=변색/오염/코팅 불균일 후보. 기준이 '그 이미지 자체의 평균색'이므로 상대 색차임.",
        "related": "cielab_de_mean, cielab_local_de_std",
    },
    "Morphology": {
        "title": "Morphology (결함 형태 분석)",
        "purpose": "검출된 이상 영역의 '모양'을 분석해 결함 유형(파티클 vs 스크래치 등)을 추정한다.",
        "method": "3σ anomaly 마스크의 각 윤곽(5px 이상)에 대해 원형도(4πA/P²)를 계산 → 색으로 코딩(녹색=원형≈1.0, 빨강=비원형) + bounding rect(청록 사각형) 표시. 상단에 객체 수 표시.",
        "interpret": "원형(녹색)≈파티클/이물질, 길쭉하거나 비원형(빨강)≈스크래치/크랙/접힘. Good/Bad 이진판정보다 불량의 '원인 분류'에 쓰인다.",
        "related": "morph_circularity, morph_aspect_ratio, morph_solidity",
    },
}


def _cv2_to_pil(img: np.ndarray) -> Image.Image:
    """Convert OpenCV image (BGR or gray) to PIL Image."""
    if len(img.shape) == 2:
        return Image.fromarray(img, mode="L")
    return Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))


def _colormap(gray: np.ndarray, cmap=cv2.COLORMAP_JET) -> np.ndarray:
    """Apply colormap to normalized grayscale array."""
    normalized = np.clip(gray, 0, None)
    if normalized.max() > 0:
        normalized = (normalized / normalized.max() * 255).astype(np.uint8)
    else:
        normalized = np.zeros_like(gray, dtype=np.uint8)
    return cv2.applyColorMap(normalized, cmap)


def _make_channel_vis(ch_data: np.ndarray, tint_bgr: tuple) -> np.ndarray:
    """Create channel visualization: grayscale structure + light color tint.

    Shows the actual texture/detail of each channel while keeping
    a subtle color identity (R=red tint, G=green, B=blue).
    """
    gray = np.clip(ch_data, 0, 255).astype(np.uint8)
    # Normalize to enhance contrast within the channel
    gray_eq = cv2.equalizeHist(gray)
    # Convert to 3-channel grayscale
    base = cv2.cvtColor(gray_eq, cv2.COLOR_GRAY2BGR)
    # Create color tint layer
    tint = np.full_like(base, tint_bgr, dtype=np.uint8)
    # Blend: 70% grayscale detail + 30% color tint
    blended = cv2.addWeighted(base, 0.7, tint, 0.3, 0)
    return blended


def _make_channel_composite(
    r: np.ndarray, g: np.ndarray, b: np.ndarray,
    bgr_orig: np.ndarray, display_scale: float,
    title_prefix: str = "",
) -> Image.Image:
    """Create 2x2 grid (Original + R/G/B channels), same overall size as other phases."""
    h, w = r.shape

    # Channel visualizations with grayscale detail + color tint
    r_vis = _make_channel_vis(r, (60, 60, 200))   # red tint in BGR
    g_vis = _make_channel_vis(g, (60, 180, 60))    # green tint
    b_vis = _make_channel_vis(b, (200, 60, 60))    # blue tint

    # Each cell = half the display size
    cell_scale = display_scale * 0.5
    ch, cw = int(h * cell_scale), int(w * cell_scale)

    orig_small = cv2.resize(bgr_orig, (cw, ch), interpolation=cv2.INTER_AREA)
    r_small = cv2.resize(r_vis, (cw, ch), interpolation=cv2.INTER_AREA)
    g_small = cv2.resize(g_vis, (cw, ch), interpolation=cv2.INTER_AREA)
    b_small = cv2.resize(b_vis, (cw, ch), interpolation=cv2.INTER_AREA)

    # Add labels on each cell
    font = cv2.FONT_HERSHEY_SIMPLEX
    label_cfg = [
        (orig_small, f"{title_prefix}Original", (255, 255, 255)),
        (r_small, f"{title_prefix}R Channel", (150, 150, 255)),
        (g_small, f"{title_prefix}G Channel", (150, 255, 150)),
        (b_small, f"{title_prefix}B Channel", (255, 150, 150)),
    ]
    labeled = []
    for img, text, color in label_cfg:
        cv2.putText(img, text, (8, 24), font, 0.7, color, 2, cv2.LINE_AA)
        labeled.append(img)

    # 2x2 grid
    top_row = np.hstack([labeled[0], labeled[1]])
    bot_row = np.hstack([labeled[2], labeled[3]])
    composite = np.vstack([top_row, bot_row])

    return _cv2_to_pil(composite)


def render_all_phases(image_path: str, camera_config: Optional[CameraConfig] = None) -> Dict[str, Image.Image]:
    """Render all processing phase visualizations.

    Returns:
        Dict mapping phase tab_id to PIL Image
    """
    camera_config = camera_config or CameraConfig()
    loader = ImageLoader(camera_config)
    data = loader.prepare(image_path)

    results = {}

    # 1. Original
    bgr = data["bgr"]
    # Downsample for display
    display_size = 1200
    h, w = bgr.shape[:2]
    scale = display_size / max(h, w)

    bgr_small = cv2.resize(bgr, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
    results["Original"] = _cv2_to_pil(bgr_small)

    # 2. Grayscale
    gray = data["gray"]
    gray_small = cv2.resize(gray, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
    results["Grayscale"] = _cv2_to_pil(gray_small)

    # 3. Channels (RGB as-captured) — 2×2 grid with original
    results["Channels"] = _make_channel_composite(
        data["R"], data["G"], data["B"], bgr, scale, title_prefix=""
    )

    # 4. Gain-corrected channels — 2×2 grid
    results["GainCorrected"] = _make_channel_composite(
        data["R_corr"], data["G_corr"], data["B_corr"], bgr, scale, title_prefix="Corrected "
    )

    # 5. FFT spectrum
    gray_f = gray.astype(np.float64)
    f = np.fft.fft2(gray_f)
    fshift = np.fft.fftshift(f)
    magnitude = np.log1p(np.abs(fshift))
    mag_norm = (magnitude / magnitude.max() * 255).astype(np.uint8) if magnitude.max() > 0 else np.zeros_like(gray)
    fft_color = cv2.applyColorMap(mag_norm, cv2.COLORMAP_INFERNO)

    # Draw frequency band circles
    cy, cx = gray.shape[0] // 2, gray.shape[1] // 2
    max_r = min(cy, cx)
    cv2.circle(fft_color, (cx, cy), int(max_r / 3), (0, 255, 0), 2)
    cv2.circle(fft_color, (cx, cy), int(max_r * 2 / 3), (0, 255, 255), 2)

    # Add legend
    cv2.putText(fft_color, "Low", (cx + int(max_r / 3) + 5, cy),
                cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 0), 2)
    cv2.putText(fft_color, "Mid", (cx + int(max_r * 2 / 3) + 5, cy),
                cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 255), 2)

    fft_small = cv2.resize(fft_color, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
    results["FFT"] = _cv2_to_pil(fft_small)

    # 6. Anomaly detection (3σ mask overlay)
    mean_val = np.mean(gray_f)
    std_val = np.std(gray_f, ddof=0)
    mask_3sigma = (np.abs(gray_f - mean_val) > 3 * std_val).astype(np.uint8)

    # Create overlay: original + red anomaly regions
    overlay = bgr.copy()
    overlay[mask_3sigma == 1] = [0, 0, 255]  # Red for anomalies
    blended = cv2.addWeighted(bgr, 0.6, overlay, 0.4, 0)

    # Draw contours
    contours, _ = cv2.findContours(mask_3sigma, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    cv2.drawContours(blended, contours, -1, (0, 255, 255), 1)

    # Add stats text
    anomaly_count = sum(1 for cnt in contours if cv2.contourArea(cnt) >= ANOMALY_MIN_AREA_PX)
    area_ratio = np.sum(mask_3sigma) / mask_3sigma.size * 100
    cv2.putText(blended, f"3-sigma Anomalies: {anomaly_count} regions", (20, 50),
                cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 255, 255), 3)
    cv2.putText(blended, f"Area: {area_ratio:.3f}%", (20, 100),
                cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 255, 255), 3)

    blended_small = cv2.resize(blended, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
    results["Anomaly"] = _cv2_to_pil(blended_small)

    # 7. Local Contrast map
    ksize = LOCAL_CONTRAST_KERNEL
    local_mean = cv2.blur(gray_f, (ksize, ksize))
    local_sq_mean = cv2.blur(gray_f ** 2, (ksize, ksize))
    local_var = np.maximum(local_sq_mean - local_mean ** 2, 0)
    local_std_map = np.sqrt(local_var)

    lc_color = _colormap(local_std_map, cv2.COLORMAP_HOT)

    # Add colorbar info
    cv2.putText(lc_color, f"Local Contrast (kernel={ksize})", (20, 50),
                cv2.FONT_HERSHEY_SIMPLEX, 1.5, (255, 255, 255), 3)
    cv2.putText(lc_color, f"Mean: {np.mean(local_std_map):.2f}  Std: {np.std(local_std_map):.2f}", (20, 100),
                cv2.FONT_HERSHEY_SIMPLEX, 1.2, (255, 255, 255), 2)

    lc_small = cv2.resize(lc_color, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
    results["LocalContrast"] = _cv2_to_pil(lc_small)

    # 8. Local Entropy map
    from skimage.filters.rank import entropy as sk_entropy
    from skimage.morphology import disk
    selem = disk(ENTROPY_DISK_RADIUS)
    local_ent = sk_entropy(gray, selem).astype(np.float64)

    ent_color = _colormap(local_ent, cv2.COLORMAP_VIRIDIS)
    cv2.putText(ent_color, f"Local Entropy (r={ENTROPY_DISK_RADIUS})", (20, 50),
                cv2.FONT_HERSHEY_SIMPLEX, 1.5, (255, 255, 255), 3)
    cv2.putText(ent_color, f"Mean: {np.mean(local_ent):.2f}  Std: {np.std(local_ent):.2f}", (20, 100),
                cv2.FONT_HERSHEY_SIMPLEX, 1.2, (255, 255, 255), 2)

    ent_small = cv2.resize(ent_color, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
    results["Entropy"] = _cv2_to_pil(ent_small)

    # 9. CIELAB ΔE map
    r_corr = np.clip(data["R_corr"], 0, 255).astype(np.uint8)
    g_corr = np.clip(data["G_corr"], 0, 255).astype(np.uint8)
    b_corr = np.clip(data["B_corr"], 0, 255).astype(np.uint8)
    bgr_corr = np.stack([b_corr, g_corr, r_corr], axis=-1)
    lab = cv2.cvtColor(bgr_corr, cv2.COLOR_BGR2LAB).astype(np.float64)

    l_mean = np.mean(lab[:, :, 0])
    a_mean = np.mean(lab[:, :, 1])
    b_mean_lab = np.mean(lab[:, :, 2])
    de = np.sqrt((lab[:, :, 0] - l_mean) ** 2 + (lab[:, :, 1] - a_mean) ** 2 + (lab[:, :, 2] - b_mean_lab) ** 2)

    de_color = _colormap(de, cv2.COLORMAP_MAGMA)
    cv2.putText(de_color, "CIE L*a*b* Delta-E", (20, 50),
                cv2.FONT_HERSHEY_SIMPLEX, 1.5, (255, 255, 255), 3)
    cv2.putText(de_color, f"Mean dE: {np.mean(de):.2f}", (20, 100),
                cv2.FONT_HERSHEY_SIMPLEX, 1.2, (255, 255, 255), 2)

    de_small = cv2.resize(de_color, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
    results["CIELAB"] = _cv2_to_pil(de_small)

    # 10. Morphological analysis overlay
    morph_overlay = bgr.copy()
    morph_mask = (np.abs(gray_f - mean_val) > MORPH_SIGMA * std_val).astype(np.uint8)
    morph_contours, _ = cv2.findContours(morph_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    valid_contours = [cnt for cnt in morph_contours if cv2.contourArea(cnt) >= ANOMALY_MIN_AREA_PX]

    for cnt in valid_contours:
        area = cv2.contourArea(cnt)
        perimeter = cv2.arcLength(cnt, True)
        circ = 4 * np.pi * area / (perimeter ** 2) if perimeter > 0 else 0

        # Color by circularity: green (circular) → red (irregular)
        color_val = int(circ * 255)
        color = (0, color_val, 255 - color_val)
        cv2.drawContours(morph_overlay, [cnt], -1, color, 2)

        # Draw bounding rect
        x, y, bw, bh = cv2.boundingRect(cnt)
        cv2.rectangle(morph_overlay, (x, y), (x + bw, y + bh), (255, 255, 0), 1)

    cv2.putText(morph_overlay, f"Morphological: {len(valid_contours)} objects", (20, 50),
                cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 255, 255), 3)
    cv2.putText(morph_overlay, "Green=Circular  Red=Irregular", (20, 100),
                cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 255, 255), 2)

    morph_small = cv2.resize(morph_overlay, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
    results["Morphology"] = _cv2_to_pil(morph_small)

    return results
