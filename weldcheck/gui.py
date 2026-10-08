"""PySide6 GUI for EN 1993-1-8 fillet weld design checks."""

import sys

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QProgressBar,
    QSplitter,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from weldcheck.engine import (
    STEEL_GRADES,
    WeldForces,
    WeldInput,
    check_weld,
    max_throat,
    min_throat,
)


class WeldDesignWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Weld Design — EN 1993-1-8 (EC3)")
        self.resize(900, 600)
        self._build_ui()

    # ---------------------------------------------------------------- UI

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QHBoxLayout(central)

        splitter = QSplitter(Qt.Horizontal)
        root.addWidget(splitter)

        left = QWidget()
        left_layout = QVBoxLayout(left)
        splitter.addWidget(left)

        # --- Material group
        mat_box = QGroupBox("Material & Method")
        mat_form = QFormLayout(mat_box)
        left_layout.addWidget(mat_box)

        self.grade_combo = QComboBox()
        self.grade_combo.addItems(sorted(STEEL_GRADES.keys()))
        self.grade_combo.currentTextChanged.connect(self.recalculate)
        mat_form.addRow("Steel grade", self.grade_combo)

        self.gamma_spin = QDoubleSpinBox()
        self.gamma_spin.setRange(1.0, 2.0)
        self.gamma_spin.setSingleStep(0.05)
        self.gamma_spin.setValue(1.25)
        self.gamma_spin.setSuffix("  (γMw)")
        self.gamma_spin.valueChanged.connect(self.recalculate)
        mat_form.addRow("Partial factor", self.gamma_spin)

        self.method_combo = QComboBox()
        self.method_combo.addItems(["directional", "simplified"])
        self.method_combo.currentTextChanged.connect(self.recalculate)
        mat_form.addRow("Method", self.method_combo)

        # --- Geometry group
        geom_box = QGroupBox("Weld Geometry")
        geom_form = QFormLayout(geom_box)
        left_layout.addWidget(geom_box)

        self.throat_spin = QDoubleSpinBox()
        self.throat_spin.setRange(0.5, 50.0)
        self.throat_spin.setSingleStep(0.5)
        self.throat_spin.setValue(6.0)
        self.throat_spin.setSuffix(" mm  (a)")
        self.throat_spin.valueChanged.connect(self.recalculate)
        geom_form.addRow("Throat thickness", self.throat_spin)

        self.length_spin = QDoubleSpinBox()
        self.length_spin.setRange(1.0, 10000.0)
        self.length_spin.setSingleStep(10.0)
        self.length_spin.setValue(150.0)
        self.length_spin.setSuffix(" mm  (L)")
        self.length_spin.valueChanged.connect(self.recalculate)
        geom_form.addRow("Weld length", self.length_spin)

        self.plate1_spin = QDoubleSpinBox()
        self.plate1_spin.setRange(1.0, 200.0)
        self.plate1_spin.setValue(10.0)
        self.plate1_spin.setSuffix(" mm")
        self.plate1_spin.valueChanged.connect(self.recalculate)
        geom_form.addRow("Plate thickness 1", self.plate1_spin)

        self.plate2_spin = QDoubleSpinBox()
        self.plate2_spin.setRange(1.0, 200.0)
        self.plate2_spin.setValue(10.0)
        self.plate2_spin.setSuffix(" mm")
        self.plate2_spin.valueChanged.connect(self.recalculate)
        geom_form.addRow("Plate thickness 2", self.plate2_spin)

        # --- Forces group
        force_box = QGroupBox("Design Forces (kN)")
        force_form = QFormLayout(force_box)
        left_layout.addWidget(force_box)

        self.n_spin = QDoubleSpinBox()
        self.n_spin.setRange(-10000.0, 10000.0)
        self.n_spin.setValue(100.0)
        self.n_spin.valueChanged.connect(self.recalculate)
        force_form.addRow("N (transverse normal)", self.n_spin)

        self.vl_spin = QDoubleSpinBox()
        self.vl_spin.setRange(-10000.0, 10000.0)
        self.vl_spin.setValue(80.0)
        self.vl_spin.valueChanged.connect(self.recalculate)
        force_form.addRow("V_L (longitudinal)", self.vl_spin)

        self.vt_spin = QDoubleSpinBox()
        self.vt_spin.setRange(-10000.0, 10000.0)
        self.vt_spin.setValue(30.0)
        self.vt_spin.valueChanged.connect(self.recalculate)
        force_form.addRow("V_T (transverse shear)", self.vt_spin)

        left_layout.addStretch()

        # --- Results panel
        right = QWidget()
        right_layout = QVBoxLayout(right)
        splitter.addWidget(right)

        self.result_tabs = QTabWidget()
        right_layout.addWidget(self.result_tabs)

        # Tab 1: summary
        summary_tab = QWidget()
        summary_layout = QVBoxLayout(summary_tab)
        self.result_tabs.addTab(summary_tab, "Summary")

        self.status_label = QLabel("")
        font = QFont()
        font.setPointSize(14)
        font.setBold(True)
        self.status_label.setFont(font)
        self.status_label.setAlignment(Qt.AlignCenter)
        summary_layout.addWidget(self.status_label)

        self.util_bar = QProgressBar()
        self.util_bar.setRange(0, 100)
        self.util_bar.setFormat("%p% utilization")
        summary_layout.addWidget(self.util_bar)

        self.details_label = QLabel("")
        self.details_label.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self.details_label.setWordWrap(True)
        summary_layout.addWidget(self.details_label)
        summary_layout.addStretch()

        # Tab 2: stress components
        stress_tab = QWidget()
        stress_layout = QFormLayout(stress_tab)
        self.result_tabs.addTab(stress_tab, "Stress Components")

        self.sigma_perp_label = QLabel("")
        stress_layout.addRow("σ⊥ (normal on throat)", self.sigma_perp_label)
        self.tau_perp_label = QLabel("")
        stress_layout.addRow("τ⊥ (transverse shear)", self.tau_perp_label)
        self.tau_par_label = QLabel("")
        stress_layout.addRow("τ∥ (longitudinal shear)", self.tau_par_label)
        self.fvwd_label = QLabel("")
        stress_layout.addRow("f_vw,d (design strength)", self.fvwd_label)
        self.fu_label = QLabel("")
        stress_layout.addRow("fu (ultimate)", self.fu_label)
        self.beta_label = QLabel("")
        stress_layout.addRow("βw (correlation factor)", self.beta_label)
        self.governed_label = QLabel("")
        stress_layout.addRow("Governed by", self.governed_label)

        # Tab 3: sizing
        sizing_tab = QWidget()
        sizing_layout = QFormLayout(sizing_tab)
        self.result_tabs.addTab(sizing_tab, "Throat Sizing")

        self.min_throat_label = QLabel("")
        sizing_layout.addRow("Minimum throat (full strength)", self.min_throat_label)
        self.max_throat_label = QLabel("")
        sizing_layout.addRow("Maximum throat (practical)", self.max_throat_label)
        self.sizing_hint_label = QLabel("")
        self.sizing_hint_label.setWordWrap(True)
        sizing_layout.addRow(self.sizing_hint_label)

        splitter.setSizes([400, 500])
        self.recalculate()

    # ------------------------------------------------------------ actions

    def _make_input(self) -> WeldInput:
        return WeldInput(
            steel_grade=self.grade_combo.currentText(),
            a=self.throat_spin.value(),
            L=self.length_spin.value(),
            gamma_Mw=self.gamma_spin.value(),
            method=self.method_combo.currentText(),
            forces=WeldForces(
                N=self.n_spin.value(),
                V_L=self.vl_spin.value(),
                V_T=self.vt_spin.value(),
            ),
        )

    def recalculate(self):
        try:
            w = self._make_input()
            out = check_weld(w)
        except ValueError as exc:
            self.status_label.setText(f"⚠ {exc}")
            return

        t1 = self.plate1_spin.value()
        t2 = self.plate2_spin.value()
        a_min = min_throat(t1, t2)
        a_max = max_throat(t1, t2)

        if out.ok:
            self.status_label.setText("✔ PASS")
            self.status_label.setStyleSheet("color: #1b5e20;")
            self.util_bar.setStyleSheet("")
        else:
            self.status_label.setText("✘ FAIL")
            self.status_label.setStyleSheet("color: #b71c1c;")

        self.util_bar.setValue(min(100, int(round(out.utilization * 100))))
        self.util_bar.setFormat(f"{out.utilization * 100:.1f}% utilization")

        self.details_label.setText(
            f"<b>Result:</b> utilization {out.utilization:.3f}<br>"
            f"<b>Check:</b> EN 1993-1-8 §4.5.3 "
            f"({'4.5.3.2 directional' if w.method == 'directional' else '4.5.3.3 simplified'})<br>"
            f"<b>Weld:</b> a = {w.a:.1f} mm, L = {w.L:.0f} mm<br>"
            f"<b>Forces:</b> N = {w.forces.N:.1f} kN, "
            f"V_L = {w.forces.V_L:.1f} kN, V_T = {w.forces.V_T:.1f} kN"
        )

        self.sigma_perp_label.setText(f"{out.sigma_perp:.2f} N/mm²")
        self.tau_perp_label.setText(f"{out.tau_perp:.2f} N/mm²")
        self.tau_par_label.setText(f"{out.tau_par:.2f} N/mm²")
        self.fvwd_label.setText(f"{out.f_vw_d:.2f} N/mm²")
        self.fu_label.setText(f"{out.fu:.0f} N/mm²")
        self.beta_label.setText(f"{out.beta_w:.2f}")
        self.governed_label.setText(out.governed_by)

        self.min_throat_label.setText(f"{a_min:.1f} mm")
        self.max_throat_label.setText(f"{a_max:.1f} mm")
        if w.a < a_min:
            hint = (
                f"⚠ Throat {w.a:.1f} mm is below the full-strength "
                f"minimum {a_min:.1f} mm for plates {t1:.1f}/{t2:.1f} mm."
            )
        elif w.a > a_max:
            hint = (
                f"⚠ Throat {w.a:.1f} mm exceeds the thinner plate "
                f"({a_max:.1f} mm) — not practical."
            )
        else:
            hint = "Throat thickness is within practical limits."
        self.sizing_hint_label.setText(hint)


def main():
    app = QApplication(sys.argv)
    win = WeldDesignWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
