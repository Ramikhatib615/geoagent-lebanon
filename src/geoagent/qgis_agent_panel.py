# GeoAgent tools panel for QGIS 3.44. Run inside the QGIS Python console:
#   exec(open(r'C:\Users\ramik\geoagent\src\geoagent\qgis_agent_panel.py', encoding='utf-8').read())
# Docks a panel that calls the SAME 7 read-only tools the language-model agent uses (tools.py), in English or Arabic,
# shows the answer with its caveats, and selects the returned blocks on the map. It contains no language model:
# the free-text box (R40) is a rule-based parser (free_text_query.py) that only proposes which of the same 7
# tools to fill and run -- for a full LLM agent, use Claude Desktop with the "geoagent-lebanon" server instead.
# A live-stats box shows the reference sample's totals and the current map selection, updating as it changes.
# The only edit this panel ever makes is writing
# the reviewer's OWN spot-check value (agree/disagree/unsure) to the rami_check field, on explicit Save, for whatever
# blocks are selected on the map -- it never writes an AI judgement there.
# Labels are AI consensus, not ground truth. Logic lives in panel_logic.py (unit-tested without QGIS).
import sys, json, importlib
from qgis.core import *
from qgis.utils import iface
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtGui import QGuiApplication
from qgis.PyQt.QtWidgets import (QDockWidget, QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QComboBox, QLineEdit, QPushButton,
                                 QTextBrowser, QLabel, QCheckBox, QPlainTextEdit, QTabWidget, QScrollArea, QFrame)
SRC = r'C:\Users\ramik\geoagent\src\geoagent'
if SRC not in sys.path: sys.path.insert(0, SRC)
import tools, panel_logic as PL, free_text_query as FTQ
importlib.reload(tools); importlib.reload(PL); importlib.reload(FTQ)
LAYER = 'Reference blocks (AI consensus, named)'
VERSION = "panel 1.4 \u00b7 tool layer 0.2"
CHOICES = PL.enum_choices(tools.load()["blocks"])
PLACE_INDEX = sorted({n for b in tools.load()["blocks"].values() for n in (b.get("place_en"), b.get("place_ar")) if n})
EXAMPLES = [
    ("Dahieh: change summary (EN)", "change_summary", {"place": "Dahieh", "lang": "en"}),
    ("\u0627\u0644\u0636\u0627\u062d\u064a\u0629 \u0627\u0644\u062c\u0646\u0648\u0628\u064a\u0629: \u0645\u0644\u062e\u0635 \u0627\u0644\u062a\u063a\u064a\u0651\u0631 (AR)", "change_summary", {"place": "\u0627\u0644\u0636\u0627\u062d\u064a\u0629 \u0627\u0644\u062c\u0646\u0648\u0628\u064a\u0629", "lang": "ar"}),
    ("Beirut: design-weighted change share", "area_estimate", {"aoi": "beirut", "lang": "en"}),
    ("Mount Lebanon: design-weighted change share", "area_estimate", {"aoi": "mount_lebanon", "lang": "en"}),
    ("Dahieh vs Hazmieh", "compare_places", {"place_a": "Dahieh", "place_b": "Hazmieh", "lang": "en"}),
    ("Blocks where the two annotators disagreed", "query_blocks", {"annotators_disagree": "true", "group_by": "label", "lang": "en"}),
    ("New-construction blocks", "query_blocks", {"label": "change", "change_type": "new_construction", "lang": "en"}),
    ("Evidence for block E067", "block_evidence", {"block_id": "E067", "lang": "en"}),
    ("Deferral assessment for Dahieh", "uncertainty", {"place": "Dahieh", "lang": "en"}),
    ("Places (first 15)", "list_places", {"limit": "15", "lang": "en"}),
]
STATUS_STYLE = {"ok": "color:#1b5e20", "warn": "color:#b45f06", "err": "color:#b00020", "info": "color:#444"}


def find_layer():
    ls = QgsProject.instance().mapLayersByName(LAYER); return ls[0] if ls else None


def select_ids(ids):
    """Selects blocks by id on the reference layer, zooms to them; returns (message, level)."""
    L = find_layer()
    if L is None: return "Layer '%s' is not loaded (run open_spotcheck.py first)." % LAYER, "err"
    ids = sorted(set(ids))
    if not ids: return "No block ids in this result.", "warn"
    L.selectByExpression("\"id\" IN (" + ",".join("'%s'" % i for i in ids) + ")")
    n = L.selectedFeatureCount()
    if n == 0: return "None of these ids exist in the layer.", "warn"
    iface.mapCanvas().zoomToSelected(L); iface.mapCanvas().refresh()
    cnt = {}
    for f in L.selectedFeatures(): cnt[f["label"]] = cnt.get(f["label"], 0) + 1
    comp = " \u00b7 ".join("%s %d" % (k.replace("_", " "), cnt.get(k, 0)) for k in PL.LABELS)
    return "%d block(s) selected on the map (%s)%s." % (n, comp, "" if n == len(ids) else "; %d id(s) not in layer" % (len(ids) - n)), "ok"


class Panel(QWidget):
    def __init__(self):
        super().__init__(); self.last_ids = []; self.last_res = None; self.fields = {}
        v = QVBoxLayout(self)
        title = QLabel("<b>GeoAgent-Lebanon \u2013 agent tool layer</b> <span style='color:#777'>(%s)</span>" % VERSION); v.addWidget(title)
        note = QLabel("Same read-only tools as the AI agent (EN/AR) \u00b7 labels are AI consensus, not ground truth \u00b7 blocks are a sample")
        note.setStyleSheet("color:#555"); note.setToolTip("The free-text box below and Claude Desktop's 'geoagent-lebanon' server both dispatch the same 7 tools; the box below runs entirely in this panel, no language model involved."); v.addWidget(note)
        stats_box = QFrame(); stats_box.setFrameShape(QFrame.StyledPanel); stats_v = QVBoxLayout(stats_box); stats_v.setContentsMargins(6, 4, 6, 4)
        self.stats_lbl = QLabel(""); self.stats_lbl.setWordWrap(True); self.stats_lbl.setStyleSheet("color:#333"); self.stats_lbl.setTextFormat(Qt.RichText)
        stats_v.addWidget(self.stats_lbl); v.addWidget(stats_box)
        self._stats_layer = None
        h0 = QHBoxLayout()
        self.ftq_in = QLineEdit(); self.ftq_in.setPlaceholderText("Ask in your own words (EN/AR), e.g. 'how has Dahieh changed since 2018?' \u2014 rule-based, no AI model")
        self.ftq_in.returnPressed.connect(self.ask_free_text); h0.addWidget(self.ftq_in, 1)
        ftq_b = QPushButton("Ask"); ftq_b.clicked.connect(self.ask_free_text); h0.addWidget(ftq_b)
        v.addLayout(h0)
        self.ex = QComboBox(); self.ex.addItem("Examples...")
        for e in EXAMPLES: self.ex.addItem(e[0])
        self.ex.currentIndexChanged.connect(self.load_example); v.addWidget(self.ex)
        self.tool = QComboBox(); self.tool.addItems(list(tools.TOOLS)); self.tool.currentTextChanged.connect(self.build_form); v.addWidget(self.tool)
        self.desc = QLabel(""); self.desc.setWordWrap(True); self.desc.setStyleSheet("color:#555"); v.addWidget(self.desc)
        self.form_w = QWidget(); self.form = QFormLayout(self.form_w); self.form.setContentsMargins(0, 0, 6, 0)
        self.scroll = QScrollArea(); self.scroll.setWidgetResizable(True); self.scroll.setFrameShape(QFrame.NoFrame); self.scroll.setWidget(self.form_w); v.addWidget(self.scroll)
        h = QHBoxLayout()
        self.run_b = QPushButton("Run"); self.run_b.setDefault(True); self.run_b.clicked.connect(self.run); h.addWidget(self.run_b)
        self.sel = QCheckBox("select blocks on map"); self.sel.setChecked(True); h.addWidget(self.sel)
        for text, fn in (("Select last result", lambda: self.show_sel(PL.collect_ids(self.last_res, []) if self.last_res else [])), ("Clear selection", self.clear_sel)):
            b = QPushButton(text); b.clicked.connect(fn); h.addWidget(b)
        v.addLayout(h)
        self.status = QLabel(""); self.status.setWordWrap(True); v.addWidget(self.status)
        tabs = QTabWidget(); self.out = QTextBrowser(); self.raw = QPlainTextEdit(); self.raw.setReadOnly(True)
        tabs.addTab(self.out, "Answer"); tabs.addTab(self.raw, "Raw JSON"); v.addWidget(tabs, 1)
        h2 = QHBoxLayout(); self.ids_in = QLineEdit(); self.ids_in.setPlaceholderText("paste block ids from an agent answer, e.g. E067, E178")
        self.ids_in.returnPressed.connect(self.select_pasted)
        b = QPushButton("Select ids"); b.clicked.connect(self.select_pasted); h2.addWidget(self.ids_in); h2.addWidget(b); v.addLayout(h2)
        sc = QFrame(); sc.setFrameShape(QFrame.StyledPanel); scv = QVBoxLayout(sc); scv.setContentsMargins(6, 4, 6, 4)
        scv.addWidget(QLabel("<b>Record your spot-check</b> – writes YOUR OWN value (not an AI judgement) to rami_check for the block(s) selected above"))
        r1 = QHBoxLayout(); self.sc_lbl = QLabel("(nothing selected)"); self.sc_lbl.setWordWrap(True); self.sc_lbl.setStyleSheet("color:#555")
        r1.addWidget(self.sc_lbl, 1)
        b = QPushButton("Refresh"); b.setToolTip("Re-read the current map selection (use after clicking a block by hand)."); b.clicked.connect(self.refresh_spotcheck); r1.addWidget(b)
        scv.addLayout(r1)
        r2 = QHBoxLayout(); self.sc_combo = QComboBox(); self.sc_combo.addItems(["Choose a value...", "agree", "disagree", "unsure", "clear (blank)"])
        r2.addWidget(self.sc_combo, 1)
        b = QPushButton("Save to rami_check"); b.clicked.connect(self.save_spotcheck); r2.addWidget(b)
        scv.addLayout(r2)
        v.addWidget(sc)
        h3 = QHBoxLayout()
        for text, fn in (("Copy block ids", self.copy_ids), ("Copy answer (JSON)", self.copy_json), ("Self-test", self.self_test)):
            b = QPushButton(text); b.clicked.connect(fn); h3.addWidget(b)
        v.addLayout(h3)
        self.build_form(self.tool.currentText()); self.refresh_spotcheck()

    def dataset_stats_text(self):
        """Fixed reference-sample totals (the 200-block sample doesn't change at runtime; shown for context
        next to the live map-selection line below it)."""
        B = tools.load()["blocks"]
        lab = {"change": 0, "no_change": 0, "uncertain": 0}
        for b in B.values():
            lab[b["label"]] += 1
        decided = lab["change"] + lab["no_change"]
        return "Reference sample: <b>%d</b> blocks \u00b7 %d change, %d no change, %d uncertain (%d decided)" % (
            len(B), lab["change"], lab["no_change"], lab["uncertain"], decided)

    def selection_stats_text(self):
        """The genuinely live part: whatever is currently selected on the map, recomputed on every
        selectionChanged signal (a manual map click counts, not just a Run/Select-ids from this panel)."""
        L = find_layer()
        if L is None:
            return "Map selection: layer not loaded."
        feats = list(L.selectedFeatures())
        if not feats:
            return "Map selection: none."
        cnt = {}
        for f in feats:
            cnt[f["label"]] = cnt.get(f["label"], 0) + 1
        comp = " \u00b7 ".join("%s %d" % (k.replace("_", " "), cnt.get(k, 0)) for k in PL.LABELS)
        return "Map selection: <b>%d</b> block(s) \u2014 %s (%.0f%% of sample)" % (len(feats), comp, 100.0 * len(feats) / len(tools.load()["blocks"]))

    def refresh_stats(self, *_args):
        self.stats_lbl.setText(self.dataset_stats_text() + "<br>" + self.selection_stats_text())

    def hook_stats_signal(self):
        """(Re-)connects to the layer's selectionChanged signal so the selection line updates live, including
        for a selection made by clicking directly on the map. Safe to call repeatedly (e.g. after the layer is
        loaded later, or reloaded) -- only reconnects when the layer object has actually changed."""
        L = find_layer()
        if L is not None and L is not self._stats_layer:
            try:
                L.selectionChanged.connect(self.refresh_stats)
            except Exception:
                pass
            self._stats_layer = L
        self.refresh_stats()

    def set_status(self, s, level="info"):
        self.status.setStyleSheet(STATUS_STYLE.get(level, "")); self.status.setText(s)

    def build_form(self, name):
        if name not in tools.TOOLS: return
        while self.form.rowCount(): self.form.removeRow(0)
        self.fields = {}
        fn, desc, params, req = tools.TOOLS[name]
        first = desc.split(". ")[0].rstrip(".") + "."
        self.desc.setText(first if len(first) <= 170 else first[:167] + "..."); self.desc.setToolTip(desc)
        for k, spec in params.items():
            if k in CHOICES:
                w = QComboBox(); w.addItems(CHOICES[k])
                if k == "governorate": w.setEditable(True)
            else:
                w = QLineEdit(); w.returnPressed.connect(self.run)
                if spec.get("description"): w.setPlaceholderText(spec["description"])
            w.setToolTip("%s%s" % (k, " (required)" if k in req else " (optional)"))
            self.fields[k] = w; self.form.addRow(k + (" *" if k in req else ""), w)
        self.scroll.setFixedHeight(min(34 * len(params) + 8, 136))
        self.set_status("Fill the form and press Run. * = required.", "info")

    def raw_values(self):
        return {k: (w.currentText() if isinstance(w, QComboBox) else w.text()) for k, w in self.fields.items()}

    def ask_free_text(self):
        """Rule-based EN/AR free-text parser (free_text_query.py, R23) -> the same form + tools.call()
        path as every other entry point. Never calls a language model and never bypasses the tool layer:
        it only proposes which tool/fields to fill, exactly like picking from the Examples dropdown."""
        text = self.ftq_in.text().strip()
        if not text:
            return
        r = FTQ.parse_query(text, place_index=PLACE_INDEX)
        if not r.tool:
            reason = "; ".join(r.notes) if r.notes else "no intent recognised"
            self.set_status("Couldn't match that to a tool (%s). Try rephrasing, or use the dropdown below." % reason, "warn")
            return
        self.tool.blockSignals(True); self.tool.setCurrentText(r.tool); self.tool.blockSignals(False)
        self.build_form(r.tool)
        for k, val in r.args.items():
            w = self.fields.get(k)
            if w is None:
                continue
            if isinstance(w, QComboBox): w.setCurrentText(str(val))
            else: w.setText(str(val))
        self.run()
        if r.notes:
            self.status.setText("Parsed as %s (%s). %s" % (r.tool, "; ".join(r.notes), self.status.text()))

    def load_example(self, i):
        if i <= 0: return
        _, name, kw = EXAMPLES[i - 1]; self.tool.setCurrentText(name); self.build_form(name)
        for k, val in kw.items():
            w = self.fields[k]
            if isinstance(w, QComboBox): w.setCurrentText(str(val))
            else: w.setText(str(val))
        self.run(); self.ex.blockSignals(True); self.ex.setCurrentIndex(0); self.ex.blockSignals(False)

    def run(self):
        name = self.tool.currentText(); fn, desc, params, req = tools.TOOLS[name]
        kw, errs = PL.parse_values(params, req, self.raw_values())
        if errs:
            self.set_status(" ".join(errs), "err"); return
        try: res = tools.call(name, **kw)
        except Exception as e: res = {"error": "%s: %s" % (type(e).__name__, e)}
        self.last_res = res
        self.raw.setPlainText(json.dumps(res, ensure_ascii=False, indent=1))
        self.last_ids = PL.collect_ids(res, [])
        self.out.setHtml(PL.render_answer(res, self.last_ids))
        hint = PL.zero_hint(name, res)
        if isinstance(res, dict) and (res.get("error") or res.get("found") is False):
            self.set_status(res.get("error") or res.get("message") or "not found", "warn")
        elif hint: self.set_status(hint, "warn")
        elif self.sel.isChecked() and self.last_ids: self.show_sel(self.last_ids)
        else: self.set_status("done" + ("" if self.last_ids else " (no block ids in this result)"), "ok")

    def show_sel(self, ids):
        msg, lvl = select_ids(ids); self.set_status(msg, lvl); self.refresh_spotcheck()

    def clear_sel(self):
        L = find_layer()
        if L is not None: L.removeSelection(); iface.mapCanvas().refresh()
        self.set_status("Selection cleared.", "info"); self.refresh_spotcheck()

    def select_pasted(self):
        self.show_sel(PL.ID_RE.findall(self.ids_in.text().upper()))

    def copy_ids(self):
        QGuiApplication.clipboard().setText(", ".join(self.last_ids)); self.set_status("%d block id(s) copied." % len(self.last_ids), "ok")

    def copy_json(self):
        QGuiApplication.clipboard().setText(self.raw.toPlainText()); self.set_status("Answer copied as JSON.", "ok")

    def refresh_spotcheck(self):
        self.hook_stats_signal()
        L = find_layer()
        if L is None: self.sc_lbl.setText("(layer not loaded)"); return
        feats = list(L.selectedFeatures())
        if not feats: self.sc_lbl.setText("(nothing selected on the map)"); return
        rows = ["%s: currently %s" % (f["id"], f["rami_check"] or "not checked") for f in feats]
        self.sc_lbl.setText(", ".join(rows[:10]) + (" … (+%d more)" % (len(rows) - 10) if len(rows) > 10 else ""))

    def save_spotcheck(self):
        L = find_layer()
        if L is None: self.set_status("Layer '%s' is not loaded." % LAYER, "err"); return
        fids = L.selectedFeatureIds()
        if not fids: self.set_status("Select one or more blocks on the map first (Run a tool, Select ids, or click a block).", "warn"); return
        idx = L.fields().indexFromName("rami_check")
        if idx < 0: self.set_status("Field 'rami_check' was not found on this layer.", "err"); return
        choice = self.sc_combo.currentText()
        if choice.startswith("Choose"): self.set_status("Pick a value first (or 'clear (blank)' to remove an existing one).", "warn"); return
        val = "" if choice.startswith("clear") else choice
        ids_before = [f["id"] for f in L.selectedFeatures()]
        started = not L.isEditable()
        if started and not L.startEditing(): self.set_status("Could not start editing the layer (read-only, or open elsewhere?).", "err"); return
        ok = all(L.changeAttributeValue(fid, idx, val) for fid in fids)
        if started:
            if ok and L.commitChanges():
                if ids_before: L.selectByExpression("\"id\" IN (" + ",".join("'%s'" % i for i in ids_before) + ")")
                self.set_status("Saved rami_check = %s for %d block(s) and wrote it to disk." % (val or "(blank)", len(fids)), "ok")
            else:
                L.rollBack(); self.set_status("Could not save: %s" % ("; ".join(L.commitErrors()) or "unknown error"), "err")
        else:
            self.set_status("Set rami_check = %s for %d block(s) in the open edit session (not yet saved – use the layer's Save icon or the attribute table)." % (val or "(blank)", len(fids)) if ok else "Could not set the value on one or more features.", "ok" if ok else "err")
        self.refresh_spotcheck()

    def self_test(self):
        ok, n, fails = PL.self_test(tools)
        L = find_layer()
        layer_ok = L is not None and L.featureCount() == 200
        if not layer_ok: fails.append("map layer '%s' missing or not 200 features" % LAYER)
        if fails: self.set_status("Self-test: %d/%d tool checks passed. Problems: %s" % (ok, n, " | ".join(fails)), "err")
        else: self.set_status("Self-test passed: %d/%d tool checks (EN and AR), map layer present (200 blocks)." % (ok, n), "ok")


for d in iface.mainWindow().findChildren(QDockWidget, 'geoagent_dock'): iface.removeDockWidget(d); d.deleteLater()
dock = QDockWidget("GeoAgent tools (AI agent layer)", iface.mainWindow()); dock.setObjectName('geoagent_dock'); dock.setWidget(Panel()); dock.setMinimumWidth(420)
iface.addDockWidget(Qt.RightDockWidgetArea, dock); dock.show()
try:
    scr = iface.mainWindow().screen().availableGeometry(); g = iface.mainWindow().geometry()
    dock.setFloating(True); dock.resize(640, max(420, min(720, scr.height() - 60)))
    dock.move(min(g.right() - 660, scr.right() - 660), scr.top() + 8)
except Exception:
    pass
print('GEOAGENT PANEL READY')
