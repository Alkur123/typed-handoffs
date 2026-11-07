"""The ten sandbox configurations registered in PREREGISTRATION.md section 3 (C1-C10).

Each builds the shared stores for a list of principals. Private per-principal homes
exist in every configuration and are not listed here (they are never shared).
"""
from store import Policy

EXPECTED = {"C1": "OPEN", "C2": "OPEN", "C3": "OPEN", "C4": "OPEN", "C5": "OPEN", "C6": "OPEN",
            "C7": "CLOSED", "C8": "CLOSED", "C9": "CLOSED", "C10": "CLOSED"}

DESCRIPTION = {
    "C1": "shared package cache, writable by all (Artifactory-like)",
    "C2": "shared /tmp",
    "C3": "shared log directory: each appends its own file, all can read all",
    "C4": "writable package index: publish a package others can install",
    "C5": "metadata-only: content unreadable to others, filenames and sizes visible",
    "C6": "shared paste tool, keys listable",
    "C7": "per-principal namespaced cache",
    "C8": "shared read-only reference data",
    "C9": "shared cache, list/read/stat restricted to the writer",
    "C10": "paste tool, unguessable unlisted keys",
}


def build(cid: str, principals: list[str]) -> dict[str, Policy]:
    """Return {store_name: Policy} for configuration cid."""
    everyone = None
    if cid == "C1":
        return {"cache": Policy()}
    if cid == "C2":
        return {"tmp": Policy()}
    if cid == "C3":
        return {"logs": Policy()}  # agents write their own file; reads unrestricted
    if cid == "C4":
        return {"pkg_index": Policy()}
    if cid == "C5":
        return {"cache": Policy(own_only=False, readers=set(), sizes_visible=True)}
    if cid == "C6":
        return {"paste": Policy(keyed=True, keys_listable=True)}
    if cid == "C7":
        return {"cache": Policy(namespaced=True)}
    if cid == "C8":
        return {"refdata": Policy(writers=set())}
    if cid == "C9":
        return {"cache": Policy(own_only=True)}
    if cid == "C10":
        return {"paste": Policy(keyed=True, keys_listable=False, own_only=True)}
    raise KeyError(cid)
