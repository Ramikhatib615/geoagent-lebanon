"""GeoAgent-Lebanon tool layer (R5): bilingual (Arabic / English) read-only tools over the reference layer.

Pure standard library. Every function returns a JSON-serialisable dict; nothing is estimated that is not in the files.
Data sources (outputs/eval): eval_reference.geojson, eval_places.csv, reference_labels_AI_consensus.csv,
change_types_consensus.csv, change_types/ct_index.json, conformal_results_AI_consensus.json.

IMPORTANT semantics that every answer carries in `caveats`:
  * the 200 blocks (420 m x 420 m) are a stratified SAMPLE of two AOIs (Beirut, Mount Lebanon), not full coverage;
  * labels are AI consensus (two annotators + adjudication), NOT human ground truth; `human_check` is filled only where a person checked;
  * the place name is the nearest named place to the block centre (OSM / Nominatim), not the administrative extent of that place;
  * change = visible change between Sentinel-2 composites of 2018 and 2025 (10 m), so small changes can be missed.
"""
import csv, json, os, random, re, unicodedata, difflib

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
EV = os.path.join(ROOT, "outputs", "eval")

LABEL_AR = {"change": "تغيّر", "no_change": "لا تغيّر", "uncertain": "غير مؤكد"}
TYPE_AR = {"new_construction": "بناء جديد", "quarry_earthworks": "محاجر / أعمال حفر وتسوية", "demolition_damage": "هدم / أضرار",
           "greenhouse_agri": "بيوت زراعية / نشاط زراعي", "vegetation_change": "تغيّر في الغطاء النباتي", "other_unclear": "أخرى / غير واضح"}
STATUS_AR = {"agreed": "اتفق المصنّفان", "adjudicated": "حُسم بعد اختلاف", "uncertain": "غير مؤكد"}
AOI_AR = {"beirut": "بيروت", "mount_lebanon": "جبل لبنان"}
STRATUM_AR = {"low": "منخفض", "mid": "متوسط", "high": "مرتفع"}
GOV_AR = {"Beirut Governorate": "محافظة بيروت", "Mount Lebanon Governorate": "محافظة جبل لبنان", "Keserwan-Jbeil Governorate": "محافظة كسروان - جبيل"}
# R24 (2026-09-25): categorical filters accept canonical values, Arabic values and common variants; an unknown value now
# returns an explicit error with the valid values instead of a silent empty result (bug found by R13 / R17 audit).
_LABEL_SYN = {"no change": "no_change", "nochange": "no_change", "unchanged": "no_change", "not changed": "no_change", "changed": "change",
              "unsure": "uncertain", "unclear": "uncertain", "بلا تغيّر": "no_change", "لا يوجد تغيّر": "no_change", "لم يتغيّر": "no_change",
              "دون تغيّر": "no_change", "تغيير": "change", "متغيّر": "change", "غير واضح": "uncertain", "غير مؤكدة": "uncertain"}
_VOCAB = {
    "label": (LABEL_AR, _LABEL_SYN),
    "annotator": (LABEL_AR, _LABEL_SYN),
    "change_type": (TYPE_AR, {"construction": "new_construction", "new building": "new_construction", "new buildings": "new_construction",
                              "quarry": "quarry_earthworks", "quarries": "quarry_earthworks", "earthworks": "quarry_earthworks",
                              "demolition": "demolition_damage", "damage": "demolition_damage", "greenhouse": "greenhouse_agri",
                              "greenhouses": "greenhouse_agri", "agriculture": "greenhouse_agri", "vegetation": "vegetation_change",
                              "other": "other_unclear", "unclear": "other_unclear", "بناء": "new_construction", "بناء جديد": "new_construction",
                              "عمران جديد": "new_construction", "محاجر": "quarry_earthworks", "محجر": "quarry_earthworks", "أعمال حفر": "quarry_earthworks",
                              "هدم": "demolition_damage", "أضرار": "demolition_damage", "دمار": "demolition_damage", "بيوت زراعية": "greenhouse_agri",
                              "بيوت بلاستيكية": "greenhouse_agri", "زراعي": "greenhouse_agri", "غطاء نباتي": "vegetation_change",
                              "نباتي": "vegetation_change", "أخرى": "other_unclear", "غير واضح": "other_unclear"}),
    "label_source": ({"agreed": STATUS_AR["agreed"], "adjudicated": STATUS_AR["adjudicated"]},
                     {"agree": "agreed", "agreement": "agreed", "adjudication": "adjudicated", "disagreed": "adjudicated", "اتفاق": "agreed",
                      "متفق عليه": "agreed", "اتفق": "agreed", "حسم": "adjudicated", "محسوم": "adjudicated", "حُسم": "adjudicated"}),
    "aoi": (AOI_AR, {"greater beirut": "beirut", "beirut aoi": "beirut", "mount lebanon": "mount_lebanon", "mount lebanon aoi": "mount_lebanon",
                     "mt lebanon": "mount_lebanon", "بيروت الكبرى": "beirut", "منطقة بيروت": "beirut", "منطقة جبل لبنان": "mount_lebanon"}),
    "stratum": (STRATUM_AR, {"medium": "mid", "middle": "mid", "moderate": "mid", "منخفضة": "low", "متدني": "low", "متوسطة": "mid",
                             "مرتفعة": "high", "عالي": "high", "عالية": "high"}),
}
CAVEATS_EN = ["Blocks are a stratified sample of 420 m blocks in two AOIs (Beirut, Mount Lebanon), not full coverage of any place.",
              "Labels are AI consensus (two independent AI annotators plus adjudication), not human ground truth, unless human_check is filled.",
              "The place name is the nearest named place to the block centre, not the administrative extent of that place.",
              "Change means visible change between Sentinel-2 composites of 2018 and 2025 at 10 m resolution; small changes can be missed."]
CAVEATS_AR = ["الكتل عيّنة طبقية من كتل 420 م في منطقتين (بيروت وجبل لبنان) وليست تغطية كاملة لأي مكان.",
              "التصنيفات إجماع مصنّفين آليين (مصنّفان مستقلان مع حسم الخلاف) وليست حقيقة ميدانية بشرية ما لم يُملأ حقل human_check.",
              "اسم المكان هو أقرب مكان مُسمّى إلى مركز الكتلة وليس الامتداد الإداري لذلك المكان.",
              "التغيّر يعني تغيّراً مرئياً بين مركّبات Sentinel-2 لعامي 2018 و2025 بدقة 10 م، وقد تفوت التغيّرات الصغيرة."]

_DIAC = re.compile("[ً-ٰٟـ]")
_cache = {}


def _is_ar(s):
    return bool(re.search("[؀-ۿ]", s or ""))


def norm(s):
    """Normalise a place name for matching: Arabic diacritics/tatweel removed, alef/yaa/taa-marbuta unified, Latin casefolded, punctuation dropped."""
    s = unicodedata.normalize("NFKC", (s or "")).strip()
    s = _DIAC.sub("", s)
    s = re.sub("[أإآٱ]", "ا", s).replace("ى", "ي").replace("ة", "ه")
    s = s.casefold()
    s = re.sub(r"[^\w؀-ۿ ]+", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def _strip_article(s):
    s = re.sub(r"^(al|el|ad|as|ash|an)[ -]+", "", s)
    return s[2:] if s.startswith("ال") and len(s) > 3 else s


def _rd(fn):
    with open(os.path.join(EV, fn), encoding="utf-8-sig", newline="") as f:
        return {r["id"]: r for r in csv.DictReader(f)}


def load():
    if "d" in _cache:
        return _cache["d"]
    g = json.load(open(os.path.join(EV, "eval_reference.geojson"), encoding="utf-8"))
    ct = _rd("change_types_consensus.csv") if os.path.exists(os.path.join(EV, "change_types_consensus.csv")) else {}
    des = _rd("eval_design.csv")
    sheets = {}
    p = os.path.join(EV, "change_types", "ct_index.json")
    if os.path.exists(p):
        for sheet, ids in json.load(open(p)).items():
            for i in ids:
                sheets[i] = sheet
    blocks = {}
    for f in g["features"]:
        pr = f["properties"]; i = pr["id"]; ring = f["geometry"]["coordinates"][0]
        lons = [c[0] for c in ring]; lats = [c[1] for c in ring]
        t = ct.get(i, {})
        blocks[i] = {"id": i, "aoi": pr["aoi"], "stratum": pr["stratum"], "weight": float(pr["weight"]), "label": pr["label"], "label_source": pr["label_source"],
                     "annotator_A": pr["ann_A"], "annotator_B": pr["ann_B"], "place_en": pr["place_en"] or "", "place_ar": pr["place_ar"] or "",
                     "admin_en": pr["admin_en"] or "", "admin_ar": pr["admin_ar"] or "", "governorate": pr["governorate"] or "",
                     "human_check": (pr.get("rami_check") or "").strip(), "centre_lon": round((min(lons) + max(lons)) / 2, 6), "centre_lat": round((min(lats) + max(lats)) / 2, 6),
                     "bbox_lonlat": [round(min(lons), 6), round(min(lats), 6), round(max(lons), 6), round(max(lats), 6)],
                     "screening_score": float(des[i]["score"]) if i in des else None,
                     "change_type": t.get("consensus_type") or None, "change_type_status": t.get("status") or None,
                     "type_conf_A": t.get("conf_A") or None, "type_conf_B": t.get("conf_B") or None,
                     "type_sheet": os.path.join("outputs", "eval", "change_types", sheets[i]) if i in sheets else None}
    conf = {}
    cp = os.path.join(EV, "conformal_results_AI_consensus.json")
    if os.path.exists(cp):
        conf = json.load(open(cp))
    _cache["d"] = {"blocks": blocks, "conformal": conf}
    return _cache["d"]


def _load_audit():
    """Rows of the completed Appendix G human audit (outputs/eval/human_audit_results.csv), keyed by block id.
    Read-only passthrough of a file already produced and verified outside this tool layer; {} if it doesn't exist."""
    d = load()
    if "audit" not in d:
        rows = {}
        p = os.path.join(EV, "human_audit_results.csv")
        if os.path.exists(p):
            with open(p, encoding="utf-8-sig", newline="") as f:
                for r in csv.DictReader(f):
                    rows[r["block_id"]] = r
        d["audit"] = rows
    return d["audit"]


def _load_certainty_units():
    """Block ids the audit protocol pre-registered as 'certainty units' (outputs/eval/human_audit_key_R26.csv,
    certainty_unit == 1): the 8 pivotal no-change blocks that must hold, and the 5 Mount Lebanon-low change blocks
    whose outcome decides Appendix G's Rule 1. Read-only passthrough, fixed before any block was reviewed; {} if missing."""
    d = load()
    if "certainty_units" not in d:
        rows = {}
        p = os.path.join(EV, "human_audit_key_R26.csv")
        if os.path.exists(p):
            with open(p, encoding="utf-8-sig", newline="") as f:
                for r in csv.DictReader(f):
                    if r.get("certainty_unit") == "1":
                        rows[r["block_id"]] = r
        d["certainty_units"] = rows
    return d["certainty_units"]


def _load_json(fn):
    p = os.path.join(EV, fn)
    return json.load(open(p, encoding="utf-8")) if os.path.exists(p) else {}


def _lang(lang, query=""):
    if lang in ("en", "ar"):
        return lang
    return "ar" if _is_ar(query) else "en"


def _names(b):
    return [n for n in (b["place_en"], b["place_ar"], b["admin_en"], b["admin_ar"]) if n]


def resolve(query):
    """Return (block_ids, how). Accepts a block id (E001), or a place / admin name in Arabic or English (exact, then article-insensitive, then substring)."""
    B = load()["blocks"]
    q = (query or "").strip()
    if q.upper() in B:
        return [q.upper()], "id"
    nq = norm(q)
    if not nq:
        return [], "none"
    exact = [i for i, b in B.items() if any(norm(n) == nq for n in (b["place_en"], b["place_ar"]))]
    if exact:
        return exact, "exact"
    aq = _strip_article(nq)
    art = [i for i, b in B.items() if any(_strip_article(norm(n)) == aq for n in (b["place_en"], b["place_ar"]))]
    if art:
        return art, "article_insensitive"
    adm = [i for i, b in B.items() if any(norm(n) == nq for n in (b["admin_en"], b["admin_ar"]))]
    if adm:
        return adm, "admin_area"
    if len(nq) >= 3:
        sub = [i for i, b in B.items() if any(nq in norm(n) for n in _names(b))]
        if sub:
            return sub, "substring"
    return [], "none"


def _suggest(query, k=5):
    B = load()["blocks"]
    # R24: each place is scored by its best-matching form (full name, name without the article, single words of 4+ letters),
    # so an Arabic misspelling of one word of a longer name (e.g. "ضاهيه" for "الضاحية الجنوبية") still gets a suggestion;
    # candidates more than 0.1 below the best one are dropped (R20 V4-5: "Hazmiyeh" also suggested "Adliyeh").
    q = norm(query)
    if not q:
        return []
    score = {}
    for b in B.values():
        en = b["place_en"] or b["place_ar"]
        for n in (b["place_en"], b["place_ar"]):
            if not n:
                continue
            nn = norm(n)
            full = max(difflib.SequenceMatcher(None, f, q).ratio() for f in {nn, _strip_article(nn)})
            words = [_strip_article(w) for w in nn.split() if len(nn.split()) > 1 and len(_strip_article(w)) >= 4]
            part = max([0.9 * difflib.SequenceMatcher(None, w, q).ratio() for w in words] or [0])   # one word of a longer name: small penalty
            r = max(full, part)
            if r > score.get(en, (0, ""))[0]:
                score[en] = (r, en)
    ranked = sorted((v for v in score.values() if v[0] >= 0.6), key=lambda x: (-x[0], x[1]))
    if not ranked:
        return []
    best = ranked[0][0]
    return [n for r, n in ranked[:k] if r >= best - 0.1]


def _lab(l, lang):
    return LABEL_AR.get(l, l) if lang == "ar" else l


def _typ(t, lang):
    return TYPE_AR.get(t, t) if (lang == "ar" and t) else t


def _caveats(lang):
    return CAVEATS_AR if lang == "ar" else CAVEATS_EN


def _not_found(query, lang):
    s = _suggest(query)
    msg = ("لم يتم العثور على مكان مطابق ضمن الكتل المرجعية." if lang == "ar" else "No matching place among the reference blocks.")
    return {"found": False, "query": query, "message": msg, "suggestions": s, "caveats": _caveats(lang)}


def _k(s):
    return norm(str(s)).replace("_", " ")


def _bad_filter(field, value, valid, lang):
    sug = difflib.get_close_matches(_k(value), [_k(v) for v in valid], n=3, cutoff=0.5)
    sug = [v for v in valid if _k(v) in sug]
    en = "Unknown value '%s' for filter '%s'. Valid values: %s." % (value, field, ", ".join(valid))
    ar = "القيمة «%s» غير معروفة للمرشّح «%s». القيم المقبولة: %s." % (value, field, "، ".join(valid))
    return {"found": False, "error": "unknown_filter_value", "filter": field, "value": value, "valid_values": valid, "suggestions": sug,
            "message": ar if lang == "ar" else en, "caveats": _caveats(lang)}


def _canon(field, value, lang):
    """Map a categorical filter value (canonical, Arabic or a common variant; any case / diacritics) to the canonical value.
    Returns (canonical_or_empty, error_dict_or_None). Empty input -> ("", None)."""
    if value in ("", None):
        return "", None
    ar_map, syn = _VOCAB["annotator" if field.startswith("annotator") else field]
    table = {}
    for c, ar in ar_map.items():
        table[_k(c)] = c; table[_k(ar)] = c; table[_strip_article(_k(ar))] = c
    for v, c in syn.items():
        table[_k(v)] = c; table[_strip_article(_k(v))] = c
    k = _k(value)
    if k in table:
        return table[k], None
    if _strip_article(k) in table:
        return table[_strip_article(k)], None
    if len(k) >= 4:
        hits = {c for kk, c in table.items() if k in kk}
        if len(hits) == 1:
            return hits.pop(), None
    valid = list(ar_map)
    return None, _bad_filter(field, value, ["%s (%s)" % (c, ar_map[c]) for c in valid] if lang == "ar" else valid, lang)


def _gov(value, lang):
    """Governorate filter: English substring match (unchanged behaviour) or Arabic name. Returns (set_of_governorates_or_None, error_or_None)."""
    if value in ("", None):
        return None, None
    govs = sorted({b["governorate"] for b in load()["blocks"].values() if b["governorate"]})
    nv = norm(value)
    core = lambda x: re.sub(r"^محافظه ", "", re.sub(r" (governorate|محافظه)$", "", x))
    hits = {g for g in govs if nv and (nv in norm(g) or nv in norm(GOV_AR.get(g, "")) or core(nv) in core(norm(GOV_AR.get(g, ""))))}
    if hits:
        return hits, None
    return None, _bad_filter("governorate", value, ["%s (%s)" % (g, GOV_AR.get(g, "")) for g in govs], lang)


def list_places(query="", governorate="", limit=30, lang="auto"):
    """List named places that have reference blocks, with per-place block counts. Filter by (partial) name in Arabic or English and/or governorate."""
    lang = _lang(lang, query + governorate)
    B = load()["blocks"]
    nq = norm(query)
    govs, err = _gov(governorate, lang)
    if err:
        return err
    agg = {}
    for b in B.values():
        if not (b["place_en"] or b["place_ar"]):
            continue
        if govs is not None and b["governorate"] not in govs:
            continue
        if nq and not any(nq in norm(n) for n in _names(b)):
            continue
        k = (b["place_en"], b["place_ar"])
        a = agg.setdefault(k, {"place_en": b["place_en"], "place_ar": b["place_ar"], "governorate": b["governorate"], "aoi": b["aoi"], "n_blocks": 0, "n_change": 0, "n_no_change": 0, "n_uncertain": 0})
        a["n_blocks"] += 1
        a["n_" + b["label"]] += 1
    rows = sorted(agg.values(), key=lambda r: (-r["n_blocks"], r["place_en"]))
    lim = max(1, min(int(limit), 200))
    return {"found": bool(rows), "total_matching_places": len(rows), "places": rows[:lim], "n_unnamed_blocks": sum(1 for b in B.values() if not (b["place_en"] or b["place_ar"])),
            "message": ("عدد الأماكن المطابقة: %d" % len(rows)) if lang == "ar" else "%d matching places" % len(rows), "caveats": _caveats(lang)}


def _counts(bl):
    lab = {"change": 0, "no_change": 0, "uncertain": 0}
    typ = {}
    for b in bl:
        lab[b["label"]] += 1
        if b["label"] == "change" and b["change_type"]:
            typ[b["change_type"]] = typ.get(b["change_type"], 0) + 1
    return lab, typ


def change_summary(place, lang="auto"):
    """Summarise reference-block evidence of change 2018-2025 for the blocks named after `place` (or a block id). Raw counts, no extrapolation to the whole place."""
    lang = _lang(lang, place)
    ids, how = resolve(place)
    if not ids:
        return _not_found(place, lang)
    B = load()["blocks"]
    bl = [B[i] for i in ids]
    lab, typ = _counts(bl)
    decided = lab["change"] + lab["no_change"]
    en = "%d sampled block(s) matched '%s': %d show change, %d show no change, %d are uncertain." % (len(bl), place, lab["change"], lab["no_change"], lab["uncertain"])
    ar = "عدد الكتل المطابقة لـ«%s»: %d؛ منها %d فيها تغيّر، و%d بلا تغيّر، و%d غير مؤكدة." % (place, len(bl), lab["change"], lab["no_change"], lab["uncertain"])
    names = sorted({(b["place_en"], b["place_ar"]) for b in bl})
    return {"found": True, "query": place, "match_type": how, "matched_places": [{"place_en": a, "place_ar": b_} for a, b_ in names],
            "n_blocks": len(bl), "labels": lab, "labels_localised": {_lab(k, lang): v for k, v in lab.items()},
            "change_types": {_typ(k, lang): v for k, v in sorted(typ.items(), key=lambda x: -x[1])},
            "share_changed_among_decided_blocks": round(lab["change"] / decided, 3) if decided else None,
            "block_ids": ids, "human_checked_blocks": [b["id"] for b in bl if b["human_check"]],
            "message": ar if lang == "ar" else en,
            "interpretation_note": ("النسبة غير موزونة لأن الكتل لم تُسحب باحتمالات متساوية، ولا يجوز تعميمها على كامل المكان." if lang == "ar" else "The share is unweighted (blocks were sampled with unequal probabilities by stratum) and must not be generalised to the whole place."),
            "caveats": _caveats(lang)}


def block_evidence(block_id, lang="auto"):
    """Full evidence record for one reference block: location, both annotators, adjudication, change type, human check, image sheet path."""
    lang = _lang(lang, "")
    B = load()["blocks"]
    i = (block_id or "").strip().upper()
    if i not in B:
        return {"found": False, "query": block_id, "message": ("معرّف الكتلة غير موجود." if lang == "ar" else "Unknown block id."), "valid_id_pattern": "E001..E200", "caveats": _caveats(lang)}
    b = dict(B[i])
    b["found"] = True
    b["label_localised"] = _lab(b["label"], lang)
    b["change_type_localised"] = _typ(b["change_type"], lang)
    b["aoi_localised"] = AOI_AR.get(b["aoi"], b["aoi"]) if lang == "ar" else b["aoi"]
    b["stratum_localised"] = STRATUM_AR.get(b["stratum"], b["stratum"]) if lang == "ar" else b["stratum"]
    b["label_status_localised"] = STATUS_AR.get(b["label_source"], b["label_source"]) if lang == "ar" else b["label_source"]
    aud = _load_audit().get(i)
    if aud:
        differs = bool((aud.get("human_final") or "").strip()) and aud["human_final"] != b["label"]
        b["human_audit"] = {
            "audited": True,
            "human_1": aud.get("human_1") or None,
            "human_2": aud.get("human_2") or None,
            "human_final": aud.get("human_final") or None,
            "interpretation_sensitive": (aud.get("interpretation_sensitive") or "").strip().lower() in ("yes", "true", "1"),
            "reviewer_1": aud.get("r1_reviewer") or None,
            "reviewer_2": aud.get("r2_reviewer") or None,
            "differs_from_ai_consensus_label": differs,
            "note": ("This block is part of the blind two-reviewer human audit (Appendix G). human_final is the audited label; "
                     "it can differ from the AI-consensus 'label' field above -- when it does, the audited label is the one the "
                     "thesis treats as primary from Section 5.14 onward." if lang != "ar" else
                     "هذه الكتلة ضمن التدقيق البشري الأعمى بمراجعَين (الملحق G). human_final هو التصنيف بعد التدقيق، وقد يختلف عن "
                     "حقل «label» أعلاه (تصنيف إجماع الذكاء الاصطناعي)؛ وعند الاختلاف، فإن التصنيف المدقَّق هو المعتمد اعتباراً من القسم 5.14."),
        }
    else:
        b["human_audit"] = {
            "audited": False,
            "note": ("Not part of the 80-block human audit sample; this label is AI-consensus only, not human ground truth." if lang != "ar" else
                     "ليست ضمن عيّنة التدقيق البشري المؤلفة من 80 كتلة؛ هذا التصنيف بإجماع الذكاء الاصطناعي فقط وليس حقيقة ميدانية بشرية."),
        }
    b["caveats"] = _caveats(lang)
    return b


def uncertainty(place, lang="auto"):
    """Deferral assessment for a block or place. A block is flagged `defer_to_human` when its label is uncertain, the two annotators disagreed (adjudicated),
    or a change-type confidence is low. Model-level conformal deferral rates come from conformal_results_AI_consensus.json (design-weighted split conformal)."""
    lang = _lang(lang, place)
    ids, how = resolve(place)
    if not ids:
        return _not_found(place, lang)
    B = load()["blocks"]; conf = load()["conformal"]
    items = []
    for i in ids:
        b = B[i]; why = []
        if b["label"] == "uncertain":
            why.append("label_uncertain")
        if b["label_source"] == "adjudicated":
            why.append("annotators_disagreed_then_adjudicated")
        if b["label"] == "change" and "low" in (b["type_conf_A"], b["type_conf_B"]):
            why.append("low_confidence_change_type")
        items.append({"id": i, "label": b["label"], "label_localised": _lab(b["label"], lang), "annotator_A": b["annotator_A"], "annotator_B": b["annotator_B"],
                      "defer_to_human": bool(why), "reasons": why, "human_check": b["human_check"] or None})
    nd = sum(1 for x in items if x["defer_to_human"])
    model = {}
    for name, d in conf.items():
        if isinstance(d, dict) and "0.1" in d:
            model[name] = {a: {k: d[a][k] for k in ("target_coverage", "deferral_rate", "coverage_change", "coverage_no_change")} for a in ("0.1", "0.2") if a in d}
    msg_en = "%d of %d block(s) should be deferred to a human reviewer." % (nd, len(items))
    msg_ar = "يُوصى بإحالة %d من أصل %d كتلة إلى مراجع بشري." % (nd, len(items))
    return {"found": True, "query": place, "match_type": how, "n_blocks": len(items), "n_deferred": nd, "blocks": items[:50], "message": msg_ar if lang == "ar" else msg_en,
            "model_level_conformal_note": {"source": "conformal_results_AI_consensus.json (n=%s labelled blocks, AI-consensus labels)" % conf.get("labels_source_n", conf.get("n_used")),
                                           "results": model, "meaning": "At a 90% coverage target the conformal classifier defers most blocks (see deferral_rate): the current models are weak, so most automatic decisions would be unreliable."},
            "caveats": _caveats(lang)}


def compare_places(place_a, place_b, lang="auto"):
    """Side-by-side change_summary for two places, with an explicit note when sample sizes are too small to rank them."""
    lang = _lang(lang, place_a + place_b)
    a, b = change_summary(place_a, lang), change_summary(place_b, lang)
    out = {"found": bool(a.get("found") and b.get("found")), "a": a, "b": b, "caveats": _caveats(lang)}
    if out["found"]:
        na, nb = a["n_blocks"], b["n_blocks"]
        small = min(na, nb) < 5
        out["ranking_allowed"] = not small
        out["message"] = (("عدد الكتل %d مقابل %d؛ " % (na, nb)) + ("العيّنة صغيرة جداً للمفاضلة بين المكانين." if small else "يمكن المقارنة بحذر.")) if lang == "ar" else \
            ("Blocks: %d vs %d. " % (na, nb)) + ("Too few blocks to rank the two places." if small else "Compare with caution.")
    else:
        out["message"] = "أحد المكانين غير موجود." if lang == "ar" else "One of the places was not found."
    return out


def area_estimate(aoi="", governorate="", lang="auto", reps=2000, seed=0):
    """Design-weighted (N_h/n_h) estimate of the share of blocks with change in an AOI and/or governorate, excluding uncertain blocks,
    with a stratified bootstrap 95% interval. Ratio estimator; domains with few blocks are flagged unreliable."""
    lang = _lang(lang, aoi + governorate)
    B = load()["blocks"]
    na, err = _canon("aoi", aoi, lang)
    if err:
        return err
    govs, err = _gov(governorate, lang)
    if err:
        return err
    sel = [b for b in B.values() if (not na or b["aoi"] == na) and (govs is None or b["governorate"] in govs)]
    dec = [b for b in sel if b["label"] in ("change", "no_change")]
    if not dec:
        return {"found": False, "message": "No decided blocks in this selection." if lang == "en" else "لا توجد كتل مصنّفة ضمن هذا الاختيار.", "caveats": _caveats(lang)}

    def est(bs):
        w = sum(b["weight"] for b in bs)
        return sum(b["weight"] * (b["label"] == "change") for b in bs) / w if w else float("nan")
    point = est(dec)
    rng = random.Random(seed); strata = {}
    for b in dec:
        strata.setdefault(b["stratum"], []).append(b)
    vals = []
    for _ in range(int(reps)):
        bs = [x for s in strata.values() for x in (rng.choice(s) for _ in s)]
        v = est(bs)
        if v == v:
            vals.append(v)
    vals.sort()
    lo, hi = vals[int(0.025 * len(vals))], vals[int(0.975 * len(vals)) - 1]
    unreliable = len(dec) < 30 or sum(1 for b in dec if b["label"] == "change") < 5
    en = "Design-weighted share of blocks with change: %.1f%% (bootstrap 95%% interval %.1f-%.1f%%), from %d decided blocks (%d uncertain excluded)." % (100 * point, 100 * lo, 100 * hi, len(dec), len(sel) - len(dec))
    ar = "النسبة الموزونة بتصميم العيّنة للكتل التي فيها تغيّر: %.1f%% (فاصل بوتستراب 95%%: %.1f–%.1f%%) من %d كتلة مصنّفة (استُبعدت %d غير مؤكدة)." % (100 * point, 100 * lo, 100 * hi, len(dec), len(sel) - len(dec))
    return {"found": True, "selection": {"aoi": aoi or "all", "governorate": governorate or "all"}, "n_selected": len(sel), "n_decided": len(dec), "n_uncertain_excluded": len(sel) - len(dec),
            "share_change_weighted": round(point, 4), "ci95_bootstrap": [round(lo, 4), round(hi, 4)], "bootstrap": {"reps": int(reps), "seed": seed, "by": "stratum resampling"},
            "unreliable": unreliable, "message": ar if lang == "ar" else en,
            "note": "Uncertain blocks are excluded, so the estimate assumes they change at the same rate as decided ones; labels are AI consensus." if lang == "en" else "استُبعدت الكتل غير المؤكدة؛ التقدير يفترض أنها تتغيّر بالمعدل نفسه، والتصنيفات آلية.",
            "caveats": _caveats(lang)}


def query_blocks(aoi="", governorate="", label="", change_type="", stratum="", place="", label_source="", annotator_a="", annotator_b="", annotators_disagree=None,
                 min_lat=None, max_lat=None, min_lon=None, max_lon=None, group_by="", lang="auto"):
    """Count and list reference blocks matching ALL given filters (aoi: beirut|mount_lebanon, governorate, label: change|no_change|uncertain, change_type, stratum: low|mid|high,
    place: name in Arabic/English, label_source: agreed|adjudicated, annotator_a / annotator_b label, annotators_disagree: true|false, centre-coordinate bounds min/max_lat/lon).
    Returns the unweighted count, the design-weighted share of change among decided blocks in the selection (uncertain excluded; ratio estimator with N_h/n_h weights)
    and, if group_by is one of label|change_type|stratum|aoi|governorate|place_en|label_source, a dict of counts per group. Sampled blocks only, not the population."""
    lang = _lang(lang, " ".join(str(x) for x in (place, governorate, aoi, label, change_type, stratum, label_source, annotator_a, annotator_b) if x))
    B = load()["blocks"]
    cv = {}
    for f, v in (("aoi", aoi), ("label", label), ("change_type", change_type), ("stratum", stratum), ("label_source", label_source),
                 ("annotator_a", annotator_a), ("annotator_b", annotator_b)):
        cv[f], err = _canon(f, v, lang)
        if err:
            return err
    govs, err = _gov(governorate, lang)
    if err:
        return err
    pool = list(B.values())
    if place:
        ids, how = resolve(place)
        if not ids:
            return _not_found(place, lang)
        pool = [B[i] for i in ids]
    def ok(b):
        return ((not cv["aoi"] or b["aoi"] == cv["aoi"]) and (govs is None or b["governorate"] in govs) and (not cv["label"] or b["label"] == cv["label"])
                and (not cv["change_type"] or b["change_type"] == cv["change_type"]) and (not cv["stratum"] or b["stratum"] == cv["stratum"])
                and (not cv["label_source"] or b["label_source"] == cv["label_source"])
                and (not cv["annotator_a"] or b["annotator_A"] == cv["annotator_a"]) and (not cv["annotator_b"] or b["annotator_B"] == cv["annotator_b"])
                and (annotators_disagree is None or (b["annotator_A"] != b["annotator_B"]) == bool(annotators_disagree))
                and (min_lat is None or b["centre_lat"] > float(min_lat)) and (max_lat is None or b["centre_lat"] < float(max_lat))
                and (min_lon is None or b["centre_lon"] > float(min_lon)) and (max_lon is None or b["centre_lon"] < float(max_lon)))
    sel = [b for b in pool if ok(b)]
    n = len(sel)
    dec = [b for b in sel if b["label"] in ("change", "no_change")]
    wsum = sum(b["weight"] for b in dec)
    out = {"found": True, "filters": {k: v for k, v in dict(aoi=aoi, governorate=governorate, label=label, change_type=change_type, stratum=stratum, place=place, label_source=label_source,
           annotator_a=annotator_a, annotator_b=annotator_b, annotators_disagree=annotators_disagree, min_lat=min_lat, max_lat=max_lat, min_lon=min_lon, max_lon=max_lon).items() if v not in ("", None)},
           "filters_canonical": {k: v for k, v in dict(cv, governorate=sorted(govs) if govs else "").items() if v},
           "n_blocks": n, "n_decided": len(dec), "unweighted_share_change_among_decided": round(sum(b["label"] == "change" for b in dec) / len(dec), 4) if dec else None,
           "design_weighted_share_change_among_decided": round(sum(b["weight"] for b in dec if b["label"] == "change") / wsum, 4) if wsum else None,
           "block_ids": [b["id"] for b in sel][:100], "truncated": n > 100,
           "message": ("عدد الكتل المطابقة: %d" % n) if lang == "ar" else "%d matching blocks" % n, "caveats": _caveats(lang)}
    if group_by:
        if group_by not in ("label", "change_type", "stratum", "aoi", "governorate", "place_en", "label_source"):
            return {"found": False, "message": "invalid group_by", "caveats": _caveats(lang)}
        g = {}
        for b in sel:
            g[str(b[group_by])] = g.get(str(b[group_by]), 0) + 1
        out["groups"] = dict(sorted(g.items(), key=lambda x: -x[1]))
    return out


# ---------------------------------------------------------------------------------------------------------------- R27
# Radius query over block centres (the ST_DWithin of this tool layer). A uniform grid index (cells of GRID_DEG degrees)
# narrows the candidates before the exact haversine test; results are identical to a brute-force scan (tested).
GRID_DEG = 0.01


def _haversine_km(lat1, lon1, lat2, lon2):
    import math
    p1, p2 = math.radians(lat1), math.radians(lat2); dp = p2 - p1; dl = math.radians(lon2 - lon1)
    h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * 6371.0088 * math.asin(math.sqrt(h))


def _grid():
    d = load()
    if "grid" not in d:
        g = {}
        for b in d["blocks"].values():
            g.setdefault((int(b["centre_lat"] // GRID_DEG), int(b["centre_lon"] // GRID_DEG)), []).append(b["id"])
        d["grid"] = g
    return d["grid"]


def _near_ids(lat, lon, radius_km, use_index=True):
    import math
    B = load()["blocks"]
    if not use_index:
        cand = list(B)
    else:
        g = _grid(); dlat = radius_km / 111.0; dlon = radius_km / (111.320 * max(math.cos(math.radians(lat)), 1e-6))
        i0, i1 = int((lat - dlat) // GRID_DEG), int((lat + dlat) // GRID_DEG); j0, j1 = int((lon - dlon) // GRID_DEG), int((lon + dlon) // GRID_DEG)
        cand = [i for a in range(i0, i1 + 1) for c in range(j0, j1 + 1) for i in g.get((a, c), [])]
    out = [(round(_haversine_km(lat, lon, B[i]["centre_lat"], B[i]["centre_lon"]), 3), i) for i in cand]
    return sorted((d_, i) for d_, i in out if d_ <= radius_km)


def blocks_near(lat, lon, radius_km=1.0, label="", limit=50, lang="auto"):
    """Reference blocks whose centre lies within radius_km of a point (lat, lon in WGS84 degrees), nearest first, optionally
    filtered by label (English or Arabic). Returns distances, unweighted label counts and the usual caveats; sample only."""
    lang = _lang(lang, str(label))
    try:
        lat, lon, radius_km = float(lat), float(lon), float(radius_km)
    except (TypeError, ValueError):
        return {"found": False, "error": "bad_coordinates", "message": "lat, lon and radius_km must be numbers.", "caveats": _caveats(lang)}
    if not (-90 <= lat <= 90 and -180 <= lon <= 180) or not (0 < radius_km <= 50):
        return {"found": False, "error": "out_of_range", "message": "lat in [-90, 90], lon in [-180, 180], 0 < radius_km <= 50.", "caveats": _caveats(lang)}
    lb, err = _canon("label", label, lang)
    if err:
        return err
    B = load()["blocks"]
    hits = [(d_, i) for d_, i in _near_ids(lat, lon, radius_km) if not lb or B[i]["label"] == lb]
    lab = {"change": 0, "no_change": 0, "uncertain": 0}
    for _, i in hits: lab[B[i]["label"]] += 1
    lim = max(1, min(int(limit), 200))
    rows = [{"id": i, "distance_km": d_, "label": B[i]["label"], "label_localised": _lab(B[i]["label"], lang), "place_en": B[i]["place_en"], "place_ar": B[i]["place_ar"]} for d_, i in hits[:lim]]
    en = "%d sampled block(s) within %.2f km." % (len(hits), radius_km); ar = "عدد الكتل ضمن %.2f كم: %d." % (radius_km, len(hits))
    return {"found": bool(hits), "query": {"lat": lat, "lon": lon, "radius_km": radius_km, "label": lb or None}, "n_blocks": len(hits), "labels": lab,
            "blocks": rows, "truncated": len(hits) > lim, "message": ar if lang == "ar" else en,
            "note": ("No sampled block lies this close; the sample covers two study areas with blocks about 420 m wide, so try a larger radius." if not hits else
                     "Counts are unweighted sample counts, not an estimate for the area around the point."),
            "caveats": _caveats(lang)}


def audit_status(lang="auto"):
    """Report the completed Appendix G blind two-reviewer human audit: how many of the 80 decision-sensitive
    blocks were decided, reviewer agreement, which blocks' final label differs from their AI-consensus label,
    the correlated-error test (Rule 2) result, and the resulting audited re-analysis (headline spectral-vs-random-
    forest AUC comparison and the recalibrated changed-area estimate). Every value is read from the audit's own
    result files (human_audit_results.csv, appendix_g_rules23_R38.json, audited_primary_reanalysis_R38.json);
    nothing here is recomputed or estimated by this tool."""
    lang = _lang(lang, "")
    aud = _load_audit()
    if not aud:
        return {"found": False, "message": "No completed human audit found." if lang == "en" else "لا يوجد تدقيق بشري مكتمل.", "caveats": _caveats(lang)}
    B = load()["blocks"]
    decided = {i: r for i, r in aud.items() if (r.get("human_final") or "").strip()}
    interp_sensitive = sorted(i for i, r in aud.items() if (r.get("interpretation_sensitive") or "").strip().lower() in ("yes", "true", "1"))
    agree_n = sum(1 for r in decided.values() if r["human_1"] == r["human_2"])
    flipped = sorted(i for i, r in decided.items() if i in B and r["human_final"] != B[i]["label"])
    cu = _load_certainty_units()
    cu_flipped = sorted(i for i in cu if i in flipped)
    rules = _load_json("appendix_g_rules23_R38.json")
    reanalysis = _load_json("audited_primary_reanalysis_R38.json")
    auc = reanalysis.get("A_headline_auc", {})
    area = reanalysis.get("B_area_recalibration", {})
    gap_point = auc.get("gap_spec_minus_rf_point")
    gap_ci = (auc.get("audited_auc_bootstrap_95ci") or {}).get("gap_spec_minus_rf")
    gap_point_r = round(gap_point, 3) if isinstance(gap_point, (int, float)) else gap_point
    gap_ci_r = [round(x, 3) for x in gap_ci] if gap_ci else None
    area_corr, area_ci, area_uncorr = area.get("area_corrected_km2"), area.get("area_corrected_95ci"), area.get("area_uncorrected_km2")
    en = ("The Appendix G blind two-reviewer human audit is complete: %d/%d blocks decided (%d left interpretation-sensitive, undecided); "
          "reviewers agreed on %d/%d final labels. %d block(s) overall differ from their AI-consensus label: %s. Of the 13 pre-registered "
          "'certainty units' (Rule 1: 8 pivotal no-change blocks plus 5 Mount Lebanon-low change blocks), %d flipped: %s -- it is this Rule 1 "
          "flip, not the broader 17-block list, that drives the headline finding. The correlated-error test %s (Rule 2). The audited "
          "spectral-vs-random-forest AUC gap is %s, 95%% CI %s -- reported as not supported / audit-sensitive, not a confirmed win for either "
          "model. The audited, per-stratum-corrected changed area is %s km^2 (95%% CI %s), revised down from the uncorrected %s km^2.") % (
        len(decided), len(aud), len(interp_sensitive), agree_n, len(decided), len(flipped), ", ".join(flipped) or "none",
        len(cu_flipped), ", ".join(cu_flipped) or "none",
        "fired" if rules.get("rule2_fires_correlated_error") else "did not fire", gap_point_r, gap_ci_r, area_corr, area_ci, area_uncorr)
    ar = ("التدقيق البشري الأعمى بمراجعَين (الملحق G) مكتمل: اتُّخذ قرار في %d من أصل %d كتلة (بقيت %d كتلة حسّاسة للتأويل بلا قرار)؛ "
          "اتفق المراجعان على %d من %d تصنيف نهائي. اختلف تصنيف %d كتلة إجمالاً عن تصنيفها بإجماع الذكاء الاصطناعي: %s. ومن أصل 13 «وحدة يقين» "
          "محدَّدة مسبقاً (القاعدة 1: 8 كتل محورية بلا تغيّر و5 كتل تغيّر في جبل لبنان-منخفض)، انقلبت %d: %s -- وهذا الانقلاب بحسب القاعدة 1، لا "
          "القائمة الأوسع، هو ما يقود النتيجة الرئيسية. اختبار الخطأ المترابط (القاعدة 2) %s. فجوة AUC المدقَّقة بين النتيجة الطيفية والغابة "
          "العشوائية %s، وفاصل الثقة 95%% لها %s -- وتُعرض كنتيجة غير مؤكدة وحسّاسة للتدقيق، لا كفوز محسوم لأي طرف. تقدير المساحة المتغيّرة بعد "
          "تصحيحها حسب الشريحة هو %s كم² (فاصل ثقة 95%%: %s)، منخفضاً من %s كم² غير المصحح.") % (
        len(decided), len(aud), len(interp_sensitive), agree_n, len(decided), len(flipped), "، ".join(flipped) or "لا يوجد",
        len(cu_flipped), "، ".join(cu_flipped) or "لا يوجد",
        "أُطلق" if rules.get("rule2_fires_correlated_error") else "لم يُطلق", gap_point_r, gap_ci_r, area_corr, area_ci, area_uncorr)
    return {
        "found": True,
        "n_audited": len(aud), "n_decided": len(decided), "n_interpretation_sensitive_undecided": len(interp_sensitive),
        "interpretation_sensitive_blocks": interp_sensitive, "reviewer_agreement_n": agree_n,
        "reviewer_agreement_rate": round(agree_n / len(decided), 4) if decided else None,
        "blocks_where_audited_label_differs_from_ai_consensus": flipped,
        "rule1_certainty_units": {"n_units": len(cu), "block_ids": sorted(cu), "n_flipped": len(cu_flipped), "flipped_block_ids": cu_flipped,
                                   "meaning": ("These 13 blocks were fixed before any review as the pre-registered test of the headline ranking "
                                               "(8 pivotal no-change blocks that must hold, 5 Mount Lebanon-low change blocks). A flip here is what "
                                               "makes the spectral-vs-random-forest ranking 'not supported', separately from the broader "
                                               "'differs from AI-consensus' list above, which includes ordinary audit disagreements outside this set." if lang != "ar" else
                                               "حُدِّدت هذه الكتل الـ13 مسبقاً قبل أي مراجعة كاختبار مُعلَن للمفاضلة الرئيسية (8 كتل محورية بلا تغيّر "
                                               "يجب أن تصمد، و5 كتل تغيّر في جبل لبنان-منخفض). وانقلاب إحداها هو ما يجعل المفاضلة بين النتيجة "
                                               "الطيفية والغابة العشوائية «غير مؤكدة»، بمعزل عن القائمة الأوسع أعلاه التي تشمل خلافات تدقيق عادية "
                                               "خارج هذه المجموعة.")},
        "correlated_error_test": {"fires": rules.get("rule2_fires_correlated_error"), "ai_agreed_error_rate": rules.get("rule2_ai_agreed_error_rate"),
                                   "auditor_error_estimate": rules.get("auditor_error_estimate"), "gap_percentage_points": rules.get("rule2_gap_percentage_points")},
        "audited_headline_auc": {"spectral": (auc.get("audited_auc_point") or {}).get("spec"), "random_forest": (auc.get("audited_auc_point") or {}).get("rf"),
                                  "dinov2": (auc.get("audited_auc_point") or {}).get("dino"), "gap_spectral_minus_rf": gap_point, "gap_95ci": gap_ci,
                                  "conclusion": "not_supported_audit_sensitive"},
        "audited_area_estimate_km2": {"corrected": area_corr, "corrected_95ci": area_ci, "uncorrected": area_uncorr,
                                       "beirut_corrected": area.get("area_beirut_corrected_km2"), "mount_lebanon_corrected": area.get("area_mount_lebanon_corrected_km2")},
        "message": ar if lang == "ar" else en,
        "note": ("This audit covers only the 80-block decision-sensitive subset, not the full 200-block sample." if lang == "en" else
                 "يغطي هذا التدقيق العيّنة الفرعية الحسّاسة للقرار المؤلفة من 80 كتلة فقط، وليس كامل عيّنة الـ200 كتلة."),
        "caveats": _caveats(lang),
    }


TOOLS = {
    "list_places": (list_places, "List named places (Arabic or English) that have reference blocks, with counts of blocks by label. Optional name filter and governorate.",
                    {"query": {"type": "string", "description": "partial place name, Arabic or English (optional)"}, "governorate": {"type": "string"}, "limit": {"type": "integer"}, "lang": {"type": "string", "enum": ["auto", "en", "ar"]}}, []),
    "change_summary": (change_summary, "Summarise the reference-block evidence of change between 2018 and 2025 for a place name (Arabic/English) or a block id. Returns raw counts, change types and caveats; never extrapolates to the whole place.",
                       {"place": {"type": "string"}, "lang": {"type": "string", "enum": ["auto", "en", "ar"]}}, ["place"]),
    "block_evidence": (block_evidence, "Full evidence for one reference block id (E001..E200): location, annotators, adjudication, change type, human check, image sheet.",
                       {"block_id": {"type": "string"}, "lang": {"type": "string", "enum": ["auto", "en", "ar"]}}, ["block_id"]),
    "uncertainty": (uncertainty, "Deferral assessment: which blocks of a place / block id should be deferred to a human reviewer, and why; plus model-level conformal deferral rates.",
                    {"place": {"type": "string"}, "lang": {"type": "string", "enum": ["auto", "en", "ar"]}}, ["place"]),
    "compare_places": (compare_places, "Compare the change evidence of two places side by side; refuses to rank when there are fewer than 5 blocks per place.",
                       {"place_a": {"type": "string"}, "place_b": {"type": "string"}, "lang": {"type": "string", "enum": ["auto", "en", "ar"]}}, ["place_a", "place_b"]),
    "query_blocks": (query_blocks, "Count/list reference blocks matching ALL filters (aoi, governorate, label, change_type, stratum, place, label_source agreed|adjudicated, annotator_a, annotator_b, annotators_disagree, min/max_lat, min/max_lon of block centres); returns count, unweighted and design-weighted change share (uncertain excluded) and optional counts by group_by (label|change_type|stratum|aoi|governorate|place_en|label_source).",
                     {"aoi": {"type": "string"}, "governorate": {"type": "string"}, "label": {"type": "string"}, "change_type": {"type": "string"}, "stratum": {"type": "string"}, "place": {"type": "string"}, "label_source": {"type": "string"}, "annotator_a": {"type": "string"}, "annotator_b": {"type": "string"}, "annotators_disagree": {"type": "boolean"}, "min_lat": {"type": "number"}, "max_lat": {"type": "number"}, "min_lon": {"type": "number"}, "max_lon": {"type": "number"}, "group_by": {"type": "string"}, "lang": {"type": "string", "enum": ["auto", "en", "ar"]}}, []),
    "blocks_near": (blocks_near, "Reference blocks whose centre lies within radius_km (default 1, max 50) of a WGS84 point, nearest first, with distances and label counts; optional label filter (English or Arabic). Sample blocks only.",
                    {"lat": {"type": "number"}, "lon": {"type": "number"}, "radius_km": {"type": "number"}, "label": {"type": "string"}, "limit": {"type": "integer"}, "lang": {"type": "string", "enum": ["auto", "en", "ar"]}}, ["lat", "lon"]),
    "area_estimate": (area_estimate, "Design-weighted share of blocks with change in an AOI (beirut / mount_lebanon) and/or governorate with a stratified-bootstrap 95% interval.",
                      {"aoi": {"type": "string"}, "governorate": {"type": "string"}, "lang": {"type": "string", "enum": ["auto", "en", "ar"]}}, []),
    "audit_status": (audit_status, "Report the completed Appendix G blind two-reviewer human audit: sample size, agreement, which blocks' final label "
                     "differs from the AI-consensus label, the correlated-error test result, and the resulting audited re-analysis (headline AUC "
                     "comparison and the recalibrated changed-area estimate). All values are read from the audit's own result files; nothing is recomputed.",
                     {"lang": {"type": "string", "enum": ["auto", "en", "ar"]}}, []),
}


def call(name, **kw):
    if name not in TOOLS:
        return {"error": "unknown tool %s" % name}
    return TOOLS[name][0](**kw)
