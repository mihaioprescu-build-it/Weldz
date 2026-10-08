"""Tests for the EN 1993-1-8 fillet weld engine."""

from math import isclose, sqrt

import pytest

from weldcheck.engine import (
    STEEL_GRADES,
    WeldForces,
    WeldInput,
    check_weld,
    max_throat,
    min_throat,
    weld_strength,
)


class TestWeldStrength:
    def test_s235_default_beta(self):
        fu, beta_w, f_vw_d = weld_strength("S235", 1.25)
        assert isclose(fu, 360.0)
        assert isclose(beta_w, 0.8)
        assert isclose(f_vw_d, 360.0 / (0.8 * 1.25))

    def test_s355(self):
        fu, beta_w, f_vw_d = weld_strength("S355", 1.25)
        assert isclose(fu, 510.0)
        assert isclose(beta_w, 0.9)
        assert isclose(f_vw_d, 510.0 / (0.9 * 1.25))

    def test_unknown_grade_raises(self):
        with pytest.raises(ValueError):
            weld_strength("S999", 1.25)

    def test_all_grades_have_values(self):
        for grade in STEEL_GRADES:
            fu, beta_w, _ = weld_strength(grade, 1.25)
            assert fu > 0
            assert 0.8 <= beta_w <= 1.0


class TestDirectionalMethod:
    def test_pure_longitudinal_shear(self):
        w = WeldInput(
            steel_grade="S235",
            a=4.0,
            L=100.0,
            method="directional",
            forces=WeldForces(N=0.0, V_L=50.0, V_T=0.0),
        )
        out = check_weld(w)
        # tau_par = 50000 N / (100 mm * 4 mm) = 125 N/mm2
        assert isclose(out.tau_par, 125.0, rel_tol=1e-6)
        assert isclose(out.sigma_perp, 0.0)
        # effective stress = sqrt(3) * 125 = 216.5
        assert isclose(
            sqrt(out.sigma_perp ** 2 + 3 * (out.tau_perp ** 2 + out.tau_par ** 2)),
            sqrt(3.0) * 125.0,
            rel_tol=1e-6,
        )
        assert isclose(out.utilization, sqrt(3.0) * 125.0 / 360.0, rel_tol=1e-6)

    def test_pure_transverse_normal(self):
        w = WeldInput(
            steel_grade="S235",
            a=4.0,
            L=100.0,
            method="directional",
            forces=WeldForces(N=60.0, V_L=0.0, V_T=0.0),
        )
        out = check_weld(w)
        # f_n = 600 N/mm; sigma_perp = tau_perp = f_n * sqrt(2)/2 / a
        expected = 600.0 * sqrt(2.0) / 2.0 / 4.0
        assert isclose(out.sigma_perp, expected, rel_tol=1e-6)
        assert isclose(out.tau_perp, expected, rel_tol=1e-6)
        assert out.ok

    def test_governed_by_effective_when_shear_dominant(self):
        w = WeldInput(
            steel_grade="S235",
            a=3.0,
            L=100.0,
            method="directional",
            forces=WeldForces(N=0.0, V_L=60.0, V_T=0.0),
        )
        out = check_weld(w)
        assert "effective" in out.governed_by

    def test_passing_case(self):
        w = WeldInput(
            steel_grade="S355",
            a=6.0,
            L=150.0,
            method="directional",
            forces=WeldForces(N=100.0, V_L=80.0, V_T=30.0),
        )
        out = check_weld(w)
        assert out.utilization < 1.0
        assert out.ok


class TestSimplifiedMethod:
    def test_resultant_divides_by_area(self):
        w = WeldInput(
            steel_grade="S235",
            a=4.0,
            L=100.0,
            method="simplified",
            forces=WeldForces(N=30.0, V_L=40.0, V_T=0.0),
        )
        out = check_weld(w)
        # resultant = 50 kN = 50000 N over 100 mm at a=4
        # simplified strength f_vw_d = fu / (sqrt(3)*beta_w*gamma_Mw)
        expected = (50000.0 / 100.0 / 4.0) / (360.0 / (sqrt(3.0) * 0.8 * 1.25))
        assert isclose(out.utilization, expected, rel_tol=1e-6)

    def test_equals_directional_for_pure_longitudinal(self):
        forces = WeldForces(N=0.0, V_L=80.0, V_T=0.0)
        w_dir = WeldInput(steel_grade="S235", a=6.0, L=150.0, method="directional", forces=forces)
        w_sim = WeldInput(steel_grade="S235", a=6.0, L=150.0, method="simplified", forces=forces)
        assert isclose(
            check_weld(w_sim).utilization,
            check_weld(w_dir).utilization,
            rel_tol=1e-9,
        )

    def test_conservative_for_transverse_load(self):
        forces = WeldForces(N=100.0, V_L=0.0, V_T=0.0)
        w_dir = WeldInput(steel_grade="S235", a=6.0, L=150.0, method="directional", forces=forces)
        w_sim = WeldInput(steel_grade="S235", a=6.0, L=150.0, method="simplified", forces=forces)
        assert check_weld(w_sim).utilization >= check_weld(w_dir).utilization


class TestValidation:
    def test_zero_throat_raises(self):
        w = WeldInput(a=0.0)
        with pytest.raises(ValueError):
            check_weld(w)

    def test_zero_length_raises(self):
        w = WeldInput(L=0.0)
        with pytest.raises(ValueError):
            check_weld(w)

    def test_unknown_method_raises(self):
        w = WeldInput(method=" banana")
        with pytest.raises(ValueError):
            check_weld(w)

    def test_unknown_grade_raises(self):
        w = WeldInput(steel_grade="S999")
        with pytest.raises(ValueError):
            check_weld(w)


class TestThroatLimits:
    def test_min_throat_scales_with_thinner_plate(self):
        assert isclose(min_throat(10.0, 20.0), 7.0)

    def test_min_throat_floor_3mm(self):
        assert isclose(min_throat(2.0, 3.0), 3.0)

    def test_max_throat_is_thinner_plate(self):
        assert isclose(max_throat(8.0, 12.0), 8.0)
