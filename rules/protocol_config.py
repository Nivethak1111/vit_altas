"""
Configurable Protocol Rules Representation
Defines protocol versions, rule parameters, and version differences.
Reusable by FindingEngine, AnswerEngine, and the Protocol Viewer UI.
Zero hardcoding of clinical constants into UI components.
"""
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ProtocolRuleConfig:
    version: str  # "v1", "v2", "v3"
    effective_cuts: List[int]
    visit_window_days: int
    prohibited_medication_classes: List[str]
    prohibited_medication_keywords: List[str]
    screening_age_min: int = 18
    screening_age_max: int = 75
    screening_hba1c_min: float = 7.0
    screening_hba1c_max: float = 10.5
    metformin_stability_weeks: int = 8
    hepatic_alt_ast_uln_multiplier: float = 2.0
    pregnancy_excluded: bool = True
    creatinine_max_mg_dl: Optional[float] = None  # None for v1, 1.5 for v2+
    hys_law_alt_ast_multiplier: float = 3.0
    hys_law_tbil_multiplier: float = 2.0
    hys_law_window_days: int = 14
    hys_law_alp_cholestasis_multiplier: float = 2.0
    sae_reporting_hours: int = 24
    major_changes: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "version": self.version,
            "effective_cuts": self.effective_cuts,
            "visit_window_days": self.visit_window_days,
            "visit_window_display": f"±{self.visit_window_days} days",
            "prohibited_medication_classes": self.prohibited_medication_classes,
            "prohibited_medication_keywords": self.prohibited_medication_keywords,
            "screening_age": f"{self.screening_age_min}–{self.screening_age_max} years",
            "screening_hba1c": f"{self.screening_hba1c_min}%–{self.screening_hba1c_max}%",
            "metformin_stability": f"≥{self.metformin_stability_weeks} weeks ({self.metformin_stability_weeks * 7} days)",
            "hepatic_exclusion": f"ALT/AST > {self.hepatic_alt_ast_uln_multiplier}× ULN",
            "creatinine_exclusion": f"Creatinine > {self.creatinine_max_mg_dl} mg/dL" if self.creatinine_max_mg_dl else "None (Not restricted in v1)",
            "sae_reporting_window": f"{self.sae_reporting_hours} hours from awareness",
            "major_changes": self.major_changes,
        }


class ProtocolRegistry:
    """Registry of protocol versions and rule parameters."""
    CONFIGS: Dict[str, ProtocolRuleConfig] = {
        "v1": ProtocolRuleConfig(
            version="v1",
            effective_cuts=[1],
            visit_window_days=7,
            prohibited_medication_classes=["GLUCOCORTICOIDS", "CORTICOSTEROIDS"],
            prohibited_medication_keywords=[
                "PREDNISONE", "PREDNISOLONE", "DEXAMETHASONE", "METHYLPREDNISOLONE",
                "HYDROCORTISONE", "TRIAMCINOLONE", "BETAMETHASONE"
            ],
            creatinine_max_mg_dl=None,
            major_changes=["Initial trial protocol baseline."]
        ),
        "v2": ProtocolRuleConfig(
            version="v2",
            effective_cuts=[2],
            visit_window_days=3,
            prohibited_medication_classes=["GLUCOCORTICOIDS", "CORTICOSTEROIDS"],
            prohibited_medication_keywords=[
                "PREDNISONE", "PREDNISOLONE", "DEXAMETHASONE", "METHYLPREDNISOLONE",
                "HYDROCORTISONE", "TRIAMCINOLONE", "BETAMETHASONE"
            ],
            creatinine_max_mg_dl=1.5,
            major_changes=[
                "Visit window narrowed from ±7 days to ±3 days.",
                "Renal safety exclusion added: Serum Creatinine > 1.5 mg/dL at screening."
            ]
        ),
        "v3": ProtocolRuleConfig(
            version="v3",
            effective_cuts=[3],
            visit_window_days=3,
            prohibited_medication_classes=["GLUCOCORTICOIDS", "CORTICOSTEROIDS", "SULFONYLUREAS"],
            prohibited_medication_keywords=[
                "PREDNISONE", "PREDNISOLONE", "DEXAMETHASONE", "METHYLPREDNISOLONE",
                "HYDROCORTISONE", "TRIAMCINOLONE", "BETAMETHASONE",
                "GLIMEPIRIDE", "GLIPIZIDE", "GLIBENCLAMIDE", "GLYBURIDE", "GLICLAZIDE"
            ],
            creatinine_max_mg_dl=1.5,
            major_changes=[
                "Sulfonylureas added to prohibited concomitant medication rules.",
                "Visit window remains ±3 days.",
                "Serum Creatinine > 1.5 mg/dL screening exclusion remains active."
            ]
        ),
    }

    @classmethod
    def get_config(cls, version: str) -> ProtocolRuleConfig:
        clean = (version or "v1").lower().strip()
        for k, cfg in cls.CONFIGS.items():
            if k in clean:
                return cfg
        return cls.CONFIGS["v1"]

    @classmethod
    def get_all_configs(cls) -> List[Dict[str, Any]]:
        return [cfg.to_dict() for cfg in cls.CONFIGS.values()]
