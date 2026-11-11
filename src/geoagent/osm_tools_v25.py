"""Registers the READ-ONLY historical-OSM tools (osm_hist_tools.py) in tools.TOOLS so that every server that imports this
module lists and calls them. Rule: OSM MAPPING change is not PHYSICAL building change. No write function exists."""
import tools as _t
import osm_hist_tools as _o
_L = {"type": "string", "enum": ["auto", "en", "ar"], "description": "language of the answer and caveat"}
_B = {"type": "string", "description": "block id such as N329_075 (row_col) of one of the 300 human-reviewed blocks"}
import restricted_data as _rd
def _G(fn): return _rd.guard(fn, "block-level historical OpenStreetMap features", "GEOAGENT_OSM_HIST", "data/osm_hist/block_osm_features_300.csv")
TOOLS_V24 = {
 "osm_block_history": (_o.osm_block_history, "Mapped OSM building history of one reviewed block (2018-09-15, 2025-09-15, 2022): counts, covered area, transition categories, with the mapping-vs-physical caveat. Read-only.", {"block_id": _B, "lang": _L}, ["block_id"]),
 "osm_mapping_vs_physical": (_o.osm_mapping_vs_physical, "Explains why an OSM mapping change is not a physical building change and what evidence would be needed. Read-only.", {"lang": _L}, []),
 "osm_building_free_status": (_o.osm_building_free_status, "Status of a block with zero mapped footprints: never 'building-free' without imagery review. Read-only.", {"block_id": _B, "lang": _L}, ["block_id"]),
 "osm_vs_scores": (_o.osm_vs_scores, "Blocks where the OSM change and the spectral score disagree. kind: osm_increase_low_spectral | high_spectral_no_osm_change.", {"kind": {"type": "string", "enum": ["osm_increase_low_spectral", "high_spectral_no_osm_change"]}, "lang": _L, "n": {"type": "integer"}}, ["kind"]),
 "osm_region_coverage": (_o.osm_region_coverage, "Mapped-footprint counts and growth by governorate, 2018 vs 2025 (mapping imbalance, not construction). Read-only.", {"lang": _L}, []),
 "osm_contradictions": (_o.osm_contradictions, "Blocks where OSM evidence and the human label or model scores contradict each other. Read-only.", {"lang": _L, "n": {"type": "integer"}}, []),
 "osm_physical_verification": (_o.osm_physical_verification, "Physical verification status of OSM building changes: always 'pending' (no dated imagery review exists). Read-only.", {"block_id": _B, "lang": _L}, []),
}
for _n, _v in TOOLS_V24.items():
    if _n in _t.TOOLS: raise RuntimeError("tool name clash: " + _n)
    _t.TOOLS[_n] = (_G(_v[0]),) + tuple(_v[1:])

# ---- Aggregate added after an agent test showed that no tool returned the count of blocks with no mapped footprint ----
def osm_zero_footprint_summary(lang="auto", governorate=""):
    """READ-ONLY aggregate: how many of the 300 reviewed blocks have zero MAPPED footprints per snapshot and in all three. Never 'building-free'."""
    import osm_hist_tools as _oo
    rs=_oo._rows(); l=_oo._lang(lang,governorate)
    g=_oo._gov(governorate) if governorate else None
    if governorate and not g: return {"found":False,"error":"unknown governorate; use e.g. Akkar, Bekaa, Baalbek-Hermel, Beirut, Mount Lebanon, Nabatiye, North, South"}
    if g: rs=[r for r in rs if r["governorate"]==g]
    z=lambda r,k:int(r[k])==0
    out={"found":True,"scope":g or "all 300 human-reviewed blocks","n_blocks":len(rs),
         "zero_mapped_footprints":{"2018":sum(z(r,"2018_n") for r in rs),"2022":sum(z(r,"osm_building_count_2022") for r in rs),"2025":sum(z(r,"2025_n") for r in rs),
                                   "all_three_snapshots":sum(z(r,"2018_n") and z(r,"osm_building_count_2022") and z(r,"2025_n") for r in rs)},
         "verified_building_free":0,
         "statement":("عدد الكتل بلا أي مضلّع مرسوم؛ لا تعني أنها خالية من المباني، والتحقق التصويري البشري معلّق." if l=="ar" else "Counts of blocks with NO MAPPED footprint per snapshot. This is not a count of building-free blocks: zero verified building-free blocks exist, because no dated-imagery review has been done."),
         "caveat":_oo._cav(l)}
    return out
_t.TOOLS["osm_zero_footprint_summary"]=(_G(osm_zero_footprint_summary),"Counts of the 300 reviewed blocks with zero MAPPED OSM footprints in 2018, 2022, 2025 and in all three (optionally by governorate). Never 'building-free'. Read-only.",
    {"lang":_L,"governorate":{"type":"string","description":"optional governorate name, e.g. Akkar"}},[])
