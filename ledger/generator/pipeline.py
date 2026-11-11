from .awards import build_awards
from .billing import build_billing
from .dataset import Dataset
from .derive import derive_all
from .enrollments import build_enrollments_and_invoices
from .masters import build_masters
from .profile import Profile


def build(profile: Profile) -> Dataset:
    ds = Dataset(profile)
    build_masters(ds)
    build_enrollments_and_invoices(ds, profile.invoices)
    build_awards(ds, profile.scholarships)
    build_billing(ds, profile.payments)
    derive_all(ds.tables)
    return ds
