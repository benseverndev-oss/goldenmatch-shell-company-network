"""National-registry adapters for corroboration-side point-query lookups.

Each adapter wraps a country's official corporate registry API and
returns a normalised :class:`~shellnet.registries.base.RegistryHit`
object. The corroboration script uses these to verify cluster-member
companies against authoritative state sources.

Available adapters
------------------

================ ===================================== =========================
Country          Adapter                               Coverage
================ ===================================== =========================
Norway           ``brreg_norway.BrregNorwayAdapter``   Full: officers, addresses,
                                                       roles, NACE code (NLOD)
France           ``inpi_france.InpiFranceAdapter``     Full: officers,
                                                       shareholders, capital
Ireland          ``cro_ireland.CroIrelandAdapter``     Limited: basic company
                                                       data (CKAN open data)
Netherlands      ``kvk_netherlands.KvkNetherlandsAdapter`` Limited: name/status
                                                       only without paid key
================ ===================================== =========================

Design choices
--------------

* **Point-query only.** These are LEI / national-ID -keyed lookups, not
  bulk-ingest. Bulk-ingest for these jurisdictions is parked until a
  cluster surfaces enough hits there to justify the engineering.
* **No required API keys for the working adapters.** Norway and France
  both ship usable free tiers. Ireland's CKAN is open. The
  Netherlands KvK adapter is a stub because the free tier returns only
  name + status (officer data is paid).
* **Output normalised to FollowTheMoney-friendly shape.** Each hit
  carries the official name, jurisdiction, registry, identifier,
  status, dates, and a list of officers. Drops into the corroboration
  evidence ledger without reshuffling.
"""

from shellnet.registries.base import (
    RegistryAdapter,
    RegistryError,
    RegistryHit,
    RegistryOfficer,
)

__all__ = [
    "RegistryAdapter",
    "RegistryError",
    "RegistryHit",
    "RegistryOfficer",
]
