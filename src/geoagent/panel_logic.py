"""Pure-Python logic of the QGIS GeoAgent panel (no QGIS imports, so it can be unit-tested headlessly).

Validation of form input, rendering of tool results as readable HTML (English or Arabic, right-to-left aware),
extraction of block ids for map selection, and a self-test that exercises every tool.
Nothing here changes any tool behaviour: results are exactly those of tools.call().
"""
import html
import re

ID_RE = re.compile(r"E\d{3}")
LABELS = ["change", "no_change", "uncertain"]
GROUP_BY = ["label", "change_type", "stratum", "aoi", "governorate", "place_en", "label_source"]
HIDDEN_KEYS = {"message", "interpretation_note", "note", "caveats", "block_ids", "found", "lang"}
MAX_ROWS = 60


def enum_choices(blocks):
    """Dropdown values for the fixed-vocabulary filters, read from the data so they can never drift from the tool layer."""
    vals = lambda k: sorted({str(b[k]) for b in blocks.values() if b.get(k) not in (None, "")})
    return {
        "aoi": [""] + vals("aoi"),
        "label": [""] + LABELS,
        "stratum": [""] + ["low", "mid", "high"],
        "label_source": [""] + vals("label_source"),
        "annotator_a": [""] + LABELS,
        "annotator_b": [""] + LABELS,
        "change_type": [""] + vals("change_type"),
        "group_by": [""] + GROUP_BY,
        "governorate": [""] + vals("governorate"),
        "annotators_disagree": ["", "true", "false"],
        "lang": ["auto", "en", "ar"],
    }


def parse_values(spec_params, required, raw):
    """raw: field name -> text typed/chosen by the user. Returns (kwargs, errors). Never raises."""
    kw, errors = {}, []
    for k, spec in spec_params.items():
        t = (raw.get(k) or "").strip()
        if t == "":
            if k in required:
                errors.append("'%s' is required." % k)
            continue
        try:
            if k == "annotators_disagree" or spec.get("type") == "boolean":
                if t.lower() not in ("true", "false"):
                    raise ValueError
                kw[k] = t.lower() == "true"
            elif spec.get("type") == "integer":
                kw[k] = int(t)
                if kw[k] < 1 and k == "limit":
                    errors.append("'limit' must be 1 or more.")
            elif spec.get("type") == "number":
                kw[k] = float(t.replace(",", "."))
            else:
                kw[k] = t
        except ValueError:
            errors.append("'%s' must be %s (got %r)." % (k, {"integer": "a whole number", "number": "a number", "boolean": "true or false"}.get(spec.get("type"), "valid"), t))
    for lo, hi in (("min_lat", "max_lat"), ("min_lon", "max_lon")):
        if lo in kw and hi in kw and kw[lo] >= kw[hi]:
            errors.append("'%s' must be smaller than '%s'." % (lo, hi))
    if "block_id" in kw and not ID_RE.fullmatch(kw["block_id"].upper()):
        errors.append("'block_id' must look like E067 (E001..E200).")
    return kw, errors


def collect_ids(o, out):
    """Every block id mentioned in a result, in stable sorted order (no duplicates)."""
    if isinstance(o, dict):
        for k, v in o.items():
            if k == "block_ids" and isinstance(v, list):
                out.extend(x for x in v if isinstance(x, str) and ID_RE.fullmatch(x))
            elif k in ("id", "block_id") and isinstance(v, str) and ID_RE.fullmatch(v):
                out.append(v)
            else:
                collect_ids(v, out)
    elif isinstance(o, list):
        for v in o:
            collect_ids(v, out)
    return sorted(set(out))


def _num(x):
    if isinstance(x, float):
        return ("%.4f" % x).rstrip("0").rstrip(".")
    return str(x)


def pretty(v, depth=0):
    """Compact human-readable text for a scalar, list or dict (used inside table cells)."""
    if v is None:
        return "—"
    if isinstance(v, bool):
        return "yes" if v else "no"
    if isinstance(v, (int, float)):
        return _num(v)
    if isinstance(v, str):
        return v
    if isinstance(v, list):
        if not v:
            return "—"
        items = [pretty(x, depth + 1) for x in v[:12]]
        return ", ".join(items) + (" … (+%d)" % (len(v) - 12) if len(v) > 12 else "")
    if isinstance(v, dict):
        if "place_en" in v and "place_ar" in v and len(v) == 2:
            return "%s (%s)" % (v["place_en"], v["place_ar"])
        return "; ".join("%s: %s" % (k.replace("_", " "), pretty(x, depth + 1)) for k, x in v.items() if k not in ("caveats", "block_ids"))
    return str(v)


def _esc(s):
    return html.escape(str(s))


def _list_table(rows):
    """List of flat dicts -> HTML table (columns = union of scalar-ish keys)."""
    cols = []
    for r in rows[:MAX_ROWS]:
        for k in r:
            if k not in cols and not k.endswith("_localised"):
                cols.append(k)
    head = "".join("<th align='left' style='padding:2px 10px 2px 0'>%s</th>" % _esc(c.replace("_", " ")) for c in cols)
    body = ""
    for r in rows[:MAX_ROWS]:
        body += "<tr>" + "".join("<td dir='auto' style='padding:2px 10px 2px 0'>%s</td>" % _esc(pretty(r.get(c))) for c in cols) + "</tr>"
    more = "<p><i>… %d more rows (see Raw JSON)</i></p>" % (len(rows) - MAX_ROWS) if len(rows) > MAX_ROWS else ""
    return "<table cellspacing='0'><tr>%s</tr>%s</table>%s" % (head, body, more)


def render_answer(res, ids=None):
    """Result dict -> HTML for the Answer tab. Numbers and wording come straight from the tool result."""
    if not isinstance(res, dict):
        return "<pre>%s</pre>" % _esc(res)
    parts = []
    if res.get("error"):
        parts.append("<p style='color:#b00020'><b>Error:</b> %s</p>" % _esc(res["error"]))
    if res.get("message"):
        colour = "#b45f06" if res.get("found") is False else "#0b5394"
        parts.append("<p dir='auto' style='font-size:14px;color:%s'><b>%s</b></p>" % (colour, _esc(res["message"])))
    if res.get("interpretation_note"):
        parts.append("<p dir='auto'><i>%s</i></p>" % _esc(res["interpretation_note"]))
    if res.get("note"):
        parts.append("<p dir='auto'><i>%s</i></p>" % _esc(res["note"]))
    if res.get("suggestions"):
        parts.append("<p dir='auto'>Did you mean: <b>%s</b></p>" % _esc(", ".join(res["suggestions"])))
    simple, blocks_tables = [], []
    for key, val in res.items():
        if key in HIDDEN_KEYS or key == "suggestions" or (key + "_localised") in res:
            continue
        if isinstance(val, list) and val and all(isinstance(x, dict) for x in val):
            blocks_tables.append("<p><b>%s</b> (%d)</p>%s" % (_esc(key.replace("_", " ")), len(val), _list_table(val)))
        elif isinstance(val, list) and val and all(isinstance(x, str) and ID_RE.fullmatch(x) for x in val):
            continue
        elif isinstance(val, dict) and key in ("a", "b") and val.get("found"):
            simple.append("<tr><td valign='top' style='padding-right:14px'><b>%s</b></td><td dir='auto'>%s</td></tr>" % (_esc(key.upper()), _esc(pretty({k: x for k, x in val.items() if k not in ("found", "query", "match_type")}))))
        else:
            simple.append("<tr><td valign='top' style='padding-right:14px'><b>%s</b></td><td dir='auto'>%s</td></tr>" % (_esc(key.replace("_", " ")), _esc(pretty(val))))
    if simple:
        parts.append("<table cellspacing='0'>" + "".join(simple) + "</table>")
    parts.extend(blocks_tables)
    if ids:
        parts.append("<p dir='auto'><b>Blocks (%d):</b> %s%s</p>" % (len(ids), _esc(", ".join(ids[:60])), " …" if len(ids) > 60 else ""))
    if res.get("truncated"):
        parts.append("<p><i>The tool lists at most 100 block ids; refine the filters to see the rest.</i></p>")
    cav = res.get("caveats") or []
    if cav:
        parts.append("<hr><p><b>Caveats</b></p><ul>%s</ul>" % "".join("<li dir='auto'>%s</li>" % _esc(c) for c in cav))
    return "".join(parts)


def zero_hint(name, res):
    """One-line hint when a query silently matches nothing (the tool layer filters by exact values)."""
    if name == "query_blocks" and isinstance(res, dict) and res.get("n_blocks") == 0:
        return "0 blocks match all of these filters together (values may be given in English or Arabic; latitude/longitude bounds are of block centres)."
    return ""


SELF_TESTS = [
    ("list_places", {"limit": 3}, lambda r: r.get("found") and len(r["places"]) == 3),
    ("change_summary", {"place": "Dahieh"}, lambda r: r.get("found") and r["n_blocks"] == 20),
    ("change_summary", {"place": "الضاحية الجنوبية", "lang": "ar"}, lambda r: r.get("found") and r["n_blocks"] == 20),
    ("change_summary", {"place": "Atlantis"}, lambda r: r.get("found") is False),
    ("block_evidence", {"block_id": "E067"}, lambda r: r.get("id") == "E067" and r.get("label") == "no_change"),
    ("uncertainty", {"place": "Dahieh"}, lambda r: r.get("found") and r["n_deferred"] == 5),
    ("compare_places", {"place_a": "Dahieh", "place_b": "Hazmieh"}, lambda r: r.get("found") and r.get("ranking_allowed") is True),
    ("query_blocks", {}, lambda r: r["n_blocks"] == 200 and r["n_decided"] == 182),
    ("area_estimate", {"aoi": "beirut"}, lambda r: abs(r["share_change_weighted"] - 0.1635) < 1e-4),
]


def self_test(tools):
    """Runs every tool once with a known expectation (values from the reference data). Returns (n_ok, n_total, failures)."""
    fails = []
    for name, kw, check in SELF_TESTS:
        try:
            res = tools.call(name, **kw)
            if not check(res):
                fails.append("%s %s: unexpected result" % (name, kw))
            elif not res.get("caveats") and res.get("found", True):
                fails.append("%s: caveats missing" % name)
            render_answer(res, collect_ids(res, []))
        except Exception as e:  # a self-test must report, never crash the panel
            fails.append("%s %s: %s: %s" % (name, kw, type(e).__name__, e))
    return len(SELF_TESTS) - len(fails), len(SELF_TESTS), fails
