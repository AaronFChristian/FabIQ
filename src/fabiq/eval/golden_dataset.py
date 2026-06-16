"""
FabIQ golden evaluation dataset — 30 Q&A pairs across 3 difficulty tiers.

Tier 1 (10): Factual lookups — single-source, specific answers
Tier 2 (10): Procedural — how-to, step-based answers
Tier 3 (10): Multi-hop — require reasoning across multiple sources

Used by run_eval.py for regression testing the full pipeline.
Each entry carries expected_keywords so the eval runner can do lightweight
lexical checks in addition to the LLM-as-judge scores.
"""
from __future__ import annotations
from dataclasses import dataclass, field

@dataclass
class GoldenItem:
    id: str
    tier: int  # 1 | 2 | 3
    question: str
    reference_answer: str
    expected_keywords: list[str] = field(default_factory=list)
    role: str = "process_engineer"   # which role should be able to answer this

GOLDEN_DATASET: list[GoldenItem] = [
    # ── Tier 1: Factual ──────────────────────────────────────────────────────
    GoldenItem(
        id="T1-01", tier=1,
        question="What wavelength does EUV lithography use?",
        reference_answer="EUV lithography uses 13.5 nm wavelength light.",
        expected_keywords=["13.5", "nm", "wavelength"],
    ),
    GoldenItem(
        id="T1-02", tier=1,
        question="What is the numerical aperture of the ASML NXE:3400 scanner?",
        reference_answer="The NXE:3400 has a numerical aperture of 0.33.",
        expected_keywords=["0.33", "numerical aperture"],
    ),
    GoldenItem(
        id="T1-03", tier=1,
        question="What material is used as the EUV light source target?",
        reference_answer="Tin (Sn) droplets are used as the target material for EUV light generation.",
        expected_keywords=["tin", "Sn", "droplets"],
    ),
    GoldenItem(
        id="T1-04", tier=1,
        question="What type of laser excites the EUV light source?",
        reference_answer="A CO2 laser is used to excite tin droplets and generate EUV plasma.",
        expected_keywords=["CO2", "laser"],
    ),
    GoldenItem(
        id="T1-05", tier=1,
        question="What is the approximate wafer throughput of the NXE:3400B?",
        reference_answer="The NXE:3400B achieves approximately 125 wafers per hour under optimal conditions.",
        expected_keywords=["125", "wafers", "hour"],
    ),
    GoldenItem(
        id="T1-06", tier=1,
        question="What gas environment does the EUV optical system operate in?",
        reference_answer="The EUV optics operate in a near-vacuum environment with hydrogen buffer gas.",
        expected_keywords=["vacuum", "hydrogen"],
    ),
    GoldenItem(
        id="T1-07", tier=1,
        question="How many mirrors are in the EUV projection optical path?",
        reference_answer="The EUV projection optics use 6 multilayer mirrors.",
        expected_keywords=["6", "mirrors", "multilayer"],
    ),
    GoldenItem(
        id="T1-08", tier=1,
        question="What type of mask does EUV lithography use?",
        reference_answer="EUV lithography uses reflective masks (EUV reticles) rather than transmissive masks.",
        expected_keywords=["reflective", "reticle"],
    ),
    GoldenItem(
        id="T1-09", tier=1,
        question="What is the overlay specification for the NXE:3400?",
        reference_answer="The NXE:3400 overlay specification is less than 2 nm.",
        expected_keywords=["2 nm", "overlay"],
    ),
    GoldenItem(
        id="T1-10", tier=1,
        question="What wavelength does the ArF excimer laser operate at?",
        reference_answer="The ArF excimer laser operates at 193 nm wavelength, used in DUV lithography.",
        expected_keywords=["193", "nm", "ArF"],
    ),

    # ── Tier 2: Procedural ────────────────────────────────────────────────────
    GoldenItem(
        id="T2-01", tier=2,
        question="How should a field engineer respond to a dose uniformity alarm?",
        reference_answer="When a dose uniformity alarm triggers, the engineer should inspect the illumination system apertures, verify laser pulse energy stability, and check the sensor calibration. If the issue persists, escalate to a process engineer.",
        expected_keywords=["dose", "illumination", "apertures", "laser"],
        role="field_engineer",
    ),
    GoldenItem(
        id="T2-02", tier=2,
        question="What is the sequence for performing a focus calibration on the EUV scanner?",
        reference_answer="Focus calibration involves: (1) loading the calibration reticle, (2) exposing the focus-exposure matrix, (3) measuring the developed wafer with the metrology tool, (4) fitting the best-focus curve, and (5) updating the focus offset in the scanner recipe.",
        expected_keywords=["calibration", "reticle", "focus", "metrology"],
    ),
    GoldenItem(
        id="T2-03", tier=2,
        question="How do you perform a reticle pod inspection before loading?",
        reference_answer="Reticle pod inspection includes: verifying pod ID matches job, checking pod integrity for cracks or contamination, inspecting the reticle surface for particles using the pod viewer, and confirming the environment specification before opening.",
        expected_keywords=["pod", "reticle", "contamination", "inspection"],
    ),
    GoldenItem(
        id="T2-04", tier=2,
        question="What are the steps for daily maintenance of the EUV light source?",
        reference_answer="Daily maintenance includes: checking tin droplet generator status, verifying CO2 laser power levels, inspecting collector mirror reflectivity readings, monitoring hydrogen flow rates, and logging all readings in the maintenance record.",
        expected_keywords=["maintenance", "tin", "collector", "hydrogen"],
    ),
    GoldenItem(
        id="T2-05", tier=2,
        question="How is wafer stage position calibrated between production lots?",
        reference_answer="Stage calibration between lots uses the on-product overlay marks from the previous lot. The stage grid is corrected using higher-order corrections from the APC system, and the calibration is verified using the first wafer of the new lot.",
        expected_keywords=["stage", "overlay", "calibration", "APC"],
    ),
    GoldenItem(
        id="T2-06", tier=2,
        question="What is the procedure for qualifying a new photoresist lot before production?",
        reference_answer="New resist qualification requires: (1) coating and baking test wafers to spec, (2) exposing a focus-exposure matrix, (3) measuring CD, LWR, and sensitivity, (4) comparing against the qualification specification, and (5) documenting results in the MES system.",
        expected_keywords=["resist", "CD", "qualification", "sensitivity"],
    ),
    GoldenItem(
        id="T2-07", tier=2,
        question="How do you diagnose and resolve a reticle alignment failure?",
        reference_answer="Reticle alignment failures are diagnosed by: checking reticle stage encoder readings, verifying the reticle is seated correctly in the clamp, inspecting alignment marks for contamination, and running the alignment recovery procedure. If hardware alignment persists, escalate to the reticle chuck for cleaning.",
        expected_keywords=["alignment", "encoder", "clamp", "marks"],
    ),
    GoldenItem(
        id="T2-08", tier=2,
        question="What is the proper shutdown sequence for the EUV scanner during planned maintenance?",
        reference_answer="Planned shutdown sequence: (1) complete current lot, (2) park the wafer stage, (3) ramp down EUV source power, (4) wait for collector cooling, (5) vent the vacuum module in prescribed order, (6) confirm hydrogen purge is off, (7) log shutdown time and status.",
        expected_keywords=["shutdown", "stage", "vacuum", "hydrogen", "collector"],
    ),
    GoldenItem(
        id="T2-09", tier=2,
        question="How is overlay error measured and corrected on the EUV scanner?",
        reference_answer="Overlay is measured using a scatterometry or IBO metrology tool on product wafers. The measured overlay map is fed into the APC system which decomposes it into correctable components (translation, rotation, magnification, higher-order) and applies corrections to the next lot.",
        expected_keywords=["overlay", "metrology", "APC", "correction"],
    ),
    GoldenItem(
        id="T2-10", tier=2,
        question="What steps are taken when the pellicle inspection shows a defect?",
        reference_answer="A pellicle defect requires: quarantining the reticle, logging the defect coordinates, comparing against the exclusion zone specification, and determining if the defect prints at the working NA. If critical, the reticle is replaced and the pellicle sent for root-cause analysis.",
        expected_keywords=["pellicle", "defect", "reticle", "exclusion"],
    ),

    # ── Tier 3: Multi-hop / Inferential ───────────────────────────────────────
    GoldenItem(
        id="T3-01", tier=3,
        question="Why does EUV lithography require near-vacuum conditions and how does this affect system design?",
        reference_answer="EUV light at 13.5 nm is strongly absorbed by air molecules, requiring near-vacuum to prevent attenuation over the beam path. This drives the system design to enclose all optics in vacuum modules, use hydrogen buffer gas to prevent tin contamination, and adds complexity to the wafer handling and reticle loading interfaces which must transition between atmospheric and vacuum environments.",
        expected_keywords=["vacuum", "absorption", "hydrogen", "tin", "optics"],
    ),
    GoldenItem(
        id="T3-02", tier=3,
        question="How does numerical aperture relate to resolution and what are the tradeoffs for high-NA EUV?",
        reference_answer="Resolution is proportional to wavelength divided by numerical aperture (R = k1 × λ / NA). Higher NA improves resolution but reduces depth of focus (DoF ∝ λ / NA²), tightening focus control requirements. High-NA EUV (0.55 NA) systems also require anamorphic optics to handle the increased field angle, adding optical complexity and cost.",
        expected_keywords=["resolution", "NA", "depth of focus", "anamorphic"],
    ),
    GoldenItem(
        id="T3-03", tier=3,
        question="If overlay error increases after a reticle swap, what are the most likely root causes?",
        reference_answer="After a reticle swap, overlay degradation most likely comes from: (1) reticle-specific grid distortion not compensated in the correction model, (2) reticle clamping differences affecting thermal expansion, (3) residual contamination on the chuck affecting seating, or (4) a mismatch between the reticle writing grid and the scanner grid. The engineer should run a full overlay map, decompose the error fingerprint, and check reticle thermal history.",
        expected_keywords=["overlay", "reticle", "grid", "thermal", "chuck"],
    ),
    GoldenItem(
        id="T3-04", tier=3,
        question="What is the relationship between EUV source power, wafer throughput, and photoresist sensitivity?",
        reference_answer="Throughput scales directly with source power and resist sensitivity. A more sensitive resist requires fewer photons per exposure, reducing dose and allowing higher scan speed at the same source power. However, higher sensitivity resists typically show increased stochastic effects (shot noise, LWR). The fab must balance throughput, sensitivity, and process window to optimise overall cost of ownership.",
        expected_keywords=["source power", "throughput", "sensitivity", "stochastic", "LWR"],
    ),
    GoldenItem(
        id="T3-05", tier=3,
        question="How do stochastic effects in EUV differ from DUV and what process controls minimise their impact?",
        reference_answer="EUV uses far fewer photons per pixel than DUV (due to the 14× lower photon energy at 13.5 nm vs 193 nm), making stochastic fluctuations proportionally larger. This drives higher LWR, higher defect density from local dose variation, and pattern collapse in dense lines. Controls include: higher-sensitivity resists with photon amplification chemistry, dose optimisation, post-exposure bake tuning, and statistical process control on CD-SEM measurements.",
        expected_keywords=["stochastic", "photons", "LWR", "dose", "DUV"],
    ),
    GoldenItem(
        id="T3-06", tier=3,
        question="Why are collector mirrors replaced on a schedule and what performance indicators justify early replacement?",
        reference_answer="Collector mirrors degrade from tin deposition and radiation-induced reflectivity loss. Scheduled replacement prevents unplanned source downtime. Early replacement is justified when: EUV power output at the intermediate focus drops below the throughput floor, reflectivity measurements show >5% degradation from baseline, or dose control drift exceeds the APC correction budget. These indicators must be tracked cumulatively, not just at point-in-time checks.",
        expected_keywords=["collector", "tin", "reflectivity", "replacement", "dose"],
    ),
    GoldenItem(
        id="T3-07", tier=3,
        question="How does hydrogen purge gas serve dual functions and what happens if flow is interrupted?",
        reference_answer="Hydrogen serves as (1) a cleaning agent — it reacts with tin deposits on optical surfaces, converting them to volatile SnH4 that pumps away, and (2) a buffer gas — it reduces the mean free path for EUV photons while being relatively transparent at 13.5 nm. A flow interruption allows tin to accumulate on collector and projection optics, causing permanent reflectivity loss that cannot be recovered by resuming hydrogen flow.",
        expected_keywords=["hydrogen", "tin", "SnH4", "cleaning", "reflectivity"],
    ),
    GoldenItem(
        id="T3-08", tier=3,
        question="What process parameters most affect line edge roughness in EUV patterning?",
        reference_answer="LWR in EUV is dominated by: (1) photon shot noise (inversely proportional to dose), (2) acid diffusion length in the resist chemistry, (3) resist film thickness uniformity, (4) post-exposure bake temperature uniformity, and (5) developer concentration and temperature. Optimising all five simultaneously requires design-of-experiments across chemistry and process parameters, constrained by the overlay and CD spec.",
        expected_keywords=["LWR", "shot noise", "dose", "resist", "bake", "developer"],
    ),
    GoldenItem(
        id="T3-09", tier=3,
        question="How does mask blank defectivity impact yield and what inspection strategy minimises risk?",
        reference_answer="Mask blank defects that fall within the pattern placement field print as chip defects, reducing yield. High-defect masks require defect-aware placement — routing critical layers away from defect locations. The inspection strategy combines: AIMS simulation to determine if a defect prints at the working conditions, aerial image metrology to verify, and actinic patterned mask inspection for the most critical layers. Blanks with defects above the kill threshold are rejected.",
        expected_keywords=["mask blank", "defect", "yield", "AIMS", "actinic"],
    ),
    GoldenItem(
        id="T3-10", tier=3,
        question="If a scanner shows degrading CD uniformity over time, what are the systematic root causes?",
        reference_answer="Degrading CD uniformity over time can stem from: (1) EUV dose control drift as source power changes, (2) illumination uniformity degradation from contaminated optical surfaces, (3) resist coating or bake non-uniformity developing as track hardware ages, (4) reticle heating effects accumulating over high-volume lots, or (5) focus drift from wafer stage thermal load. Isolating the root cause requires comparing across time with constant-process test structures and separating scanner, track, and reticle contributions.",
        expected_keywords=["CD uniformity", "dose", "illumination", "resist", "focus"],
    ),
]

def get_tier(tier: int) -> list[GoldenItem]:
    return [q for q in GOLDEN_DATASET if q.tier == tier]

def all_questions() -> list[GoldenItem]:
    return GOLDEN_DATASET
