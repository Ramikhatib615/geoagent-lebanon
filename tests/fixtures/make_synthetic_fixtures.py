"""Writes two SYNTHETIC fixture tables for the test suite. They have the column layout of the restricted
files (data/human_ref/human_ref_300.csv and data/osm_hist/block_osm_features_300.csv) but every value is
generated from a fixed seed. No row describes a real block, label, score or reviewer decision.
Usage: python tests/fixtures/make_synthetic_fixtures.py
"""
import csv
import os
import random

HERE = os.path.dirname(os.path.abspath(__file__))
GOV = ["Akkar", "Baalbek-Hermel", "Beirut", "Bekaa", "Mount Lebanon", "Nabatiye", "North", "South"]
CLS = [("two_reviewers_concordant", "agreed"), ("adjudicated_by_third_reviewer", "disagreed_then_adjudicated"),
       ("single_rater_resolution", "not_applicable_one_rating_after_two_reviewers_could_not_resolve")]
NOTE = "SYNTHETIC TEST FIXTURE - not a real block, label or score"
OSM_NOTE = "SYNTHETIC TEST FIXTURE - not an OpenStreetMap count"
HUMAN_COLS = ["block_id", "batch", "brow", "bcol", "test_id", "score_spectral", "score_dino", "label_class", "human_label",
              "reviewer_agreement", "provenance_note", "lat", "lon", "governorate", "cadastral_unit", "osm_building_count_2022",
              "landcover_2024_south_only", "in_flagged_unit_list", "osm_note"]
OSM_NUM = ["2018_n", "2018_n_cent", "2018_area", "2018_sumarea_naive", "2018_cat_D_disappearing", "2018_cat_A_unchanged",
           "2018_edge_cross", "2018_cat_B_modified_geometry", "2018_cat_E_remapped_split_merged", "2018_nb3km", "2025_n",
           "2025_n_cent", "2025_area", "2025_sumarea_naive", "2025_cat_C_appearing", "2025_edge_cross", "2025_cat_A_unchanged",
           "2025_cat_B_modified_geometry", "2025_cat_E_remapped_split_merged", "2025_nb3km", "cover_pct_2018", "cover_pct_2025",
           "any18", "any25", "any22"]


def main(n=96, seed=20261111):
    rng = random.Random(seed)
    human, osm = [], []
    for i in range(n):
        brow, bcol = 900 + i // 12, 900 + i % 12            # outside the real grid, so no id can match a real block
        gov = GOV[i % len(GOV)]
        label = "change" if rng.random() < 0.5 else "no_change"
        cls, agr = CLS[0] if rng.random() < 0.75 else CLS[1 + (rng.random() < 0.3)]
        spec = round(rng.gauss(1.3 if label == "change" else 0.9, 0.5), 4)
        dino = round(min(0.6, max(0.01, rng.gauss(0.17 if label == "change" else 0.14, 0.05))), 4)
        n22 = rng.choice([0, 0, 0, 2, 7, 25, 90])
        row = {"block_id": "N%03d_%03d" % (brow, bcol), "batch": 1 + (i >= n // 3), "brow": brow, "bcol": bcol, "test_id": "S%03d" % i,
               "score_spectral": spec, "score_dino": dino, "label_class": cls, "human_label": label, "reviewer_agreement": agr,
               "provenance_note": NOTE, "lat": round(rng.uniform(33.1, 34.6), 6), "lon": round(rng.uniform(35.2, 36.5), 6),
               "governorate": gov, "cadastral_unit": "Synthetic unit %d" % (i % 20), "osm_building_count_2022": n22,
               "landcover_2024_south_only": "", "in_flagged_unit_list": str(i % 9 == 0), "osm_note": OSM_NOTE}
        human.append(row)
        n18 = rng.choice([0, 0, 1, 4, 12]); n25 = n18 + rng.choice([0, 0, 3, 10])
        o = {k: row[k] for k in ("block_id", "batch", "brow", "bcol", "test_id", "score_spectral", "score_dino", "label_class", "human_label",
                                 "reviewer_agreement", "lat", "lon", "governorate", "cadastral_unit", "osm_building_count_2022")}
        o.update({k: 0 for k in OSM_NUM})
        o.update({"2018_n": n18, "2025_n": n25, "2025_cat_A_unchanged": n18, "2025_cat_C_appearing": n25 - n18, "2018_cat_A_unchanged": n18,
                  "2018_nb3km": n18 * 9, "2025_nb3km": n25 * 9, "cover_pct_2018": round(n18 * 0.08, 2), "cover_pct_2025": round(n25 * 0.08, 2),
                  "any18": int(n18 > 0), "any25": int(n25 > 0), "any22": int(n22 > 0)})
        osm.append(o)
    for name, rows, cols in (("human_ref_synthetic.csv", human, HUMAN_COLS), ("block_osm_features_synthetic.csv", osm, list(osm[0]))):
        with open(os.path.join(HERE, name), "w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=cols); w.writeheader(); w.writerows(rows)
    print("wrote", n, "synthetic rows to each fixture")


if __name__ == "__main__":
    main()
