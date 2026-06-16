from __future__ import annotations
from dataclasses import dataclass, field

@dataclass
class GoldenItem:
    id: str
    tier: int
    question: str
    reference_answer: str
    expected_keywords: list[str] = field(default_factory=list)
    role: str = "process_engineer"

GOLDEN_DATASET: list[GoldenItem] = [
    GoldenItem("T1-01",1,"What wavelength does EUV lithography use?","EUV lithography uses 13.5 nm wavelength light.",["13.5","nm","wavelength"]),
    GoldenItem("T1-02",1,"What is the numerical aperture of the ASML NXE:3400 scanner?","The NXE:3400 has a numerical aperture of 0.33.",["0.33","numerical aperture"]),
    GoldenItem("T1-03",1,"What material is used as the EUV light source target?","Tin (Sn) droplets are used as the target material.",["tin","Sn","droplets"]),
    GoldenItem("T1-04",1,"What type of laser excites the EUV light source?","A CO2 laser is used to excite tin droplets.",["CO2","laser"]),
    GoldenItem("T1-05",1,"What is the approximate wafer throughput of the NXE:3400B?","Approximately 125 wafers per hour.",["125","wafers","hour"]),
    GoldenItem("T1-06",1,"What gas environment does the EUV optical system operate in?","Near-vacuum with hydrogen buffer gas.",["vacuum","hydrogen"]),
    GoldenItem("T1-07",1,"How many mirrors are in the EUV projection optical path?","6 multilayer mirrors.",["6","mirrors","multilayer"]),
    GoldenItem("T1-08",1,"What type of mask does EUV lithography use?","Reflective masks (EUV reticles).",["reflective","reticle"]),
    GoldenItem("T1-09",1,"What is the overlay specification for the NXE:3400?","Less than 2 nm.",["2 nm","overlay"]),
    GoldenItem("T1-10",1,"What wavelength does the ArF excimer laser operate at?","193 nm wavelength.",["193","nm","ArF"]),
    GoldenItem("T2-01",2,"How should a field engineer respond to a dose uniformity alarm?","Inspect the illumination system apertures, verify laser pulse energy stability, and check sensor calibration.",["dose","illumination","apertures","laser"],role="field_engineer"),
    GoldenItem("T2-02",2,"What is the sequence for performing a focus calibration on the EUV scanner?","Load calibration reticle, expose focus-exposure matrix, measure developed wafer, fit best-focus curve, update focus offset in recipe.",["calibration","reticle","focus","metrology"]),
    GoldenItem("T2-03",2,"How do you perform a reticle pod inspection before loading?","Verify pod ID, check pod integrity, inspect reticle surface for particles, confirm environment specification.",["pod","reticle","contamination","inspection"]),
    GoldenItem("T2-04",2,"What are the steps for daily maintenance of the EUV light source?","Check tin droplet generator, verify CO2 laser power, inspect collector mirror reflectivity, monitor hydrogen flow, log readings.",["maintenance","tin","collector","hydrogen"]),
    GoldenItem("T2-05",2,"How is wafer stage position calibrated between production lots?","Use on-product overlay marks, apply APC corrections, verify with first wafer of new lot.",["stage","overlay","calibration","APC"]),
    GoldenItem("T2-06",2,"What is the procedure for qualifying a new photoresist lot?","Coat test wafers, expose focus-exposure matrix, measure CD/LWR/sensitivity, compare to spec, document in MES.",["resist","CD","qualification","sensitivity"]),
    GoldenItem("T2-07",2,"How do you diagnose and resolve a reticle alignment failure?","Check stage encoder readings, verify reticle seating, inspect alignment marks for contamination, run recovery procedure.",["alignment","encoder","clamp","marks"]),
    GoldenItem("T2-08",2,"What is the proper shutdown sequence for the EUV scanner?","Complete lot, park stage, ramp down EUV source, wait for cooling, vent vacuum, confirm hydrogen off, log shutdown.",["shutdown","stage","vacuum","hydrogen","collector"]),
    GoldenItem("T2-09",2,"How is overlay error measured and corrected on the EUV scanner?","Measured via scatterometry/IBO metrology, fed into APC which decomposes and corrects translation/rotation/magnification.",["overlay","metrology","APC","correction"]),
    GoldenItem("T2-10",2,"What steps are taken when pellicle inspection shows a defect?","Quarantine reticle, log defect coordinates, compare to exclusion zone spec, determine if defect prints at working NA.",["pellicle","defect","reticle","exclusion"]),
    GoldenItem("T3-01",3,"Why does EUV lithography require near-vacuum conditions and how does this affect system design?","EUV at 13.5 nm is strongly absorbed by air, requiring vacuum enclosures for all optics and hydrogen buffer gas to prevent tin contamination.",["vacuum","absorption","hydrogen","tin","optics"]),
    GoldenItem("T3-02",3,"How does numerical aperture relate to resolution and what are the tradeoffs for high-NA EUV?","Resolution = k1*lambda/NA; higher NA improves resolution but reduces depth of focus and requires anamorphic optics.",["resolution","NA","depth of focus","anamorphic"]),
    GoldenItem("T3-03",3,"If overlay error increases after a reticle swap, what are the most likely root causes?","Reticle-specific grid distortion, clamping differences, chuck contamination, or mismatch between reticle writing grid and scanner grid.",["overlay","reticle","grid","thermal","chuck"]),
    GoldenItem("T3-04",3,"What is the relationship between EUV source power, wafer throughput, and photoresist sensitivity?","Throughput scales with source power and resist sensitivity; higher sensitivity enables faster scan speed but increases stochastic effects.",["source power","throughput","sensitivity","stochastic","LWR"]),
    GoldenItem("T3-05",3,"How do stochastic effects in EUV differ from DUV and what process controls minimise their impact?","EUV uses fewer photons per pixel (lower energy), causing larger LWR and local dose variation; controlled via high-sensitivity resists and dose optimisation.",["stochastic","photons","LWR","dose","DUV"]),
    GoldenItem("T3-06",3,"Why are collector mirrors replaced on a schedule and what performance indicators justify early replacement?","Tin deposition and radiation damage degrade reflectivity; replace early when EUV power drops below throughput floor or reflectivity degrades >5%.",["collector","tin","reflectivity","replacement","dose"]),
    GoldenItem("T3-07",3,"How does hydrogen purge gas serve dual functions and what happens if flow is interrupted?","Hydrogen cleans tin deposits (forms volatile SnH4) and acts as buffer gas; interruption causes permanent reflectivity loss from tin accumulation.",["hydrogen","tin","SnH4","cleaning","reflectivity"]),
    GoldenItem("T3-08",3,"What process parameters most affect line edge roughness in EUV patterning?","Photon shot noise, acid diffusion length, resist film thickness, PEB temperature uniformity, and developer concentration/temperature.",["LWR","shot noise","dose","resist","bake","developer"]),
    GoldenItem("T3-09",3,"How does mask blank defectivity impact yield and what inspection strategy minimises risk?","Blank defects in pattern field reduce yield; use AIMS simulation, aerial image metrology, and actinic patterned mask inspection.",["mask blank","defect","yield","AIMS","actinic"]),
    GoldenItem("T3-10",3,"If a scanner shows degrading CD uniformity over time, what are the systematic root causes?","EUV dose drift, illumination contamination, resist coating/bake aging, reticle heating, or focus drift from stage thermal load.",["CD uniformity","dose","illumination","resist","focus"]),
]

def get_tier(tier: int) -> list[GoldenItem]:
    return [q for q in GOLDEN_DATASET if q.tier == tier]

def all_questions() -> list[GoldenItem]:
    return GOLDEN_DATASET
