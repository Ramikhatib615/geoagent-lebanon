"""GeoAgent-Lebanon: READ-ONLY tools over historical OSM (2018-09-15, 2025-09-15) joined to the 300 human-reviewed blocks.
Rule enforced everywhere: OSM MAPPING change is not PHYSICAL building change. No write function exists. Nothing here verifies buildings physically."""
import csv, os, re
HERE=os.path.dirname(os.path.abspath(__file__)); F=os.environ.get("GEOAGENT_OSM_HIST") or os.path.join(HERE,"..","..","data","osm_hist","block_osm_features_300.csv"); _c={}
CAVEAT_EN=("OSM snapshots record what was MAPPED on 2018-09-15 and 2025-09-15, not what physically existed. A new footprint can be new construction, "
 "an older building mapped for the first time, a remap with a new ID, an import or a mapping campaign; a vanished footprint is not proof of demolition. Zero mapped footprints is not proof of a building-free area. "
 "Physical change needs dated imagery and human review (none exists for these snapshots). Source: (c) OpenStreetMap contributors, ODbL.")
CAVEAT_AR=("لقطات OSM تسجّل ما كان مرسوماً في 15-09-2018 و15-09-2025 وليس ما كان موجوداً فعلاً. قد يكون المضلّع الجديد بناءً جديداً أو مبنى قديماً رُسم لأول مرة أو إعادة رسم بمعرّف جديد أو استيراداً أو حملة رسم؛ واختفاء مضلّع لا يثبت الهدم. "
 "غياب المضلّعات لا يثبت خلوّ المنطقة من المباني. تأكيد التغيّر الفعلي يحتاج صوراً مؤرّخة ومراجعة بشرية (غير متوفرة لهذه اللقطات). المصدر: © مساهمو OpenStreetMap، رخصة ODbL.")
GOV_AR={"Akkar":"عكار","Baalbek-Hermel":"بعلبك الهرمل","Beirut":"بيروت","Bekaa":"البقاع","Mount Lebanon":"جبل لبنان","Nabatiye":"النبطية","North":"الشمال","South":"الجنوب"}
def _rows():
    if "r" not in _c:
        with open(F,encoding="utf-8") as f: rs=list(csv.DictReader(f))
        for r in rs:
            for k in r:
                try: r[k]=float(r[k]) if k not in("block_id","governorate","human_label","label_class","cadastral_unit","lc_group","test_id","region","landcover_2024_south_only","reviewer_agreement") else r[k]
                except ValueError: pass
        _c["r"]=rs
    return _c["r"]
def _ar(q): return bool(re.search(r"[؀-ۿ]",str(q)))
def _find(b):
    m=re.fullmatch(r"(?i)\s*N?\s*(\d{1,3})\s*[_\-,/ ]\s*(\d{1,3})\s*",str(b))
    if not m: return None
    k=(int(m.group(1)),int(m.group(2)))
    return next((r for r in _rows() if (int(r["brow"]),int(r["bcol"]))==k),None)
def _gov(g):
    if not g: return None
    g=str(g).strip().lower()
    for e,a in GOV_AR.items():
        if g in (e.lower(),a,e.lower().replace("-"," ")): return e
    return None
def _cav(lang): return CAVEAT_AR if lang=="ar" else CAVEAT_EN
def _lang(lang,q): return lang if lang in("ar","en") else ("ar" if _ar(q) else "en")
def osm_block_history(block_id, lang="auto"):
    r=_find(block_id); l=_lang(lang,block_id)
    if not r: return {"found":False,"error":("لا توجد كتلة مطابقة. الصيغة مثل N162_157. تغطي الأداة 300 كتلة مراجَعة بشرياً." if l=="ar" else "No matching block. Ids look like N162_157. This tool covers the 300 human-reviewed blocks only.")}
    g=lambda k:int(r.get(k,0) or 0)
    return {"found":True,"block_id":r["block_id"],"evidence_class":"HISTORICAL OSM MAPPING (not physical buildings)",
     "mapped_footprints":{"2018":g("2018_n"),"2022":int(r["osm_building_count_2022"]),"2025":g("2025_n")},
     "mapped_footprint_area_pct_of_block":{"2018":round(r["cover_pct_2018"],2),"2025":round(r["cover_pct_2025"],2)},
     "mapping_transitions_2025_objects":{"persistent_same_id":g("2025_cat_A_unchanged")+g("2025_cat_B_modified_geometry"),"modified_geometry_same_id":g("2025_cat_B_modified_geometry"),"newly_mapped_no_overlap_with_2018":g("2025_cat_C_appearing"),"remapped_split_or_merged":g("2025_cat_E_remapped_split_merged"),"ambiguous":g("2025_cat_F_ambiguous")},
     "no_longer_mapped_2018_objects":g("2018_cat_D_disappearing"),
     "neighbourhood_3km_square_mapped_2018_2025":[g("2018_nb3km"),g("2025_nb3km")],
     "human_label":r["human_label"],"label_class":r["label_class"],
     "interpretation":("خريطة مرسومة فقط: " if l=="ar" else "Mapping only: ")+("زيادة في المضلّعات المرسومة لا تُثبت بناءً جديداً." if l=="ar" else "an increase in mapped footprints does not prove new construction."),
     "caveat":_cav(l)}
def osm_mapping_vs_physical(lang="en"):
    return {"answer":("لا. " if lang=="ar" else "No. ")+_cav(lang),"caveat":_cav(lang)}
def osm_building_free_status(block_id, lang="auto"):
    r=_find(block_id); l=_lang(lang,block_id)
    if not r: return osm_block_history(block_id,l)
    z=[int(r["2018_n"]),int(r["osm_building_count_2022"]),int(r["2025_n"])]
    if sum(z)==0:
        msg=("لا مضلّعات مرسومة في 2018 و2022 و2025، لكن هذا لا يثبت خلو الكتلة من المباني؛ التحقق التصويري البشري ما زال معلّقاً." if l=="ar" else "No footprints were mapped in 2018, 2022 or 2025, but this does NOT verify the block as building-free; human imagery review is still pending.")
    else:
        msg=("توجد مضلّعات مرسومة في إحدى اللقطات؛ الكتلة ليست خالية من المباني حسب OSM." if l=="ar" else "Footprints are mapped in at least one snapshot; the block is not building-free according to OSM.")
    return {"found":True,"block_id":r["block_id"],"verified_building_free":False,"mapped_2018_2022_2025":z,"statement":msg,"caveat":_cav(l)}
def osm_vs_scores(kind, lang="en", n=10):
    """kind: 'osm_increase_low_spectral' | 'high_spectral_no_osm_change'. Spectral threshold = median / top-third of the 300 blocks."""
    R=_rows(); sp=sorted(r["score_spectral"] for r in R); med=sp[len(sp)//2]; hi=sp[2*len(sp)//3]
    if kind=="osm_increase_low_spectral": S=[r for r in R if r["2025_n"]>r["2018_n"] and r["score_spectral"]<med]
    elif kind=="high_spectral_no_osm_change": S=[r for r in R if r["score_spectral"]>=hi and r["2025_n"]==r["2018_n"]]
    else: return {"found":False,"error":"unknown kind"}
    S=sorted(S,key=lambda r:-r["score_spectral"])
    return {"found":True,"kind":kind,"spectral_median":round(med,4),"spectral_top_third_cut":round(hi,4),"n_blocks":len(S),"example_blocks":[r["block_id"] for r in S[:n]],"caveat":_cav(_lang(lang,""))}
def osm_region_coverage(lang="en"):
    R=_rows(); out={}
    for r in R:
        o=out.setdefault(r["governorate"],{"blocks":0,"with_footprint_2018":0,"with_footprint_2025":0})
        o["blocks"]+=1; o["with_footprint_2018"]+=r["2018_n"]>0; o["with_footprint_2025"]+=r["2025_n"]>0
    for k,o in out.items(): o["share_blocks_mapped_2025"]=round(o["with_footprint_2025"]/o["blocks"],3)
    w=sorted(out,key=lambda k:out[k]["share_blocks_mapped_2025"])
    return {"found":True,"basis":"share of the 300 reviewed blocks (not a probability sample) with >=1 footprint","weakest_first":w,"regions":out,"caveat":_cav(lang)}
def osm_contradictions(lang="en",n=10):
    R=_rows(); A=[r["block_id"] for r in R if r["2025_n"]>r["2018_n"] and r["human_label"]=="no_change"]
    B=[r["block_id"] for r in R if r["2025_n"]==0 and r["human_label"]=="change"]
    return {"found":True,"mapping_increase_but_human_no_change":{"n":len(A),"examples":A[:n]},"no_footprint_2025_but_human_change":{"n":len(B),"examples":B[:n]},
     "note":("الصنف الثاني متوقع لأن التصنيف البشري يخص تغيّر سطح الأرض وليس المباني." if lang=="ar" else "The second class is expected: the human label is visible land-surface change, not building change."),"caveat":_cav(lang)}
def osm_physical_verification(block_id=None, lang="en"):
    return {"found":False,"status":"PENDING","statement":("لا يوجد تحقق مستقل من تغيّر المباني الفعلي؛ حزمة المراجعة جاهزة والمراجعة البشرية معلّقة." if lang=="ar" else "No independent physical building verification exists; the review package is prepared and human review is pending."),
     "needed":["dated high-resolution imagery for 2018 and 2025 with legal permission","two independent reviewers + adjudication","a sample drawn independently of these blocks"]}
TOOLS={"osm_block_history":osm_block_history,"osm_mapping_vs_physical":osm_mapping_vs_physical,"osm_building_free_status":osm_building_free_status,"osm_vs_scores":osm_vs_scores,"osm_region_coverage":osm_region_coverage,"osm_contradictions":osm_contradictions,"osm_physical_verification":osm_physical_verification}
