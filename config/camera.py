"""Camera configuration for gain correction."""
from dataclasses import dataclass, field
from typing import Dict


@dataclass
class CameraConfig:
    """Camera gain / gamma settings for optical correction.

    Default gains reflect the microscope's per-channel analog gain:
      R=1.3, G=1.0, B=0.9
    Gain-corrected pixel = raw pixel / gain (per channel).
    """
    r_gain: float = 1.3
    g_gain: float = 1.0
    b_gain: float = 0.9
    gamma: float = 1.0

    @property
    def gains(self) -> Dict[str, float]:
        return {"R": self.r_gain, "G": self.g_gain, "B": self.b_gain}

    def to_dict(self) -> dict:
        return {
            "r_gain": self.r_gain,
            "g_gain": self.g_gain,
            "b_gain": self.b_gain,
            "gamma": self.gamma,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "CameraConfig":
        return cls(**{k: d[k] for k in ("r_gain", "g_gain", "b_gain", "gamma") if k in d})


# ──────────────────────────────────────────────────────────────────────────
# Reference capture conditions — shown in the GUI (View → Capture Conditions)
# so every operator shoots under identical settings. Measured values verified
# against the R20-11377 BMP set (4096×3000, 8-bit/ch, uncompressed). This is
# documentation; the pipeline only consumes the gains via CameraConfig above.
# ──────────────────────────────────────────────────────────────────────────
CAPTURE_EQUIPMENT = "Olympus OM (현미경) + Preciv Pro (소프트웨어)"

CAPTURE_CONDITIONS = [
    # (항목, 설정값, 비고)
    ("Color mode", "RGB", ""),
    ("Bit depth", "8-bit RGB color", "채널당 8-bit · BMP 24bpp (실측)"),
    ("Color space", "sRGB", ""),
    ("Gamma", "1 (Linear)", "선형 응답 (밝기 ∝ DN)"),
    ("Sharpness", "2", ""),
    ("Contrast", "0", ""),
    ("Shading", "Flatfield", "조명 불균일은 장비단에서 보정됨"),
    ("Color gain R / G / B", "1.3 / 1.0 / 0.9", "코드의 gain 역보정에 실제 사용"),
    ("Exposure", "Peak", "자동노출 → gray_mean 샷마다 변동 주의"),
    ("Resolution", "Super High", "실측 4096 × 3000"),
    ("File format", "BMP (무압축)", "24bpp · 약 36.9 MB/장"),
]

CAPTURE_NOTES = (
    "• 위 조건을 모든 촬영에서 동일하게 유지해야 이미지 간/Lot 간 데이터 비교가 유효합니다.\n"
    "• Reactor / Densification 공정은 같은 조건으로 각각 촬영하되, baseline(기준선)은 공정별 독립 관리합니다.\n"
    "• 10-bit 정밀도가 필요하면 BMP가 아닌 16-bit TIFF로 저장해야 합니다 "
    "(BMP로 저장하는 순간 8-bit로 이미 손실되어 사후 복원 불가).\n"
    "• gray_mean 등 절대 밝기 지표는 Exposure=Peak(자동노출) 영향으로 흔들릴 수 있어, "
    "정상/불량 분류보다 Lot 간 trend 모니터링용으로 해석하는 것이 안전합니다."
)
