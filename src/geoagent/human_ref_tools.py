"""GeoAgent-Lebanon: READ-ONLY tools over the 300-block independent human-review campaign (data/human_ref/human_ref_300.csv).
Strict separation: the 200 AI-consensus blocks stay in tools.py; nothing here can create, change or delete a label (no write function exists).
Nothing about reviewer identity, dates or blindness is invented: where the project has no record the tools say so.
"""
import csv, os, re, math, random
import tools as _t

import restricted_data as _rd
HR = _rd.path("GEOAGENT_HUMAN_REF", "data", "human_ref", "human_ref_300.csv")
_c = {}
GOV_AR = {"Akkar": "عكار", "Baalbek-Hermel": "بعلبك الهرمل", "Beirut": "بيروت", "Bekaa": "البقاع", "Mount Lebanon": "جبل لبنان", "Nabatiye": "النبطية", "North": "الشمال", "South": "الجنوب"}
LAB_AR = {"change": "تغيّر", "no_change": "لا تغيّر", "unresolved": "غير محسوم"}
CLS_AR = {"two_reviewers_concordant": "اتفق مراجعان بشريان", "adjudicated_by_third_reviewer": "اختلف مراجعان وحسم مراجع ثالث", "unresolved": "غير محسوم في هذا الجدول", "single_rater_resolution": "تصنيف مراجع واحد بعد تعذّر الحسم من مراجعَين"}
SCOPE_EN = ["300 blocks of 420 m (two batches of 100 and 200) drawn for review, not a probability sample of Lebanon.",
            "Labels are visible change between 2018 and 2026 imagery (the later 2025 and 2026 pictures were used to check that a change persists; these are nominal years of the review imagery, and reported capture dates can differ) as judged by human reviewers at moderate agreement (Cohen's kappa 0.59, 0.68, 0.65 overall). They are reference labels, not ground truth, and they do not record damage, cause or building-level change.",
            "Reviewer names are NOT recorded for batch 1; for batch 2 folder names exist but are inferred, and blindness is not documented. 13 blocks the two-reviewer process could not resolve carry ONE later rating each (class single_rater_resolution, no name, date, confidence or blindness record; project records conflict on whether the first 10 were an owner pass or other auditors'), the weakest human class.",
            "Every block was used in earlier post hoc tests; model performance computed here is development evidence, not an untouched test.",
            "OSM building counts are from a 2022-05-22 snapshot of uneven completeness: zero means 'none mapped', not 'none exist'."]
SCOPE_AR = ["300 كتلة بطول 420 م (دفعتان: 100 و200) اختيرت للمراجعة وليست عيّنة احتمالية للبنان.",
            "التصنيفات هي تغيّر مرئي بين صور 2018 و2026 (استُخدمت صور 2025 و2026 اللاحقة للتحقق من استمرار التغيّر)، وهذه سنوات اسمية لصور المراجعة وقد تختلف تواريخ الالتقاط المبلَّغ عنها، كما قدّره مراجعون بشريون باتفاق متوسط (كابا 0.59 و0.68 و0.65 إجمالاً). هي مرجعية وليست حقيقة ميدانية ولا تسجّل الأضرار أو السبب أو التغيّر على مستوى المبنى.",
            "أسماء المراجعين غير مسجّلة للدفعة الأولى؛ وللدفعة الثانية توجد أسماء مجلدات مستنتجة وغير موثّقة، والتعمية غير موثّقة. 13 كتلة تعذّر حسمها من مراجعَين لها تصنيف واحد لاحق (صنف single_rater_resolution) دون اسم أو تاريخ أو درجة ثقة أو سجل تعمية، والسجلات متضاربة حول ما إذا كانت العشر الأولى من المالك أم من مراجعين آخرين؛ وهو أضعف صنف بشري.",
            "استُخدمت كل كتلة في اختبارات لاحقة (post hoc)؛ أداء النماذج هنا دليل تطوير وليس اختباراً غير ملموس.",
            "أعداد مباني OSM من لقطة 2022-05-22 غير مكتملة بشكل متفاوت: الصفر يعني 'لا مبنى مرسوم' وليس 'لا مبنى موجود'."]

def _rows():
    if "r" not in _c:
        with open(HR, encoding="utf-8") as f: rs = list(csv.DictReader(f))
        for r in rs:
            for k in ("score_spectral", "score_dino", "lat", "lon"): r[k] = float(r[k])
            r["osm_building_count_2022"] = int(float(r["osm_building_count_2022"])); r["brow"] = int(r["brow"]); r["bcol"] = int(r["bcol"])
        _c["r"] = rs
    return _c["r"]

def _ar(lang, q=""):
    return _t._lang(lang, q) == "ar"

def _norm_id(b):
    m = re.fullmatch(r"(?i)\s*N?\s*(\d{1,3})\s*[_\-,/ ]\s*(\d{1,3})\s*", str(b))
    return (int(m.group(1)), int(m.group(2))) if m else None

def _find(block_id):
    k = _norm_id(block_id)
    if not k: return None
    for r in _rows():
        if (r["brow"], r["bcol"]) == k: return r
    return None

def _gov(g):
    if not g: return None
    n = _t.norm(g)
    for e, a in GOV_AR.items():
        if n in (_t.norm(e), _t.norm(a), _t.norm(e.replace("-", " "))): return e
    return None

def _err(lang, en, ar): return {"found": False, "error": ar if _ar(lang) else en}
def _nf(block_id, lang): return _err(lang, "no human-reviewed block matches '%s'. Ids look like N162_157 (row_col). This tool covers only the 300 human-reviewed blocks; the 200 AI-consensus blocks are in block_evidence." % block_id,
                                    "لا توجد كتلة مراجَعة بشرياً تطابق '%s'. الصيغة مثل N162_157. تغطي هذه الأداة 300 كتلة مراجَعة بشرياً فقط؛ كتل الإجماع الآلي الـ200 في block_evidence." % block_id)

def _pct(v, key):
    xs = sorted(r[key] for r in _rows()); return sum(1 for x in xs if x <= v) / len(xs)

def _prevalence():
    L = [r for r in _rows() if r["human_label"] in ("change", "no_change")]
    return sum(r["human_label"] == "change" for r in L) / len(L)

def _pred(r, key):
    thr = 1 - _prevalence(); return "change" if _pct(r[key], key) >= thr else "no_change"

def _auc(rows, key):
    pos = [r[key] for r in rows if r["human_label"] == "change"]; neg = [r[key] for r in rows if r["human_label"] == "no_change"]
    if len(pos) < 5 or len(neg) < 5: return None
    s = sum((p > n) + 0.5 * (p == n) for p in pos for n in neg); return s / (len(pos) * len(neg))

def human_block_lookup(block_id, lang="auto"):
    r = _find(block_id)
    if not r: return _nf(block_id, lang)
    ar = _ar(lang, block_id)
    return {"found": True, "evidence_class": "HUMAN reference label (not AI consensus)", "block_id": r["block_id"], "batch": int(r["batch"]),
            "governorate": GOV_AR.get(r["governorate"], r["governorate"]) if ar else r["governorate"], "cadastral_unit": r["cadastral_unit"],
            "lat": r["lat"], "lon": r["lon"], "human_label": LAB_AR[r["human_label"]] if ar else r["human_label"],
            "label_class": CLS_AR[r["label_class"]] if ar else r["label_class"], "reviewer_agreement": r["reviewer_agreement"],
            "score_spectral_raw": r["score_spectral"], "score_dino_raw": r["score_dino"], "caveats": SCOPE_AR if ar else SCOPE_EN}

def human_label_provenance(block_id, lang="auto"):
    r = _find(block_id)
    if not r: return _nf(block_id, lang)
    ar = _ar(lang, block_id)
    names = "batch 1: reviewer names not recorded in the label table" if r["batch"] == "1" else "batch 2: package folder names exist (two auditors and one adjudicator; names withheld) but who rated which block, on which dates, and whether blind is NOT documented"
    if r["label_class"] == "single_rater_resolution": names = "ONE rating from a third-reviewer sheet; no name, date, confidence or blindness record exists; records conflict on authorship (one project record describes an owner third pass for the first 10; another describes auditors other than the owner)"
    en = {"block_id": r["block_id"], "produced_by": "human reviewers (visual interpretation of imagery)", "label_class": r["label_class"], "reviewer_names": names,
          "dates": "not recorded", "blindness": "not documented", "ai_involvement": "not part of this label set; the separate 200-block set is AI consensus",
          "note": r["provenance_note"]}
    if ar:
        if r["label_class"] == "single_rater_resolution": anames = "تصنيف واحد من ورقة مراجع ثالث؛ لا يوجد اسم ولا تاريخ ولا درجة ثقة ولا سجل تعمية؛ والسجلات متضاربة حول المصدر (نص EXT4-B: المالك للعشر الأولى؛ بيان EXT12: مراجعون آخرون)"
        elif r["batch"] == "1": anames = "الدفعة 1: أسماء المراجعين غير مسجّلة في جدول التصنيفات"
        else: anames = "الدفعة 2: توجد أسماء مجلدات الحزمة لكن من صنّف أي كتلة وفي أي تاريخ وهل كان بلا اطلاع غير موثّق"
        en = {"block_id": r["block_id"], "مصدر_التصنيف": "مراجعون بشريون (تفسير بصري للصور)", "الصنف": CLS_AR[r["label_class"]], "اسماء_المراجعين": anames, "التواريخ": "غير مسجّلة", "التعمية": "غير موثّقة", "تدخل_الذكاء_الاصطناعي": "ليس جزءاً من هذه المجموعة؛ مجموعة الـ200 كتلة المنفصلة هي إجماع آلي"}
    return {"found": True, **en, "caveats": SCOPE_AR if ar else SCOPE_EN}

def human_reviewer_agreement(governorate="", lang="auto"):
    ar = _ar(lang, governorate); g = _gov(governorate) if governorate else None
    if governorate and not g: return _err(lang, "unknown governorate '%s'; valid: %s" % (governorate, ", ".join(GOV_AR)), "محافظة غير معروفة '%s'" % governorate)
    rs = [r for r in _rows() if not g or r["governorate"] == g]
    cnt = {}
    for r in rs: cnt[r["label_class"]] = cnt.get(r["label_class"], 0) + 1
    return {"found": True, "scope": g or "all 300 blocks", "n_blocks": len(rs), "by_label_class": cnt,
            "cohen_kappa_reported": {"batch1": 0.59, "batch2": 0.68, "pooled": 0.65, "source": "project report, Section 5.1.2; computed on binary decided pairs, not recomputed per governorate"},
            "caveats": SCOPE_AR if ar else SCOPE_EN}

def human_unresolved(limit=20, lang="auto"):
    """Blocks the two-reviewer process could NOT resolve (13). Each later received ONE rating (single_rater_resolution); listed here so users can treat them with extra care."""
    ar = _ar(lang); rs = [r for r in _rows() if r["label_class"] in ("single_rater_resolution", "unresolved")]
    return {"found": True, "n_originally_unresolved": len(rs), "blocks": [{"block_id": r["block_id"], "governorate": r["governorate"], "batch": int(r["batch"]), "human_label": r["human_label"], "label_class": r["label_class"]} for r in rs[:max(1, min(int(limit), 50))]],
            "note": ("the two reviewers (and the adjudicator) could not decide these; each later has one rating only, with no name, date or blindness record. Treat as the weakest human labels; results using them are shown with and without them (EXT9 vs EXT12)." if not ar else
                     "تعذّر على المراجعَين والمحكّم حسم هذه الكتل؛ لكل منها لاحقاً تصنيف واحد دون اسم أو تاريخ أو سجل تعمية. هي أضعف التصنيفات البشرية، وتُعرض النتائج بها وبدونها (EXT9 مقابل EXT12)."),
            "caveats": SCOPE_AR if ar else SCOPE_EN}

def model_vs_human(block_id, lang="auto"):
    r = _find(block_id)
    if not r: return _nf(block_id, lang)
    ar = _ar(lang, block_id); out = {"found": True, "block_id": r["block_id"], "human_label": r["human_label"], "label_class": r["label_class"]}
    for key, nm in (("score_spectral", "spectral"), ("score_dino", "dinov2_score_A")):
        out[nm] = {"percentile_among_300": round(_pct(r[key], key), 3), "decision_at_prevalence_matched_cutoff": _pred(r, key),
                   "agrees_with_human": (None if r["human_label"] == "unresolved" else _pred(r, key) == r["human_label"])}
    out["interpretation"] = ("The score is a ranking of visible 10 m change; the decision rule here (top share equal to label prevalence, %.2f) is a prespecified display rule, not a tuned classifier. It measures agreement with a reference label, not detection of damage." % _prevalence()) if not ar else "الدرجة ترتيب للتغيّر المرئي بدقة 10 م؛ قاعدة القرار هنا (أعلى نسبة تساوي انتشار التصنيف %.2f) قاعدة عرض محددة مسبقاً وليست مصنّفاً مضبوطاً." % _prevalence()
    out["caveats"] = SCOPE_AR if ar else SCOPE_EN
    return out

def human_regional_performance(governorate="", lang="auto", reps=1000, seed=0, include_single_rater=True):
    ar = _ar(lang, governorate); g = _gov(governorate) if governorate else None
    if governorate and not g: return _err(lang, "unknown governorate '%s'; valid: %s" % (governorate, ", ".join(GOV_AR)), "محافظة غير معروفة '%s'" % governorate)
    rs = [r for r in _rows() if (not g or r["governorate"] == g) and r["human_label"] in ("change", "no_change") and (include_single_rater or r["label_class"] != "single_rater_resolution")]
    npos = sum(r["human_label"] == "change" for r in rs)
    if npos < 5 or len(rs) - npos < 5:
        return {"found": True, "scope": g or "all", "n_labelled": len(rs), "n_change": npos, "auroc": None,
                "statement": "too few labelled blocks of one class (need at least 5 of each) to report a discrimination figure; absence of a figure is not evidence of good or poor performance",
                "caveats": SCOPE_AR if ar else SCOPE_EN}
    rnd = random.Random(seed); res = {}
    for key, nm in (("score_spectral", "spectral"), ("score_dino", "dinov2_score_A")):
        a = _auc(rs, key); bs = []
        for _ in range(min(int(reps), 2000)):
            b = [rs[rnd.randrange(len(rs))] for _ in rs]; v = _auc(b, key)
            if v is not None: bs.append(v)
        bs.sort(); res[nm] = {"auroc": round(a, 3), "ci95_simple_bootstrap": [round(bs[int(0.025 * len(bs))], 3), round(bs[int(0.975 * len(bs)) - 1], 3)] if len(bs) > 20 else None}
    return {"found": True, "scope": g or "all decided blocks", "n_labelled": len(rs), "n_change": npos, "includes_13_single_rater_labels": bool(include_single_rater), **res,
            "statement": ("POST HOC development figure on reused labels; the interval is a simple block bootstrap and understates uncertainty (spatial clustering is ignored here; the project report uses a cluster bootstrap and finds pooled AUROC 0.72 spectral vs 0.67 DINOv2, difference not demonstrated). The human labels are reference labels, not ground truth. Do not read regional differences as established." if not ar else "رقم تطويري (post hoc) على تصنيفات أُعيد استخدامها؛ الفاصل بوتستراب بسيط ويقلّل من عدم اليقين (لا يراعي التجمّع المكاني)؛ تجد الأطروحة بفاصل عنقودي أن AUROC الطيفية 0.72 مقابل 0.67 لـ DINOv2 وأن الفرق غير مثبت. التصنيفات البشرية مرجعية وليست حقيقة ميدانية. لا تعتبر الفروقات الإقليمية مثبتة."),
            "caveats": SCOPE_AR if ar else SCOPE_EN}

def building_footprint_evidence(block_id, lang="auto"):
    r = _find(block_id)
    if not r: return _nf(block_id, lang)
    ar = _ar(lang, block_id); n = r["osm_building_count_2022"]
    st = "mapped buildings present in the 2022 OSM snapshot" if n > 0 else "no building mapped in the 2022 OSM snapshot; this does NOT establish that no building exists (189 of 300 blocks have none, mostly in sparsely mapped regions; verification by dated imagery is pending, see v22 Phase 2)"
    if ar: st = "مبانٍ مرسومة في لقطة OSM لعام 2022" if n > 0 else "لا مبنى مرسوم في لقطة OSM لعام 2022؛ وهذا لا يثبت عدم وجود مبانٍ (189 من 300 كتلة بلا مبانٍ مرسومة، معظمها في مناطق رسمها ضعيف؛ التحقق بصور مؤرّخة قيد الانتظار)"
    return {"found": True, "block_id": r["block_id"], "osm_building_count_2022": n, "status": st, "completeness_verified": False,
            "can_support_building_level_change_claim": False, "reason": ("single 2022 snapshot, no capture dates, no damage attribute; it cannot show that a building existed in 2018 or 2025" if not ar else "لقطة واحدة لعام 2022 بلا تواريخ التقاط ولا سمة ضرر؛ لا تثبت وجود مبنى في 2018 أو 2025"),
            "landcover_2024_south_only": r["landcover_2024_south_only"] or None, "licence": "© OpenStreetMap contributors, ODbL 1.0",
            "caveats": SCOPE_AR if ar else SCOPE_EN}

def damage_claim_check(block_id="", place="", lang="auto"):
    ar = _ar(lang, block_id or place); r = _find(block_id) if block_id else None
    return {"found": True, "can_support_damage_claim": False,
            "reason": ("Human labels record visible change between 2018 and 2026 imagery (the later 2025 and 2026 pictures were used to check that a change persists). They carry no damage attribute, cause, event date or building-level assessment. The list of 35 flagged cadastral units has no recorded source, date or criteria, and the OSM snapshot predates the events."
                       if not ar else "تسجّل التصنيفات البشرية تغيّراً مرئياً بين صور 2018 و2026 (استُخدمت صور 2025 و2026 اللاحقة للتحقق من استمرار التغيّر) دون سمة ضرر أو سبب أو تاريخ حدث أو تقييم على مستوى المبنى. قائمة الوحدات الـ35 بلا مصدر أو تاريخ أو معايير موثّقة، ولقطة OSM أسبق من الأحداث."),
            "block_context": ({"block_id": r["block_id"], "human_label": r["human_label"], "in_flagged_unit_list": r["in_flagged_unit_list"]} if r else None),
            "what_would_be_needed": "dated post-event imagery with a damage protocol, or a sourced damage assessment (e.g. an institutional damage layer) and a building-level reference",
            "caveats": SCOPE_AR if ar else SCOPE_EN}

def human_dataset_scope(lang="auto"):
    ar = _ar(lang); rs = _rows()
    return {"found": True, "n_blocks": len(rs), "by_label": {k: sum(r["human_label"] == k for r in rs) for k in ("change", "no_change", "unresolved")}, "by_label_class": {k: sum(r["label_class"] == k for r in rs) for k in sorted({r["label_class"] for r in rs})},
            "by_governorate": {g: sum(r["governorate"] == g for r in rs) for g in sorted({r["governorate"] for r in rs})},
            "read_only": True, "write_tools": [], "statement": SCOPE_AR if ar else SCOPE_EN}

_LABSYN = {"change": "change", "changed": "change", "تغيّر": "change", "تغير": "change", "no_change": "no_change", "no change": "no_change", "nochange": "no_change", "unchanged": "no_change", "لا تغيّر": "no_change", "لا تغير": "no_change", "بلا تغيّر": "no_change"}
_CLASSES = ("two_reviewers_concordant", "adjudicated_by_third_reviewer", "single_rater_resolution")

def _hav(lat1, lon1, lat2, lon2):
    p = math.pi / 180; a = math.sin((lat2 - lat1) * p / 2) ** 2 + math.cos(lat1 * p) * math.cos(lat2 * p) * math.sin((lon2 - lon1) * p / 2) ** 2
    return 12742 * math.asin(math.sqrt(a))

def _flag(r): return str(r.get("in_flagged_unit_list", "")).strip().lower() in ("true", "1", "yes")
_RANK = {"score_spectral": ("Spectral change score (z-scored difference of the 2018/2025 composites); a high score ranks visible spectral change, not damage, and the top block need not be labelled change by humans.", "درجة التغيّر الطيفية؛ الدرجة العالية ترتّب تغيّراً طيفياً مرئياً وليست ضرراً، وقد لا تكون الكتلة الأعلى موسومة بالتغيّر بشرياً."),
         "score_dino": ("Frozen DINOv2 embedding-distance score; ranks visual change, not damage.", "درجة مسافة تضمين DINOv2 المجمّد؛ ترتّب تغيّراً بصرياً وليس ضرراً."),
         "osm_building_count_2022": ("Count of OSM building footprints in the block from the 2022-05-22 Geofabrik snapshot, as stored in the reference table (counting rule of the reference table: a footprint counts if its centroid lies inside the 420 m block; under the intersect rule used for the 2018 and 2025 snapshots, 185 instead of 189 blocks have none). It is a MAPPED count with uneven completeness (189 of 300 blocks have none); it is not a count of buildings that exist.", "عدد مضلعات مباني OSM في الكتلة من لقطة Geofabrik بتاريخ 2022-05-22 كما هو مخزّن في الجدول المرجعي (قاعدة الجدول المرجعي: يُحتسب المضلع إذا وقع مركزه داخل الكتلة 420 م؛ وبقاعدة التقاطع المستخدمة للقطتي 2018 و2025 تصبح الكتل بلا مضلعات 185 بدل 189). هو عدد مرسوم بتغطية متفاوتة (189 من 300 كتلة بلا مضلعات) وليس عدد المباني الموجودة.")}
def human_query_blocks(governorate="", label="", label_class="", osm_zero=None, group_by="", lang="auto", in_flagged_units=None, rank_by="", top_n=5):
    """Count human-reviewed blocks matching ALL filters. Unweighted counts only (the 300 blocks are not a probability sample)."""
    ar = _ar(lang, governorate + label)
    g = _gov(governorate) if governorate else None
    if governorate and not g: return _err(lang, "unknown governorate '%s'; valid: %s" % (governorate, ", ".join(GOV_AR)), "محافظة غير معروفة '%s'" % governorate)
    lab = None
    if label:
        lab = _LABSYN.get(_t.norm(label)) or _LABSYN.get(str(label).strip().lower())
        if not lab: return _err(lang, "unknown label '%s'; valid: change, no_change" % label, "تصنيف غير معروف '%s'" % label)
    if label_class and label_class not in _CLASSES: return _err(lang, "unknown label_class '%s'; valid: %s" % (label_class, ", ".join(_CLASSES)), "صنف غير معروف '%s'" % label_class)
    rs = [r for r in _rows() if (not g or r["governorate"] == g) and (not lab or r["human_label"] == lab) and (not label_class or r["label_class"] == label_class)
          and (osm_zero is None or (r["osm_building_count_2022"] == 0) == bool(osm_zero))
          and (in_flagged_units is None or _flag(r) == bool(in_flagged_units))]
    out = {"found": True, "n_blocks": len(rs), "filters": {"governorate": g, "label": lab, "label_class": label_class or None, "osm_zero": osm_zero}, "weighting": "unweighted; not a probability sample of Lebanon"}
    if group_by in ("label", "governorate", "label_class", "landcover_2024_south_only"):
        c = {}
        key = {"label": "human_label"}.get(group_by, group_by)
        for r in rs: c[r[key] or "none"] = c.get(r[key] or "none", 0) + 1
        out["by_" + group_by] = c
    elif group_by: return _err(lang, "unknown group_by '%s'; valid: label, governorate, label_class, landcover_2024_south_only" % group_by, "group_by غير معروف")
    if in_flagged_units is not None:
        out["filters"]["in_flagged_units"] = bool(in_flagged_units)
        out["block_ids"] = sorted(r["block_id"] for r in rs)[:100]
        out["flagged_units_note"] = ("in_flagged_units = the block lies in one of the 35 cadastral units on the project's flagged-unit list (stored flag in human_ref_300.csv, from the project's block-to-unit join). The list is a context flag from an external cadastre file; it is NOT verified damage and says nothing about whether any building in the block changed."
                                      if not ar else "in_flagged_units = تقع الكتلة ضمن إحدى الوحدات العقارية الـ35 في قائمة الوحدات المُعلَّمة (علامة مخزّنة في human_ref_300.csv من ربط الكتل بالوحدات). القائمة علامة سياقية من ملف عقاري خارجي وليست ضرراً مثبتاً ولا تدل على تغيّر أي مبنى في الكتلة.")
    if rank_by:
        if rank_by not in _RANK: return _err(lang, "unknown rank_by '%s'; valid: %s" % (rank_by, ", ".join(_RANK)), "rank_by غير معروف")
        try: k = max(1, min(int(top_n), 20))
        except (TypeError, ValueError): return _err(lang, "top_n must be an integer 1-20", "top_n يجب أن يكون عدداً صحيحاً بين 1 و20")
        top = sorted(rs, key=lambda r: (-r[rank_by], r["block_id"]))[:k]   # descending; ties broken by block_id
        out["ranked_by"] = rank_by; out["ranking_scope"] = "within the %d human-reviewed blocks matching the filters (ties by block_id)" % len(rs)
        out["ranked"] = [{"rank": i + 1, "block_id": r["block_id"], rank_by: r[rank_by], "human_label": r["human_label"], "label_class": r["label_class"], "governorate": r["governorate"]} for i, r in enumerate(top)]
        out["rank_note"] = _RANK[rank_by][1 if ar else 0]
    out["caveats"] = SCOPE_AR if ar else SCOPE_EN
    return out

def human_blocks_near(lat, lon, radius_km=5.0, label="", limit=10, lang="auto"):
    ar = _ar(lang, label)
    try: lat = float(lat); lon = float(lon); radius_km = float(radius_km)
    except (TypeError, ValueError): return _err(lang, "lat, lon and radius_km must be numbers", "يجب أن تكون الإحداثيات أرقاماً")
    if not (33.0 <= lat <= 34.8 and 35.0 <= lon <= 36.7): return _err(lang, "coordinates (%s, %s) are outside Lebanon's bounding box (lat 33.0-34.8, lon 35.0-36.7); WGS84 decimal degrees expected, latitude first" % (lat, lon), "الإحداثيات خارج حدود لبنان؛ المطلوب WGS84 بالدرجات العشرية وخط العرض أولاً")
    if not (0 < radius_km <= 50): return _err(lang, "radius_km must be in (0, 50]", "نصف القطر يجب أن يكون بين 0 و50 كم")
    lab = None
    if label:
        lab = _LABSYN.get(_t.norm(label)) or _LABSYN.get(str(label).strip().lower())
        if not lab: return _err(lang, "unknown label '%s'" % label, "تصنيف غير معروف")
    c = sorted(((_hav(lat, lon, r["lat"], r["lon"]), r) for r in _rows() if not lab or r["human_label"] == lab), key=lambda x: x[0])
    c = [(d, r) for d, r in c if d <= radius_km]
    return {"found": True, "n_within_radius": len(c), "radius_km": radius_km, "nearest": [{"block_id": r["block_id"], "distance_km": round(d, 3), "human_label": r["human_label"], "label_class": r["label_class"], "governorate": r["governorate"]} for d, r in c[:max(1, min(int(limit), 50))]],
            "note": "only the 300 human-reviewed blocks are searched; an empty result means no reviewed block nearby, not that nothing changed there",
            "caveats": SCOPE_AR if ar else SCOPE_EN}

_S = {"block_id": {"type": "string", "description": "e.g. N162_157 (row_col) of a human-reviewed block"}, "lang": {"type": "string", "enum": ["auto", "en", "ar"]}}
TOOLS_V22 = {
 "human_block_lookup": (human_block_lookup, "Look up one HUMAN-reviewed block (of 300): human reference label, label class, reviewer agreement, model scores. Read-only. Not AI-consensus.", dict(_S), ["block_id"]),
 "human_label_provenance": (human_label_provenance, "State who/what produced a human label and what is NOT documented (names, dates, blindness). Read-only.", dict(_S), ["block_id"]),
 "human_reviewer_agreement": (human_reviewer_agreement, "Counts by label class (concordant / adjudicated / unresolved) and reported kappa, optionally per governorate.", {"governorate": {"type": "string"}, "lang": _S["lang"]}, []),
 "human_unresolved": (human_unresolved, "List the 13 blocks the two-reviewer process could not resolve and their later single-rater labels, flagged as the weakest human class.", {"limit": {"type": "integer"}, "lang": _S["lang"]}, []),
 "model_vs_human": (model_vs_human, "Compare spectral and DINOv2 score decisions with the human label for one block (percentile and prevalence-matched display rule).", dict(_S), ["block_id"]),
 "human_regional_performance": (human_regional_performance, "AUROC of spectral and DINOv2 scores against human labels, nationwide or per governorate, with post hoc warnings; refuses when a class has fewer than 5 blocks. include_single_rater=false excludes the 13 single-rater labels.", {"governorate": {"type": "string"}, "include_single_rater": {"type": "boolean"}, "lang": _S["lang"]}, []),
 "building_footprint_evidence": (building_footprint_evidence, "OSM 2022 building count for a human-reviewed block with completeness warning; zero is not proof of absence.", dict(_S), ["block_id"]),
 "damage_claim_check": (damage_claim_check, "Checks whether a damage claim can be supported by the project data (it cannot) and says what is needed.", {"block_id": {"type": "string"}, "place": {"type": "string"}, "lang": _S["lang"]}, []),
 "human_query_blocks": (human_query_blocks, "Count human-reviewed blocks by governorate, label (change/no_change), label_class, OSM-zero flag and flagged-cadastral-unit membership, with optional group_by, and optional ranking (rank_by spectral score, DINOv2 score or 2022 OSM building count; top_n). Unweighted; read-only.", {"governorate": {"type": "string"}, "label": {"type": "string"}, "label_class": {"type": "string"}, "osm_zero": {"type": "boolean"}, "group_by": {"type": "string"}, "in_flagged_units": {"type": "boolean", "description": "true/false: block lies / does not lie in one of the 35 flagged cadastral units (context flag, not damage); lists matching block_ids"}, "rank_by": {"type": "string", "enum": ["score_spectral", "score_dino", "osm_building_count_2022"], "description": "return the top_n matching blocks ranked descending by this field"}, "top_n": {"type": "integer", "description": "1-20, default 5"}, "lang": _S["lang"]}, []),
 "human_blocks_near": (human_blocks_near, "Human-reviewed blocks within radius_km of a WGS84 point (validates Lebanon bounds), nearest first, with labels and classes.", {"lat": {"type": "number"}, "lon": {"type": "number"}, "radius_km": {"type": "number"}, "label": {"type": "string"}, "limit": {"type": "integer"}, "lang": _S["lang"]}, ["lat", "lon"]),
 "human_dataset_scope": (human_dataset_scope, "Scope, counts and limitations of the 300-block human reference set; states that no write tool exists.", {"lang": _S["lang"]}, []),
}
for _n, _v in TOOLS_V22.items():
    if _n in _t.TOOLS: raise RuntimeError("tool name clash: " + _n)
    _t.TOOLS[_n] = (_rd.guard(_v[0], "300-block human reference set", "GEOAGENT_HUMAN_REF", "data/human_ref/human_ref_300.csv"),) + tuple(_v[1:])
