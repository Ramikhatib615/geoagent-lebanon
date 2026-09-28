"""R27: execution-feedback (self-correction) loop around the tool layer - transparent by design.

call_with_recovery(name, **kwargs) runs a tool and, if the result is a recoverable failure, re-runs it at most
MAX_STEPS times with an adjusted call:
  * unknown place with suggestions          -> retry with the best suggestion
  * unknown categorical filter value          -> retry with the closest valid value (only if exactly one suggestion)
  * empty radius query (blocks_near)          -> double the radius (up to 50 km)
  * empty coordinate-box query (query_blocks) -> widen the box around its centre by a factor of 2
  * unexpected argument names                 -> drop them
Every adjustment is recorded in result["recovery"] = [{"step", "reason", "changed", "from", "to"}] and the result gets
result["recovered"] = True and a user-facing "recovery_note" (EN/AR). The loop NEVER changes the meaning of a question
silently: the benchmark showed that an agent that quietly substitutes its own spelling for the user's (input
substitution) produces confident wrong answers, so the substitution is always surfaced to the caller.
Pure standard library; does not modify tools.py."""
import os, sys, inspect, difflib
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tools

MAX_STEPS = 3


def _note(steps, lang):
    parts = ["%s: %s -> %s" % (s["changed"], s["from"], s["to"]) for s in steps]
    if lang == "ar":
        return "تنبيه: لم تنجح المحاولة الأولى، فعُدّلت المدخلات تلقائياً (" + "؛ ".join(parts) + "). يجب إبلاغ المستخدم بهذا التعديل."
    return "Note: the first call failed and the input was adjusted automatically (" + "; ".join(parts) + "). Tell the user about this change."


def call_with_recovery(name, **kw):
    if name not in tools.TOOLS:
        return {"error": "unknown tool %s" % name, "recovered": False}
    fn = tools.TOOLS[name][0]; steps = []; kw = dict(kw)
    for step in range(MAX_STEPS + 1):
        try:
            res = fn(**kw)
        except TypeError:
            allowed = set(inspect.signature(fn).parameters); extra = sorted(set(kw) - allowed)
            if not extra or step == MAX_STEPS:
                return {"found": False, "error": "bad_arguments", "recovered": False, "recovery": steps}
            steps.append({"step": step + 1, "reason": "unexpected argument names", "changed": "arguments", "from": extra, "to": "dropped"})
            kw = {k: v for k, v in kw.items() if k in allowed}; continue
        if step == MAX_STEPS or not isinstance(res, dict):
            break
        fix = None
        if res.get("found") is False and res.get("suggestions") and res.get("error") is None:
            key = next((k for k in ("place", "place_a", "place_b") if k in kw and kw[k] == res.get("query")), "place" if "place" in kw else None)
            if key: fix = ("unknown place", key, kw[key], res["suggestions"][0])
        elif res.get("error") == "unknown_filter_value" and len(res.get("suggestions") or []) == 1:
            f = res["filter"]; v = res["suggestions"][0].split(" (")[0]
            if f in kw: fix = ("unknown filter value", f, kw[f], v)
        elif name == "blocks_near" and res.get("found") is False and not res.get("error"):
            r0 = float(kw.get("radius_km", 1.0))
            if r0 < 50: fix = ("no block within the radius", "radius_km", r0, min(50.0, r0 * 2))
        elif name == "query_blocks" and res.get("n_blocks") == 0 and all(kw.get(k) is not None for k in ("min_lat", "max_lat", "min_lon", "max_lon")):
            cl, co = (kw["min_lat"] + kw["max_lat"]) / 2, (kw["min_lon"] + kw["max_lon"]) / 2
            hl, ho = (kw["max_lat"] - kw["min_lat"]), (kw["max_lon"] - kw["min_lon"])
            new = [round(cl - hl, 6), round(cl + hl, 6), round(co - ho, 6), round(co + ho, 6)]
            fix = ("empty coordinate box", "box", [kw["min_lat"], kw["max_lat"], kw["min_lon"], kw["max_lon"]], new)
        if fix is None:
            break
        reason, key, old, new = fix
        steps.append({"step": step + 1, "reason": reason, "changed": key, "from": old, "to": new})
        if key == "box":
            kw.update(min_lat=new[0], max_lat=new[1], min_lon=new[2], max_lon=new[3])
        else:
            kw[key] = new
    if isinstance(res, dict):
        res = dict(res); res["recovered"] = bool(steps) and res.get("found", True) is not False and not res.get("error"); res["recovery"] = steps
        if steps: res["recovery_note"] = _note(steps, tools._lang(kw.get("lang", "auto"), " ".join(str(v) for v in kw.values() if isinstance(v, str))))
    return res


if __name__ == "__main__":
    import json
    for name, kw in (("change_summary", {"place": "Dahye"}), ("query_blocks", {"label": "changd"}), ("blocks_near", {"lat": 33.90, "lon": 35.50, "radius_km": 0.3})):
        r = call_with_recovery(name, **kw); print(name, kw, "->", r.get("recovered"), r.get("recovery"), r.get("n_blocks"))
