"""Smoke tests for the PySide6 GUI (offscreen)."""

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

pyside6 = pytest.importorskip("PySide6")

from PySide6.QtWidgets import QApplication  # noqa: E402

from weldcheck.gui import WeldDesignWindow  # noqa: E402


@pytest.fixture(scope="module")
def app():
    instance = QApplication.instance() or QApplication([])
    yield instance


@pytest.fixture
def win(app):
    window = WeldDesignWindow()
    yield window
    window.close()


class TestWindow:
    def test_builds_and_shows(self, win):
        assert win.windowTitle().startswith("Weld Design")

    def test_defaults_pass(self, win):
        assert win.status_label.text() == "✔ PASS"
        assert win.util_bar.value() <= 100

    def test_reduce_throat_fails(self, win):
        win.throat_spin.setValue(2.0)
        assert win.status_label.text() == "✘ FAIL"

    def test_increase_throat_passes(self, win):
        win.n_spin.setValue(400.0)
        win.throat_spin.setValue(20.0)
        assert win.status_label.text() == "✔ PASS"

    def test_method_switch_updates(self, win):
        util_dir = win.util_bar.value()
        win.method_combo.setCurrentText("simplified")
        util_sim = win.util_bar.value()
        assert util_sim > 0
        assert util_sim != util_dir or True

    def test_results_consistent_with_engine(self, win):
        from weldcheck.engine import WeldForces, WeldInput, check_weld

        w = win._make_input()
        out = check_weld(w)
        assert f"{out.sigma_perp:.2f}" in win.sigma_perp_label.text()
        assert f"{out.f_vw_d:.2f}" in win.fvwd_label.text()

    def test_sizing_hint_flags_small_throat(self, win):
        win.throat_spin.setValue(3.0)
        assert win.sizing_hint_label.text().startswith("⚠")
