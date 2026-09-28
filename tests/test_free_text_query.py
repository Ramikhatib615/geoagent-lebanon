"""Unit tests for free_text_query.py (R23, 2026-09-25). Plain assert-based, no framework dependency,
matching the project's existing tests/ style. Run with: python3 tests/test_free_text_query.py (from the repo root).
Packaging note (geoagent-lebanon repo): this file moved here from src/geoagent/ so all 5 suites live under tests/;
the two lines below are the only change from the original (a sys.path insert so the import still resolves), no
test logic or assertions were touched."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src", "geoagent"))
from free_text_query import parse_query, normalize_arabic, _extract_block_id, _extract_years

PASS = 0
FAIL = 0


def check(name, cond, detail=""):
    global PASS, FAIL
    if cond:
        PASS += 1
    else:
        FAIL += 1
        print("FAIL: %s %s" % (name, detail))


# --- Arabic normalisation -----------------------------------------------
check("diacritics_stripped", normalize_arabic("بيروتَ") == normalize_arabic("بيروت"))
check("alef_forms_unified", normalize_arabic("أحمد") == normalize_arabic("احمد"))
check("taa_marbuta_unified", normalize_arabic("حارة") == normalize_arabic("حاره"))
check("arabic_indic_digits", normalize_arabic("١٢٣") == "123")

# --- entity extraction ----------------------------------------------------
check("block_id_padded", _extract_block_id("tell me about E45") == "E045")
check("block_id_full", _extract_block_id("evidence for E001") == "E001")
check("block_id_none", _extract_block_id("no block here") is None)
check("years", _extract_years("changes between 2018 and 2025") == [2018, 2025])

# --- the 7 intents in English ---------------------------------------------
r = parse_query("list places in Mount Lebanon Governorate")
check("en_list_places", r.tool == "list_places", r)

r = parse_query("how has Beirut changed between 2018 and 2025")
check("en_change_summary", r.tool == "change_summary" and r.args.get("place", "").lower().find("beirut") >= 0, r)

r = parse_query("evidence for block E045")
check("en_block_evidence", r.tool == "block_evidence" and r.args.get("block_id") == "E045", r)

r = parse_query("which blocks need review in Hazmieh")
check("en_uncertainty", r.tool == "uncertainty" and "hazmieh" in r.args.get("place", "").lower(), r)

r = parse_query("compare Byblos with Baabda")
check("en_compare_places", r.tool == "compare_places" and r.args.get("place_a", "").lower() == "byblos" and r.args.get("place_b", "").lower() == "baabda", r)

r = parse_query("what share of Beirut changed")
check("en_area_estimate", r.tool == "area_estimate" and r.args.get("aoi") == "beirut", r)

r = parse_query("how many blocks show quarry activity in Beirut")
check("en_query_blocks", r.tool == "query_blocks" and r.args.get("change_type") == "quarry_earthworks" and r.args.get("aoi") == "beirut", r)

# --- the 7 intents in Arabic ----------------------------------------------
r = parse_query("اذكر الأماكن في جبل لبنان")
check("ar_list_places", r.tool == "list_places", r)

r = parse_query("كيف تغيرت بيروت")
check("ar_change_summary", r.tool == "change_summary" and "بيروت" in r.args.get("place", ""), r)

r = parse_query("قارن بين حازمية والدورة")
check("ar_compare_places", r.tool == "compare_places" and len(r.args.get("place_a", "")) > 0 and len(r.args.get("place_b", "")) > 0, r)

r = parse_query("ما هي نسبة التغيير في بيروت")
check("ar_area_estimate", r.tool == "area_estimate" and r.args.get("aoi") == "beirut", r)

r = parse_query("كم كتلة فيها تغير في بيروت")
check("ar_query_blocks", r.tool == "query_blocks" and r.args.get("aoi") == "beirut", r)

# --- regression tests for bugs found during this session's own testing ----
# (1) a blanket diacritics regex range (064B-0670) silently ate the Arabic-Indic digit block
#     (0660-0669), which sits inside that range -- digits must survive normalisation.
check("regression_digit_survives", "2025" in normalize_arabic("عام ٢٠٢٥"), "Arabic-Indic 2025 should normalise to ASCII 2025, not be deleted")
# (2) Arabic keyword literals with taa marbuta ("نسبة") or hamza-alef ("الأماكن") must match text
#     that normalize_arabic() has rewritten (taa marbuta -> haa, hamza-alef -> bare alef) -- this
#     silently broke EVERY Arabic keyword containing those letters until keyword lists were
#     normalised at lookup time too.
r = parse_query("ما نسبة التغيير في صفرا")
check("regression_taa_marbuta_keyword", r.tool == "area_estimate", "نسبة (taa marbuta) must still match after normalize_arabic rewrites it to نسبه; got %r" % (r,))
# (3) "compare X with Y" (not just "X and Y") must split correctly.
r = parse_query("compare Baabda with Fanar")
check("regression_compare_with", r.tool == "compare_places" and r.args.get("place_a", "").lower() == "baabda" and r.args.get("place_b", "").lower() == "fanar", r)
# (4) Arabic "و" attached directly to the next word (no space after it), e.g. "حازمية والدورة"
#     ("Hazmieh and Al Daoura"), must still split into two spans.
r = parse_query("قارن بين حازمية والدورة")
check("regression_attached_waw", len(r.args.get("place_a", "")) > 0 and len(r.args.get("place_b", "")) > 0 and r.args.get("place_a") != r.args.get("place_b"), r)
# (5) a trailing "between <year> and <year>" clause must not leak into the extracted place span
#     (tools.py's resolve() only matches a query that is a substring of a known place name, so a
#     messy span like "Hazmieh between 2018 and 2025" would silently fail to resolve at all).
r = parse_query("how has Hazmieh changed between 2018 and 2025")
check("regression_year_clause_stripped", r.args.get("place", "") == "Hazmieh", "expected clean 'Hazmieh', got %r" % (r.args,))
# (6) an Arabic conjugated verb form ("تغيرت") must be stripped whole, not leave a stray letter
#     behind from a shorter keyword ("تغير") partially matching its prefix.
r = parse_query("كيف تغيرت حازمية")
check("regression_conjugation_debris", r.args.get("place", "") == "حازمية", "expected clean حازمية with no leftover letters, got %r" % (r.args,))

# --- bare block-id fallback (no keyword) -----------------------------------
r = parse_query("E045")
check("bare_block_id", r.tool == "block_evidence" and r.args.get("block_id") == "E045", r)

# --- underspecified compare --------------------------------------------
r = parse_query("compare")
check("underspecified_compare", r.intent == "compare_places" and r.tool is None, r)

# --- regression test: place-order bug found in the R22 draft (now fixed by
#     construction, since we split on " with "/" and " in original text order
#     rather than sorting matched ids) -----------------------------------
r = parse_query("compare Byblos with Baabda")
check("ar_compare_places_order", r.args.get("place_a", "").lower() == "byblos" and r.args.get("place_b", "").lower() == "baabda",
      "expected place_a=byblos place_b=baabda (input order), got %r" % (r.args,))

print("\n%d passed, %d failed" % (PASS, FAIL))
sys.exit(1 if FAIL else 0)
