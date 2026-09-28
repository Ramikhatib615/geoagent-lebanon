"""GeoAgent-Lebanon: rule-based bilingual (EN/AR) free-text-to-tool-call parser (R23, 2026-09-25).

Pure standard library, no third-party or project imports. Maps a free-text question to one of the
7 read-only tools in tools.py (list_places, change_summary, block_evidence, uncertainty,
compare_places, area_estimate, query_blocks) plus a best-guess set of arguments. This module does
NOT call any tool and does NOT import tools.py/mcp_server.py -- it only proposes a (tool, args)
pair for a caller (the QGIS panel, or a human) to dispatch. That keeps it zero-risk to the frozen
tool layer, same design principle used for auto_report.py in R17.

Design change from the R22 draft (2026-09-25 cloud-only session): that draft required the caller
to supply a `place_index` and matched place names against it directly. Reading tools.py on the PC
this session (R23) showed that tools.py's own `resolve()` already does bilingual, normalised,
multi-stage place matching (exact -> article-insensitive substring -> admin-area -> substring) with
a difflib-based `_suggest()` fallback when nothing matches. Duplicating that logic client-side would
both be redundant and could drift out of sync with tools.py. So this module now only *segments* a
candidate place span out of the sentence (splits on comparison words, strips known intent/filter
keywords) and hands that raw span to the tool call's place/place_a/place_b argument, trusting
tools.py's resolver to do the actual matching (including returning suggestions on a near-miss).
An optional `place_index` (an iterable of known place names, e.g. built from a live list_places()
call) can still be passed in to improve segmentation of multi-word names that would otherwise be
cut short by a stray keyword; it is used only to prefer the longest known-name match, never to
reject an unknown name outright (a name not in the index is still passed through untouched, since
the sample only covers 96 named places out of many more Lebanese place names a user might type).
"""
import re
import unicodedata

# ---------------------------------------------------------------------------
# Arabic normalisation (mirrors tools.py's norm(), kept independent on purpose
# so this module has zero import dependency on the frozen tool layer)
# ---------------------------------------------------------------------------
# Explicit tashkeel codepoints (064B-0652) + superscript alef (0670) + tatweel (0640). NOT a blanket
# range: a blanket "064B-0670" range accidentally swallows the Arabic-Indic digit block 0660-0669,
# which sits inside it -- found and fixed during this session's own unit testing (a digit-normalisation
# regression that a naive range would silently reintroduce).
_DIAC = re.compile("[ً-ْٰـ]")
_AR_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789")


def normalize_arabic(s):
    """Strip diacritics/tatweel, unify alef/yaa/taa-marbuta forms, map Arabic-Indic digits to ASCII,
    casefold, and collapse whitespace. Mirrors tools.py's norm() for Arabic text specifically."""
    s = unicodedata.normalize("NFKC", s or "").strip()
    s = _DIAC.sub("", s)
    s = re.sub("[أإآٱ]", "ا", s)  # alef forms -> bare alef
    s = s.replace("ى", "ي").replace("ة", "ه")  # alef maqsura->yaa, taa marbuta->haa
    s = s.translate(_AR_DIGITS)
    s = s.casefold()
    s = re.sub(r"\s+", " ", s).strip()
    return s


def _is_ar(s):
    return bool(re.search("[؀-ۿ]", s or ""))


# ---------------------------------------------------------------------------
# Entity extraction
# ---------------------------------------------------------------------------
_BLOCK_ID_RE = re.compile(r"\bE0*([0-9]{1,3})\b", re.IGNORECASE)
_YEAR_RE = re.compile(r"\b(19|20)\d{2}\b")

GOVERNORATES = {
    "beirut governorate": ["beirut governorate", "محافظة بيروت"],
    "mount lebanon governorate": ["mount lebanon governorate", "mount lebanon", "جبل لبنان"],
    "keserwan-jbeil governorate": ["keserwan-jbeil governorate", "keserwan jbeil", "keserwan-jbeil", "kesrouan", "كسروان", "جبيل"],
}
AOI_WORDS = {
    "beirut": "beirut",
    "بيروت": "beirut",
    "mount lebanon": "mount_lebanon",
    "جبل لبنان": "mount_lebanon",
}
CHANGE_TYPES = {
    "new_construction": ["new construction", "new building", "construction", "بناء جديد"],
    "quarry_earthworks": ["quarry", "quarrying", "earthworks", "محاجر", "حفر"],
    "demolition_damage": ["demolition", "demolished", "damage", "هدم", "أضرار"],
    "greenhouse_agri": ["greenhouse", "agri", "farming", "بيوت زراعية", "زراعي"],
    "vegetation_change": ["vegetation", "غطاء نباتي"],
    "other_unclear": ["unclear", "other change", "غير واضح"],
}
LABEL_WORDS = {
    "change": ["changed", "with change", "showing change", "تغير", "تغيّر"],
    "no_change": ["no change", "unchanged", "لا تغير"],
    "uncertain": ["uncertain", "unsure", "غير مؤكد"],
}

_COMPARE_SPLIT_RE = re.compile(
    # space-delimited separators, OR an Arabic waw ("و") attached directly to the next word with no
    # space after it (the ordinary way "X and Y" is written in Arabic, e.g. "حازمية والدورة")
    r"\s+(?:vs\.?|versus|and|with|مقابل)\s+|\s+و(?=\S)", re.IGNORECASE
)


def _extract_block_id(text):
    m = _BLOCK_ID_RE.search(text)
    if not m:
        return None
    return "E%03d" % int(m.group(1))


def _extract_years(text):
    return [int(m.group(0)) for m in _YEAR_RE.finditer(text)]


def _extract_governorate(norm_text):
    for canon, variants in _GOVERNORATES_NORM.items():
        for v in variants:
            if v in norm_text:
                return canon
    return ""


def _extract_aoi(norm_text):
    for word, aoi in _AOI_WORDS_NORM.items():
        if word in norm_text:
            return aoi
    return ""


def _extract_change_type(norm_text):
    for code, variants in _CHANGE_TYPES_NORM.items():
        for v in variants:
            if v in norm_text:
                return code
    return ""


def _extract_label(norm_text):
    for code, variants in _LABEL_WORDS_NORM.items():
        for v in variants:
            if v in norm_text:
                return code
    return ""


def _norm_for_match(text):
    """Lowercase EN + normalise AR in one pass, without destroying word boundaries needed for
    substring keyword checks."""
    if _is_ar(text):
        return normalize_arabic(text)
    return re.sub(r"\s+", " ", text.strip().casefold())


def _normalize_kw_map(mapping):
    """Pre-normalise every keyword in a {key: [variant, ...]} map with _norm_for_match, so lookups
    compare normalised-to-normalised. Needed because raw Arabic keyword literals in source (e.g.
    "نسبة" with a taa marbuta) would otherwise never match normalize_arabic()'s
    output (which rewrites taa marbuta to haa, hamza-alef forms to bare alef, etc) -- a real bug this
    session's own testing caught: every Arabic keyword containing taa marbuta or hamza-alef silently
    never matched until this normalisation was added."""
    return {k: [_norm_for_match(v) for v in vs] for k, vs in mapping.items()}


_GOVERNORATES_NORM = _normalize_kw_map(GOVERNORATES)
_AOI_WORDS_NORM = {_norm_for_match(k): v for k, v in AOI_WORDS.items()}
_CHANGE_TYPES_NORM = _normalize_kw_map(CHANGE_TYPES)
_LABEL_WORDS_NORM = _normalize_kw_map(LABEL_WORDS)


_YEAR_CLAUSE_RE = re.compile(
    r"\bbetween\s+(19|20)\d{2}\s+and\s+(19|20)\d{2}\b|\b(19|20)\d{2}\b|"
    r"بين\s+(19|20)\d{2}\s+و\s*(19|20)\d{2}",
    re.IGNORECASE,
)
_IN_WORD_AR = "في"  # "في"


def _strip_keywords(text, variants):
    """Remove each keyword substring, longest first, so a full conjugated word (e.g. Arabic
    "تغيرت") is matched and removed whole before a shorter prefix of it (e.g. "تغير") can steal a
    partial match and leave word-fragment debris behind."""
    for kw in sorted((v for v in variants if v), key=len, reverse=True):
        text = text.replace(kw, " ")
    return text


def _place_after_last_in(text):
    """Segment the span after the LAST standalone "in"/"في" -- the common phrasing for "<question>
    in <place>". Returns None if no such marker is found, so the caller can fall back to
    keyword-stripping. This is more robust than keyword-stripping for phrasings whose lead-in
    clause ("which blocks need review", "how many X are there") is too open-ended to enumerate."""
    if _is_ar(text):
        idx = text.rfind(" " + _IN_WORD_AR + " ")
        if idx == -1:
            return None
        return text[idx + len(_IN_WORD_AR) + 2:]
    matches = list(re.finditer(r"\bin\b", text, re.IGNORECASE))
    if not matches:
        return None
    return text[matches[-1].end():]


def _best_place_span(candidate, place_index):
    """If place_index is given, prefer the longest known place name that is a substring of
    `candidate` (case/diacritic-insensitive); otherwise return candidate stripped as-is."""
    candidate = candidate.strip(" ?.,!؟،")
    if not candidate:
        return candidate
    if not place_index:
        return candidate
    nc = _norm_for_match(candidate)
    best = None
    for name in place_index:
        nn = _norm_for_match(name)
        if nn and nn in nc:
            if best is None or len(nn) > len(_norm_for_match(best)):
                best = name
    return best or candidate


# ---------------------------------------------------------------------------
# Intent keyword rules (checked in this priority order -- first match wins)
# ---------------------------------------------------------------------------
INTENT_KEYWORDS = {
    "compare_places": [
        "compare", "versus", " vs ", "which changed more", "قارن", "أيهما تغير",
    ],
    "uncertainty": [
        "defer", "review", "uncertain", "needs a human", "needs review", "flagged",
        "مراجعة", "غير مؤكد", "بشري",
    ],
    "area_estimate": [
        "what share", "what percentage", "what fraction", "how much area", "how much of",
        "نسبة", "مساحة",
    ],
    "list_places": [
        "list places", "list the places", "what places", "which places", "show places", "show me places",
        "اذكر الأماكن", "ما هي الأماكن", "قائمة الأماكن",
    ],
    "change_summary": [
        "how has", "how did", "change in", "changed", "did it change", "any change",
        "كيف تغيرت", "كيف تغير", "هل تغيرت", "هل تغير", "التغيير في",
    ],
    "query_blocks": [
        "how many blocks", "count blocks", "list blocks", "blocks with", "blocks in",
        "كم كتلة", "عدد الكتل",
    ],
}


class ParsedQuery:
    def __init__(self, text, intent, tool, args, lang, notes=None):
        self.text = text
        self.intent = intent
        self.tool = tool
        self.args = args
        self.lang = lang
        self.notes = notes or []

    def __repr__(self):
        return "ParsedQuery(intent=%r, tool=%r, args=%r)" % (self.intent, self.tool, self.args)

    def as_dict(self):
        return {"text": self.text, "intent": self.intent, "tool": self.tool, "args": self.args,
                "lang": self.lang, "notes": self.notes}


_INTENT_KEYWORDS_NORM = {intent: [_norm_for_match(kw) for kw in kws] for intent, kws in INTENT_KEYWORDS.items()}


def _classify_intent(norm_text):
    for intent, kws in _INTENT_KEYWORDS_NORM.items():
        for kw in kws:
            if kw and kw in norm_text:
                return intent
    return None


def parse_query(text, place_index=None):
    """Parse a free-text EN/AR question into a proposed tool call. Returns a ParsedQuery whose
    `.tool` is one of the 7 tools.py function names, or None if no intent/entity was recognised.
    Never calls a tool itself. `place_index` is optional (see module docstring)."""
    text = (text or "").strip()
    lang = "ar" if _is_ar(text) else "en"
    notes = []
    norm_text = _norm_for_match(text)

    block_id = _extract_block_id(text)

    # Bare block id with no other recognised intent keyword -> block_evidence, even before the
    # generic intent classifier runs (mirrors the R22 draft's "bare block-ID fallback").
    intent = _classify_intent(norm_text)
    if block_id and (intent is None or intent not in ("compare_places",)):
        if intent is None or "evidence" in norm_text or "block" in norm_text or "كتلة" in norm_text or intent is None:
            if intent is None:
                return ParsedQuery(text, "block_evidence", "block_evidence", {"block_id": block_id, "lang": lang}, lang, notes)

    if intent == "compare_places":
        parts = _COMPARE_SPLIT_RE.split(text)
        # drop the leading "compare"/"قارن بين" keyword fragment from the first part
        if parts:
            parts[0] = re.sub(r"(?i)^(compare|which changed more[:,]?)\s*", "", parts[0]).strip()
            parts[0] = re.sub(r"^قارن\s*(بين)?\s*", "", parts[0]).strip()
        places = [p for p in (s.strip(" ?.,!؟،") for s in parts) if p]
        if len(places) < 2:
            notes.append("compare_places intent matched but fewer than 2 place spans were segmented; underspecified.")
            return ParsedQuery(text, "compare_places", None, {}, lang, notes)
        place_a = _best_place_span(places[0], place_index)
        place_b = _best_place_span(places[1], place_index)
        return ParsedQuery(text, "compare_places", "compare_places", {"place_a": place_a, "place_b": place_b, "lang": lang}, lang, notes)

    if intent == "uncertainty":
        rest = _place_after_last_in(text)
        if rest is None:
            rest = _strip_keywords(text, INTENT_KEYWORDS["uncertainty"])
        place = _best_place_span(rest, place_index)
        args = {"lang": lang}
        if place:
            args["place"] = place
        return ParsedQuery(text, "uncertainty", "uncertainty", args, lang, notes)

    if intent == "area_estimate":
        naoi = _extract_aoi(norm_text)
        ngov = _extract_governorate(norm_text)
        args = {"lang": lang}
        if naoi:
            args["aoi"] = naoi
        if ngov:
            args["governorate"] = ngov
        if not naoi and not ngov:
            notes.append("area_estimate intent matched but no aoi/governorate keyword found; args will be empty (whole-frame estimate).")
        return ParsedQuery(text, "area_estimate", "area_estimate", args, lang, notes)

    if intent == "list_places":
        ngov = _extract_governorate(norm_text)
        rest = text
        for kw in INTENT_KEYWORDS["list_places"]:
            rest = re.sub(re.escape(kw), "", rest, flags=re.IGNORECASE)
        rest = re.sub(r"(?i)\bin\b", "", rest).strip(" ?.,!؟،")
        args = {"lang": lang}
        if ngov:
            args["governorate"] = ngov
        elif rest and not _extract_aoi(norm_text):
            args["query"] = rest
        return ParsedQuery(text, "list_places", "list_places", args, lang, notes)

    if intent == "change_summary":
        rest = _place_after_last_in(text)
        if rest is None:
            rest = _strip_keywords(text, INTENT_KEYWORDS["change_summary"])
            rest = _YEAR_CLAUSE_RE.sub(" ", rest)
            rest = re.sub(r"(?i)\b(has|did|much|any)\b", " ", rest)
        rest = rest.strip(" ?.,!؟،")
        if block_id and not rest.strip():
            return ParsedQuery(text, "change_summary", "change_summary", {"place": block_id, "lang": lang}, lang, notes)
        place = _best_place_span(rest, place_index)
        if not place:
            notes.append("change_summary intent matched but no place span left after stripping keywords.")
            return ParsedQuery(text, "change_summary", None, {}, lang, notes)
        return ParsedQuery(text, "change_summary", "change_summary", {"place": place, "lang": lang}, lang, notes)

    if intent == "query_blocks":
        args = {"lang": lang}
        ngov = _extract_governorate(norm_text)
        naoi = _extract_aoi(norm_text)
        nct = _extract_change_type(norm_text)
        nlab = _extract_label(norm_text)
        if ngov:
            args["governorate"] = ngov
        if naoi:
            args["aoi"] = naoi
        if nct:
            args["change_type"] = nct
        if nlab:
            args["label"] = nlab
        return ParsedQuery(text, "query_blocks", "query_blocks", args, lang, notes)

    if block_id:
        return ParsedQuery(text, "block_evidence", "block_evidence", {"block_id": block_id, "lang": lang}, lang, notes)

    notes.append("no intent keyword matched")
    return ParsedQuery(text, None, None, {}, lang, notes)
