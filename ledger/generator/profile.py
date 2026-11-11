from dataclasses import dataclass

DEFAULT_SEED = 20261022


@dataclass(frozen=True)
class Profile:
    name: str
    students: int
    programs: int
    invoices: int
    scholarships: int
    payments: int
    seed: int = DEFAULT_SEED
    anomaly_rate: float = 0.002


PROFILES = {
    "starter": Profile("starter", students=500, programs=20, invoices=1500, scholarships=750, payments=2500,
                       anomaly_rate=0.01),
    "full": Profile("full", students=10000, programs=20, invoices=30000, scholarships=15000, payments=50000),
}


def scaled(scale: float, seed: int = DEFAULT_SEED) -> Profile:
    full = PROFILES["full"]
    return Profile(
        f"scale-{scale}",
        students=max(20, round(full.students * scale)),
        programs=full.programs,
        invoices=max(60, round(full.invoices * scale)),
        scholarships=max(30, round(full.scholarships * scale)),
        payments=max(100, round(full.payments * scale)),
        seed=seed,
        anomaly_rate=full.anomaly_rate if scale >= 0.5 else 0.01,
    )


def anomaly_count(profile: Profile, base: int) -> int:
    return max(3, round(base * profile.anomaly_rate))
