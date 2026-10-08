# Weld Design App

A desktop application for fillet weld design checks to **BS EN 1993-1-8**
(Eurocode 3: Design of steel structures — Part 1-8: Design of joints), with a
Qt6 (PySide6) user interface.

## Features

- **Directional method** (clause 4.5.3.2): resolves the applied forces into
  stresses on the weld throat plane and checks both code conditions:
  - σ⊥ ≤ fu / (βw · γMw)
  - √(σ⊥² + 3·(τ⊥² + τ∥²)) ≤ fu / (βw · γMw)
- **Simplified method** (clause 4.5.3.3): resultant force per unit length
  compared against the design weld shear strength — exact for pure
  longitudinal shear, conservative for transverse loading.
- **Weld strength per Table 4.1**: fu and βw for S235, S275, S355, S420, S460.
- **Throat sizing guidance**: practical minimum for a full-strength fillet
  (0.7 × thinner plate, ≥ 3 mm) and practical maximum (thinner plate thickness).
- Live recalculation as any input changes, with a utilization bar and
  PASS/FAIL indicator.

## Installation

Requires Python 3.9+ and Qt6.

```bash
pip install -r requirements.txt
```

On a headless Linux build/test environment you may also need system Qt
runtime libraries (libgl1, libegl1, etc.). Debian/Ubuntu users can get them
with:

```bash
sudo apt install libgl1 libegl1
```

## Usage

```bash
python -m weldcheck.gui
```

### Inputs

| Field | Description |
|---|---|
| Steel grade | Select from S235–S460 (sets fu and βw per Table 4.1) |
| Partial factor γMw | Recommended value 1.25; 1.0 with some National Annexes (e.g. UK) |
| Method | `directional` (clause 4.5.3.2) or `simplified` (clause 4.5.3.3) |
| Throat thickness a | Weld throat, in mm |
| Weld length L | Total active weld length, in mm |
| Plate thicknesses | Used for throat sizing guidance |
| N | Design normal force transverse to the weld axis (kN) |
| V_L | Design shear along the weld axis (kN) |
| V_T | Design transverse shear (kN) |

### Results

- **Summary** tab: PASS/FAIL, utilization, governing check.
- **Stress Components** tab: σ⊥, τ⊥, τ∥ on the throat plane, design strength
  f_vw,d, fu, βw.
- **Throat Sizing** tab: minimum/maximum practical throat and warnings.

## Development

```bash
pip install pytest
python -m pytest tests/
```

The calculation core (`weldcheck/engine.py`) is UI-independent and fully
unit-tested; the GUI (`weldcheck/gui.py`) has offscreen smoke tests.

## Limitations / Roadmap

- Single fillet weld runs only; weld groups (e.g. bolt/weld combinations,
  welds around sections) not yet covered.
- Base metal checks and clause 4.13 deep-penetration throat are not included.
- Future: bolted connections (Table 3.4), block tearing, National Annex
  selection, report export.

## Disclaimer

Engineering software for preliminary design and checking. Always verify
results against the code and have the final design checked by a qualified
engineer.
