from .anomalies import finalize_ground_truth, inject_balance_drift, inject_source_anomalies
from .awards import build_awards
from .billing import build_billing
from .dataset import Dataset
from .derive import derive_all
from .enrollments import build_enrollments_and_invoices
from .masters import build_masters
from .profile import Profile, anomaly_count


def build(profile: Profile, anomalies: bool = True) -> Dataset:
    ds = Dataset(profile)
    duplicates = anomaly_count(profile, profile.invoices) if anomalies else 0
    build_masters(ds)
    build_enrollments_and_invoices(ds, profile.invoices - duplicates)
    build_awards(ds, profile.scholarships)
    build_billing(ds, profile.payments)
    if anomalies:
        inject_source_anomalies(ds)
    derive_all(ds.tables)
    if anomalies:
        inject_balance_drift(ds)
    finalize_ground_truth(ds)
    return ds
