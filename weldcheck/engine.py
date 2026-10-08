"""Fillet weld design checks to EN 1993-1-8 (EC3, BS EN 1993).

Implements:
- Weld strength per Table 4.1
- Directional method (clause 4.5.3.2)
- Simplified method (clause 4.5.3.3)
- Practical throat sizing limits
"""

from dataclasses import dataclass, field
from math import sqrt

STEEL_GRADES = {
    "S235": {"fu": 360.0, "beta_w": 0.8},
    "S275": {"fu": 430.0, "beta_w": 0.85},
    "S355": {"fu": 510.0, "beta_w": 0.9},
    "S420": {"fu": 520.0, "beta_w": 1.0},
    "S460": {"fu": 540.0, "beta_w": 1.0},
}


@dataclass
class WeldForces:
    """Design forces on the weld group [kN].

    N   : normal force perpendicular to the weld axis
    V_L : shear force along the weld axis (longitudinal)
    V_T : transverse shear, perpendicular to both N and the weld axis
    """

    N: float = 0.0
    V_L: float = 0.0
    V_T: float = 0.0


@dataclass
class WeldInput:
    steel_grade: str = "S235"
    a: float = 3.0  # throat thickness [mm]
    L: float = 100.0  # total weld length [mm]
    gamma_Mw: float = 1.25  # 1.25 recommended; 1.0 with some NA (e.g. UK)
    method: str = "directional"  # "directional" or "simplified"
    forces: WeldForces = field(default_factory=WeldForces)

    @property
    def beta_w(self) -> float:
        return STEEL_GRADES[self.steel_grade]["beta_w"]


@dataclass
class WeldOutput:
    fu: float = 0.0
    beta_w: float = 0.0
    f_vw_d: float = 0.0  # design weld shear strength [N/mm^2]
    sigma_perp: float = 0.0  # normal stress on throat plane [N/mm^2]
    tau_perp: float = 0.0  # shear across throat (transverse) [N/mm^2]
    tau_par: float = 0.0  # shear along weld axis [N/mm^2]
    utilization: float = 0.0
    governed_by: str = ""
    ok: bool = False


def weld_strength(steel_grade: str, gamma_Mw: float) -> tuple:
    """Return (fu, beta_w, f_vw_d) per Table 4.1 of EN 1993-1-8."""
    if steel_grade not in STEEL_GRADES:
        raise ValueError(f"Unknown steel grade: {steel_grade}")
    fu = STEEL_GRADES[steel_grade]["fu"]
    beta_w = STEEL_GRADES[steel_grade]["beta_w"]
    f_vw_d = fu / (beta_w * gamma_Mw)
    return fu, beta_w, f_vw_d


def throat_stresses(w: WeldInput) -> tuple:
    """Resolve forces into stresses on the 45-degree throat plane.

    For an equal-leg fillet weld, a transverse force (N) splits evenly
    into normal and shear on the throat plane (factor sqrt(2)/2), while
    a longitudinal force (V_L) gives pure shear along the axis, and a
    transverse shear (V_T) gives pure shear across the throat.
    """
    F = w.forces
    if w.L <= 0 or w.a <= 0:
        raise ValueError("Weld length and throat thickness must be positive")
    f_n = F.N * 1000.0 / w.L  # N/mm, normal transverse force per unit length
    f_vl = F.V_L * 1000.0 / w.L  # N/mm, longitudinal shear per unit length
    f_vt = F.V_T * 1000.0 / w.L  # N/mm, transverse shear per unit length

    sigma_perp = f_n * sqrt(2.0) / (2.0 * w.a)
    tau_perp = f_n * sqrt(2.0) / (2.0 * w.a) + f_vt / w.a
    tau_par = f_vl / w.a
    return sigma_perp, tau_perp, tau_par


def check_directional(w: WeldInput) -> WeldOutput:
    """Clause 4.5.3.2: both conditions must hold.

    (1) sigma_perp <= f_vw_d
    (2) sqrt(sigma_perp^2 + 3*(tau_perp^2 + tau_par^2)) <= f_vw_d
    """
    fu, beta_w, f_vw_d = weld_strength(w.steel_grade, w.gamma_Mw)
    sigma_perp, tau_perp, tau_par = throat_stresses(w)

    util_normal = abs(sigma_perp) / f_vw_d
    sigma_eff = sqrt(
        sigma_perp ** 2 + 3.0 * (tau_perp ** 2 + tau_par ** 2)
    )
    util_eff = sigma_eff / f_vw_d

    if util_normal >= util_eff:
        util, governed = util_normal, "normal stress (clause 4.5.3.2(1))"
    else:
        util, governed = util_eff, "effective stress (clause 4.5.3.2(2))"

    return WeldOutput(
        fu=fu,
        beta_w=beta_w,
        f_vw_d=f_vw_d,
        sigma_perp=sigma_perp,
        tau_perp=tau_perp,
        tau_par=tau_par,
        utilization=util,
        governed_by=governed,
        ok=util <= 1.0,
    )


def check_simplified(w: WeldInput) -> WeldOutput:
    """Clause 4.5.3.3: resultant force per unit length <= f_vw_d * a.

    With f_vw_d = fu / (sqrt(3) * beta_w * gamma_Mw) the check is exact
    for pure longitudinal shear and conservative for transverse loads.
    """
    fu, beta_w, _ = weld_strength(w.steel_grade, w.gamma_Mw)
    f_vw_d = fu / (sqrt(3.0) * beta_w * w.gamma_Mw)
    F = w.forces
    if w.L <= 0 or w.a <= 0:
        raise ValueError("Weld length and throat thickness must be positive")

    F_res = sqrt(F.N ** 2 + F.V_L ** 2 + F.V_T ** 2) * 1000.0  # N
    f_res = F_res / w.L  # N/mm
    stress = f_res / w.a

    util = stress / f_vw_d
    return WeldOutput(
        fu=fu,
        beta_w=beta_w,
        f_vw_d=f_vw_d,
        sigma_perp=abs(F.N) * 1000.0 / (w.a * w.L),
        tau_perp=abs(F.V_T) * 1000.0 / (w.a * w.L),
        tau_par=abs(F.V_L) * 1000.0 / (w.a * w.L),
        utilization=util,
        governed_by="simplified resultant (clause 4.5.3.3)",
        ok=util <= 1.0,
    )


def check_weld(w: WeldInput) -> WeldOutput:
    if w.a <= 0:
        raise ValueError("Throat thickness must be positive")
    if w.L <= 0:
        raise ValueError("Weld length must be positive")
    if w.method == "directional":
        return check_directional(w)
    if w.method == "simplified":
        return check_simplified(w)
    raise ValueError(f"Unknown method: {w.method}")


def min_throat(t1: float, t2: float) -> float:
    """Practical minimum throat for a full-strength fillet on plate
    thicknesses t1, t2: a >= 0.7 * min(t1, t2), and at least 3 mm."""
    tmin = min(t1, t2)
    return max(3.0, 0.7 * tmin)


def max_throat(t1: float, t2: float) -> float:
    """The throat cannot practically exceed the thinner plate."""
    return min(t1, t2)
