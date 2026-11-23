# DB DeStrobe

A gizmo for Foundry Nuke designed to smooth out jerky object or camera motion via optical flow retiming, driven by a smoothed tracking curve.



---

## Core Features

* **Zero-Crop Motion Smoothing:** Eliminates stutters, jitter, and uneven movement via optical flow retiming instead of shifting the image—no cropping, scaling, or edge padding required.
* **Partial or Full Length Smoothing:** Smoothly eases in and out at the start and end of your track, making it effortless to fix a specific problematic section without visible speed jumps.
* **Handles Complex Motion:** Reliably smooths erratic, back-and-forth, or oscillating movements without unwanted frame freezes or backwards jumps.
* **Flexible Retime Choice:** Switch between **OFlow** (standard Nuke) and **Kronos** (NukeX) in a single click.
* **Curve Editor Inspection:** Compare original and smoothed curves directly in the Curve Editor for clear visual feedback.

---

## Installation

1. Download the latest version from the **[Releases page](https://github.com)**.
2. Copy the `DB_DeStrobe.gizmo` file into your `.nuke` directory or any custom plugin path defined in `init.py`.
3. Add the following command to your `menu.py` file:

```python
import nuke

toolbar = nuke.toolbar('Nodes')
dbtoolset = toolbar.addMenu('DB Toolset')
dbtoolset.addCommand("DB_DeStrobe", "nuke.createNode('DB_DeStrobe')")
```

---

## Usage

1. Connect your jerky plate to the **`image`** input.
2. Track the jerky motion using a standard **Tracker** node (keyframed `translate`) and connect it to the **`tracker`** input.
3. Adjust **Strength**, **Temporal Weight**, and **Transition Ratio** to fit the motion profile.
4. Click **CALCULATE** to smooth the motion and apply the retime.
5. Inspect `original_curve` / `smoothed_curve` in the Curve Editor to verify the smoothing.
6. Select your preferred **Engine** (**OFlow** or **Kronos**) and fine-tune the vector and filtering parameters.

---

## Controls

### Smoothing
* **Strength** (`1–50`, default `10`) — Base radius (in frames) of the Gaussian smoothing window at full strength. Higher values remove more jitter but pull the curve away from fast genuine motion.
* **Temporal Weight** (`0.1–10.0`, default `2.5`) — Cost of shifting playback by one frame, measured in median per-frame displacements. Low values follow the smoothed position aggressively and can produce freezes on oscillating motion; high values stay close to the original timing. Recommended `2–5` for erratic or back-and-forth motion.
* **Transition Ratio** (`0.01–0.50`, default `0.1`) — Fraction of the track length used as an edge blend zone. Smoothing fades out over this portion at the start and end of the track so the retimed section joins the untouched footage without a visible seam. Clamped to a minimum of 2 frames.
* **CALCULATE** — Validates inputs, computes the smoothed trajectory and monotonic lookup curve, and updates the **Info** panel.

### Retime
* **Engine** — Switches between **OFlow** and **Kronos**.
* **Vector Detail** — Controls the density of the calculated motion vector field.
* **Smoothness / Strength** — Adjusts vector field regularization (maps to *Smoothness* in OFlow and *Strength* in Kronos).
* **Filter** — Sets the pixel resampling filter (*Bilinear*, *Lanczos*, etc.).

### Info
* **Info** — Displays the detected **Input Range**, active **Smooth Range**, and **Warnings** (e.g., short tracks, unkeyed/expression-driven tracks, or mismatched track axis ranges).
* **View Curves** — Collapsible group containing keyframes for **Original Curve** and **Smoothed Curve** for direct inspection in the Curve Editor.

---

## Limitations

- **Temporal Weight** is footage-dependent. `2.5` is a neutral default; erratic motion typically needs `4–5`, while calm motion may require lower values. Tune per shot.
- **Strength** and **Temporal Weight** are coupled controls, not independent. **Strength** shapes the smoothed curve; **Temporal Weight** determines how eagerly the retime follows it.
- Tracker `translate` must be keyframed. Expression- or link-driven tracks will trigger a warning message, and no retime curve will be generated.
- Retiming is applied strictly within the tracker's animated frame range. Frames outside this range are passed through at `1.0x` speed (`1:1`) by design.

---

## Compatibility
- Supported Versions: **Nuke 15.0 or later** *(Kronos engine requires a **NukeX** license)*.
- OS Compatibility: Windows, Linux, macOS.
