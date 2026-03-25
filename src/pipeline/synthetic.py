"""Synthetic CMS data generation — reusable library.

Generates 4 sets of CMS-formatted rows (part_b_service, part_b_provider,
enrollment, revocations) with vendor column names.  Designed to produce a
meaningful distribution of high_risk, review, and stable labels after
the ETL recalibration pipeline runs.

Used by ``scripts/generate_synthetic_data.py`` (CLI) and
``POST /api/ingest/seed`` (server-side one-click seeding).
"""

from __future__ import annotations

import random
import statistics
from collections import defaultdict
from dataclasses import dataclass
from enum import StrEnum

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

SEED = 42

# ---------------------------------------------------------------------------
# Archetypes
# ---------------------------------------------------------------------------


class Archetype(StrEnum):
    STABLE = "stable"
    REVIEW_MILD = "review_mild"
    REVIEW_MID = "review_mid"
    HIGH_RISK_Z = "high_risk_z"
    HIGH_RISK_REVOKED = "high_risk_revoked"
    NOT_ENROLLED = "not_enrolled"


# Z-score targets per archetype per dimension (volume, intensity, charge, payment)
# None = draw from baseline (near-zero z).
Z_TARGETS: dict[Archetype, tuple[float | None, ...]] = {
    Archetype.STABLE: (None, None, None, None),
    Archetype.REVIEW_MILD: (2.0, None, None, None),
    Archetype.REVIEW_MID: (3.0, 3.0, None, None),
    Archetype.HIGH_RISK_Z: (5.0, 5.0, 5.0, 5.0),
    Archetype.HIGH_RISK_REVOKED: (3.0, 2.0, None, None),
    Archetype.NOT_ENROLLED: (2.0, None, None, None),
}

# ---------------------------------------------------------------------------
# Specialties and HCPCS pools
# ---------------------------------------------------------------------------

SPECIALTIES: list[dict] = [
    {
        "type": "Internal Medicine",
        "count": 70,
        "codes": [
            ("99213", "Office/outpatient visit, est, 15 min"),
            ("99214", "Office/outpatient visit, est, 25 min"),
            ("99215", "Office/outpatient visit, est, 40 min"),
            ("99203", "Office/outpatient visit, new, 30 min"),
            ("99204", "Office/outpatient visit, new, 45 min"),
            ("99205", "Office/outpatient visit, new, 60 min"),
            ("99211", "Office/outpatient visit, est, 5 min"),
            ("99212", "Office/outpatient visit, est, 10 min"),
            ("36415", "Collection of venous blood"),
            ("85025", "Complete CBC"),
            ("80053", "Comprehensive metabolic panel"),
            ("80061", "Lipid panel"),
            ("81001", "Urinalysis automated"),
            ("G0439", "Annual wellness visit, subsequent"),
            ("G0438", "Annual wellness visit, initial"),
            ("90471", "Immunization admin, 1st"),
            ("96372", "Therapeutic injection, subq/im"),
            ("99395", "Preventive visit, 18-39"),
            ("99396", "Preventive visit, 40-64"),
            ("93000", "Electrocardiogram, complete"),
        ],
        "allowed_range": (60, 250),
    },
    {
        "type": "Physical Therapist in Private Practice",
        "count": 80,
        "codes": [
            ("97110", "Therapeutic exercises"),
            ("97140", "Manual therapy techniques"),
            ("97530", "Therapeutic activities"),
            ("97112", "Neuromuscular reeducation"),
            ("97161", "PT evaluation, low complexity"),
            ("97162", "PT evaluation, mod complexity"),
            ("97163", "PT evaluation, high complexity"),
            ("97116", "Gait training therapy"),
            ("97035", "Ultrasound therapy"),
            ("97010", "Hot/cold packs therapy"),
            ("97542", "Wheelchair management"),
            ("97150", "Group therapeutic procedures"),
            ("97032", "Electrical stimulation"),
            ("97033", "Iontophoresis"),
            ("97164", "PT re-evaluation"),
            ("97760", "Orthotic mgmt and training"),
            ("97761", "Prosthetic training"),
            ("97762", "C/O for orthotic/prosthetic"),
            ("97750", "Physical performance test"),
            ("97545", "Work hardening, initial 2 hr"),
        ],
        "allowed_range": (30, 120),
    },
    {
        "type": "Cardiology",
        "count": 50,
        "codes": [
            ("93000", "Electrocardiogram, complete"),
            ("93010", "Electrocardiogram, report"),
            ("93306", "TTE w/Doppler, complete"),
            ("93005", "Electrocardiogram, tracing"),
            ("93015", "Cardiovascular stress test"),
            ("93017", "Stress test, tracing only"),
            ("93018", "Stress test, interp/report"),
            ("93320", "Doppler echo exam, complete"),
            ("93225", "ECG monitoring, review"),
            ("93224", "ECG monitoring, up to 48 hrs"),
            ("93226", "ECG monitoring, scanning"),
            ("93227", "ECG monitoring, review/report"),
            ("93880", "Duplex scan, extracranial"),
            ("93970", "Duplex scan, extremity veins"),
            ("93971", "Duplex scan, unilateral"),
        ],
        "allowed_range": (80, 500),
    },
    {
        "type": "Orthopedic Surgery",
        "count": 50,
        "codes": [
            ("20610", "Arthrocentesis, major joint"),
            ("20550", "Injection, tendon sheath"),
            ("20600", "Arthrocentesis, small joint"),
            ("20605", "Arthrocentesis, intermediate"),
            ("27447", "Total knee arthroplasty"),
            ("27130", "Total hip arthroplasty"),
            ("29881", "Arthroscopy, knee, surgical"),
            ("29880", "Arthroscopy, knee, meniscectomy"),
            ("23472", "Arthroplasty, glenohumeral"),
            ("28296", "Bunionectomy"),
        ],
        "allowed_range": (100, 800),
    },
]

# Archetype distribution per specialty (proportional to specialty count)
ARCHETYPE_RATIOS: dict[Archetype, float] = {
    Archetype.STABLE: 0.35,
    Archetype.REVIEW_MILD: 0.25,
    Archetype.REVIEW_MID: 0.14,
    Archetype.HIGH_RISK_Z: 0.15,
    Archetype.HIGH_RISK_REVOKED: 0.05,
    Archetype.NOT_ENROLLED: 0.06,
}

STATES = ["FL", "TX"]
STATE_SPLIT = 0.80  # 80% FL, 20% TX

CITIES: dict[str, list[tuple[str, str]]] = {
    "FL": [
        ("Miami", "33101"),
        ("Orlando", "32801"),
        ("Tampa", "33601"),
        ("Jacksonville", "32099"),
        ("Fort Lauderdale", "33301"),
    ],
    "TX": [
        ("Houston", "77001"),
        ("Dallas", "75201"),
        ("Austin", "78701"),
        ("San Antonio", "78201"),
    ],
}

CREDENTIALS = ["M.D.", "D.O.", "P.T.", "D.P.T.", "PA-C", "NP"]
FIRST_NAMES = [
    "James",
    "Maria",
    "David",
    "Sarah",
    "Michael",
    "Jennifer",
    "Robert",
    "Linda",
    "William",
    "Patricia",
    "Richard",
    "Elizabeth",
    "Joseph",
    "Susan",
    "Thomas",
    "Karen",
    "Christopher",
    "Nancy",
    "Daniel",
    "Lisa",
]
LAST_NAMES = [
    "Smith",
    "Johnson",
    "Williams",
    "Brown",
    "Jones",
    "Garcia",
    "Miller",
    "Davis",
    "Rodriguez",
    "Martinez",
    "Hernandez",
    "Lopez",
    "Gonzalez",
    "Wilson",
    "Anderson",
    "Thomas",
    "Taylor",
    "Moore",
    "Jackson",
    "Martin",
]

REVOCATION_REASONS = [
    "False/Fraudulent Claims (42 CFR 424.535(a)(8)(i))",
    "Felony Conviction (42 CFR 424.535(a)(3))",
    "License Revocation/Suspension (42 CFR 424.535(a)(1))",
]


# ---------------------------------------------------------------------------
# Provider record
# ---------------------------------------------------------------------------


@dataclass
class Provider:
    npi: str
    first_name: str
    last_name: str
    credentials: str
    entity_code: str
    city: str
    state: str
    zip5: str
    provider_type: str
    participating: str  # Y or N
    archetype: Archetype
    enrolled: bool
    revoked: bool


# ---------------------------------------------------------------------------
# Z-score solver
# ---------------------------------------------------------------------------


def solve_outlier_value(baseline_values: list[float], z_target: float) -> float:
    """Find value X such that z(X) within (baseline + [X]) approximates z_target.

    Since adding X changes the mean and std, we iteratively adjust X until
    the resulting z-score is within tolerance.
    """
    if len(baseline_values) < 2:
        return max(baseline_values[0] * (1 + z_target * 0.5), 12.0) if baseline_values else 100.0
    mean = statistics.mean(baseline_values)
    std = statistics.pstdev(baseline_values)
    if std == 0:
        std = mean * 0.1  # fallback
    # Initial guess: overshoot to account for mean/std shift
    x = mean + z_target * std * 2.5
    for _ in range(1000):
        full = baseline_values + [x]
        m = statistics.mean(full)
        s = statistics.pstdev(full)
        if s < 1e-9:
            break
        z_actual = (x - m) / s
        error = z_target - z_actual
        if abs(error) < 0.05:
            break
        x += error * s * 0.3
    return max(x, 12.0)


def gauss_clipped(rng: random.Random, mu: float, sigma: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, rng.gauss(mu, sigma)))


# ---------------------------------------------------------------------------
# Generation
# ---------------------------------------------------------------------------


def generate_providers(rng: random.Random) -> list[Provider]:
    providers: list[Provider] = []
    npi_counter = 1000000001

    for spec in SPECIALTIES:
        count = spec["count"]
        ptype = spec["type"]

        # Distribute archetypes
        archetype_counts: dict[Archetype, int] = {}
        remaining = count
        for arch, ratio in ARCHETYPE_RATIOS.items():
            n = max(1, round(count * ratio))
            archetype_counts[arch] = n
            remaining -= n
        # Adjust STABLE to absorb rounding
        archetype_counts[Archetype.STABLE] += remaining

        for arch, n in archetype_counts.items():
            for _ in range(n):
                state = "FL" if rng.random() < STATE_SPLIT else "TX"
                city, zip5 = rng.choice(CITIES[state])
                enrolled = arch not in (Archetype.HIGH_RISK_REVOKED, Archetype.NOT_ENROLLED)
                revoked = arch == Archetype.HIGH_RISK_REVOKED
                participating = "Y" if arch != Archetype.HIGH_RISK_REVOKED else "N"

                providers.append(
                    Provider(
                        npi=str(npi_counter),
                        first_name=rng.choice(FIRST_NAMES),
                        last_name=rng.choice(LAST_NAMES),
                        credentials=rng.choice(CREDENTIALS),
                        entity_code="I",  # Individual
                        city=city,
                        state=state,
                        zip5=zip5,
                        provider_type=ptype,
                        participating=participating,
                        archetype=arch,
                        enrolled=enrolled,
                        revoked=revoked,
                    )
                )
                npi_counter += 1

    rng.shuffle(providers)
    return providers


def generate_service_rows(rng: random.Random, providers: list[Provider]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []

    # Group providers by specialty
    by_type: dict[str, list[Provider]] = defaultdict(list)
    for p in providers:
        by_type[p.provider_type].append(p)

    for spec in SPECIALTIES:
        ptype = spec["type"]
        codes = spec["codes"]
        allowed_lo, allowed_hi = spec["allowed_range"]
        type_providers = by_type[ptype]

        for hcpcs_cd, hcpcs_desc in codes:
            # Phase 1: generate baseline values for non-outlier providers
            baseline_srvcs: list[float] = []
            baseline_spb: list[float] = []
            baseline_charge_ratio: list[float] = []
            baseline_payment: list[float] = []

            provider_values: dict[str, dict] = {}

            for p in type_providers:
                z_targets = Z_TARGETS[p.archetype]
                is_baseline = all(t is None for t in z_targets)

                allowed = gauss_clipped(
                    rng,
                    (allowed_lo + allowed_hi) / 2,
                    (allowed_hi - allowed_lo) / 4,
                    allowed_lo,
                    allowed_hi,
                )
                benes = gauss_clipped(rng, 80, 40, 12, 400)
                if p.archetype == Archetype.STABLE:
                    benes = max(benes, 150)  # ensure large_patient_panel

                if is_baseline:
                    srvcs = gauss_clipped(rng, benes * 2.5, benes * 0.5, 12, benes * 6)
                    spb = srvcs / benes
                    charge_ratio = gauss_clipped(rng, 1.8, 0.3, 1.1, 3.5)
                    payment = gauss_clipped(
                        rng, allowed * 0.82, allowed * 0.05, allowed * 0.6, allowed * 0.95
                    )

                    baseline_srvcs.append(srvcs)
                    baseline_spb.append(spb)
                    baseline_charge_ratio.append(charge_ratio)
                    baseline_payment.append(payment)

                provider_values[p.npi] = {
                    "allowed": allowed,
                    "benes": benes,
                }

            # Phase 2: solve outlier values
            for p in type_providers:
                z_targets = Z_TARGETS[p.archetype]
                vals = provider_values[p.npi]
                allowed = vals["allowed"]
                benes = vals["benes"]

                z_vol, z_int, z_chr, z_pmt = z_targets

                if z_vol is not None and baseline_srvcs:
                    srvcs = solve_outlier_value(baseline_srvcs, z_vol)
                else:
                    mu = statistics.mean(baseline_srvcs) if baseline_srvcs else benes * 2.5
                    sig = (
                        statistics.pstdev(baseline_srvcs) * 0.5
                        if len(baseline_srvcs) > 1
                        else benes * 0.3
                    )
                    srvcs = gauss_clipped(rng, mu, sig, 12, 50000)

                if z_int is not None and baseline_spb:
                    target_spb = solve_outlier_value(baseline_spb, z_int)
                    # Adjust srvcs to produce this spb, or adjust benes
                    srvcs = max(srvcs, target_spb * benes)
                    srvcs = max(srvcs, 12)

                spb = srvcs / benes if benes > 0 else 1.0

                if z_chr is not None and baseline_charge_ratio:
                    charge_ratio = solve_outlier_value(baseline_charge_ratio, z_chr)
                else:
                    charge_ratio = gauss_clipped(rng, 1.8, 0.3, 1.1, 3.5)

                if z_pmt is not None and baseline_payment:
                    payment = solve_outlier_value(baseline_payment, z_pmt)
                else:
                    payment = gauss_clipped(
                        rng, allowed * 0.82, allowed * 0.05, allowed * 0.6, allowed * 0.95
                    )

                submitted = allowed * charge_ratio
                bene_day_srvcs = srvcs  # simplification

                rows.append(
                    {
                        "Rndrng_NPI": p.npi,
                        "Rndrng_Prvdr_Last_Org_Name": p.last_name,
                        "Rndrng_Prvdr_First_Name": p.first_name,
                        "Rndrng_Prvdr_Crdntls": p.credentials,
                        "Rndrng_Prvdr_Ent_Cd": p.entity_code,
                        "Rndrng_Prvdr_City": p.city,
                        "Rndrng_Prvdr_State_Abrvtn": p.state,
                        "Rndrng_Prvdr_Zip5": p.zip5,
                        "Rndrng_Prvdr_Type": p.provider_type,
                        "Rndrng_Prvdr_Mdcr_Prtcptg_Ind": p.participating,
                        "HCPCS_Cd": hcpcs_cd,
                        "HCPCS_Desc": hcpcs_desc,
                        "Place_Of_Srvc": "O",
                        "Tot_Benes": f"{max(12, round(benes))}",
                        "Tot_Srvcs": f"{max(12, round(srvcs))}",
                        "Tot_Bene_Day_Srvcs": f"{max(12, round(bene_day_srvcs))}",
                        "Avg_Sbmtd_Chrg": f"{max(1.0, round(submitted, 2))}",
                        "Avg_Mdcr_Alowd_Amt": f"{max(1.0, round(allowed, 2))}",
                        "Avg_Mdcr_Pymt_Amt": f"{max(0.01, round(payment, 2))}",
                    }
                )

    return rows


def derive_provider_rows(
    service_rows: list[dict[str, str]], providers: list[Provider]
) -> list[dict[str, str]]:
    # Aggregate service rows by NPI
    agg: dict[str, dict] = defaultdict(
        lambda: {
            "codes": set(),
            "max_benes": 0,
            "total_srvcs": 0,
            "total_payment": 0.0,
        }
    )
    for row in service_rows:
        npi = row["Rndrng_NPI"]
        a = agg[npi]
        a["codes"].add(row["HCPCS_Cd"])
        benes = int(row["Tot_Benes"])
        srvcs = int(row["Tot_Srvcs"])
        pmt = float(row["Avg_Mdcr_Pymt_Amt"])
        a["max_benes"] = max(a["max_benes"], benes)
        a["total_srvcs"] += srvcs
        a["total_payment"] += srvcs * pmt

    prov_map = {p.npi: p for p in providers}
    result = []
    for npi, a in sorted(agg.items()):
        p = prov_map[npi]
        result.append(
            {
                "Rndrng_NPI": npi,
                "Rndrng_Prvdr_Last_Org_Name": p.last_name,
                "Rndrng_Prvdr_First_Name": p.first_name,
                "Rndrng_Prvdr_City": p.city,
                "Rndrng_Prvdr_State_Abrvtn": p.state,
                "Rndrng_Prvdr_Zip5": p.zip5,
                "Rndrng_Prvdr_Type": p.provider_type,
                "Rndrng_Prvdr_Mdcr_Prtcptg_Ind": p.participating,
                "Tot_HCPCS_Cds": str(len(a["codes"])),
                "Tot_Benes": str(a["max_benes"]),
                "Tot_Srvcs": str(a["total_srvcs"]),
                "Tot_Mdcr_Pymt_Amt": f"{round(a['total_payment'], 2)}",
            }
        )
    return result


def generate_enrollment_rows(providers: list[Provider]) -> list[dict[str, str]]:
    rows = []
    for i, p in enumerate(providers):
        if not p.enrolled:
            continue
        rows.append(
            {
                "NPI": p.npi,
                "ENRLMT_ID": f"I20240101{i:06d}",
                "PROVIDER_TYPE_CODE": "14" if "Medicine" in p.provider_type else "65",
                "PROVIDER_TYPE_DESC": p.provider_type,
                "STATE_CD": p.state,
            }
        )
    return rows


def generate_revocation_rows(rng: random.Random, providers: list[Provider]) -> list[dict[str, str]]:
    rows = []
    for p in providers:
        if not p.revoked:
            continue
        rows.append(
            {
                "NPI": p.npi,
                "REVOCATION_RSN": rng.choice(REVOCATION_REASONS),
            }
        )
    return rows


@dataclass
class SyntheticDataset:
    """All 4 generated CSV row sets plus metadata."""

    service_rows: list[dict[str, str]]
    provider_rows: list[dict[str, str]]
    enrollment_rows: list[dict[str, str]]
    revocation_rows: list[dict[str, str]]
    providers: list[Provider]


# Version strings used when loading into Postgres
SYNTHETIC_VERSIONS: dict[str, str] = {
    "part_b_service": "synthetic_2023",
    "part_b_provider": "synthetic_2023",
    "enrollment": "synthetic_q4_2025",
    "revocations": "synthetic_q1_2026",
}


def generate_all(seed: int = SEED) -> SyntheticDataset:
    """Generate all 4 synthetic CMS datasets in memory.

    Returns a :class:`SyntheticDataset` with row lists ready for CSV writing
    or direct loading via :func:`src.pipeline.raw_loader.load_raw_csv`.
    """
    rng = random.Random(seed)
    providers = generate_providers(rng)
    service_rows = generate_service_rows(rng, providers)
    provider_rows = derive_provider_rows(service_rows, providers)
    enrollment_rows = generate_enrollment_rows(providers)
    revocation_rows = generate_revocation_rows(rng, providers)
    return SyntheticDataset(
        service_rows=service_rows,
        provider_rows=provider_rows,
        enrollment_rows=enrollment_rows,
        revocation_rows=revocation_rows,
        providers=providers,
    )
