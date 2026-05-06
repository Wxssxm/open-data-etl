"""Generate a small synthetic DVF-flavoured CSV for the sample/ folder.

The real DVF dataset is published yearly on data.gouv.fr at
https://files.data.gouv.fr/geo-dvf/latest/csv/  with millions of rows per year.
This sample mirrors the schema (column names + dtypes) for a few hundred rows
so tests + CI run offline.

Reproducible with SEED.
"""

from __future__ import annotations

import csv
import random
from datetime import date, timedelta
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
OUT = REPO_ROOT / "data" / "sample" / "dvf_sample.csv"
SEED = 42
N_ROWS = 800

NATURE_MUTATION = ["Vente", "Vente en l'état futur d'achèvement", "Echange", "Adjudication"]
NATURE_WEIGHTS = [82, 12, 3, 3]

TYPE_LOCAL = ["Maison", "Appartement", "Local industriel. commercial ou assimilé", "Dépendance"]
TYPE_LOCAL_WEIGHTS = [40, 50, 5, 5]

# A handful of real (commune, postal_code, departement, region) tuples for realism.
# (commune_name, postal_code, departement_code, region, INSEE-style code_commune)
COMMUNES = [
    ("Paris 1er Arrondissement", "75001", "75", "Île-de-France", "75101"),
    ("Paris 11e Arrondissement", "75011", "75", "Île-de-France", "75111"),
    ("Paris 18e Arrondissement", "75018", "75", "Île-de-France", "75118"),
    ("Lyon 2e Arrondissement", "69002", "69", "Auvergne-Rhône-Alpes", "69382"),
    ("Lyon 6e Arrondissement", "69006", "69", "Auvergne-Rhône-Alpes", "69386"),
    ("Marseille 7e Arrondissement", "13007", "13", "Provence-Alpes-Côte d'Azur", "13207"),
    ("Marseille 11e Arrondissement", "13011", "13", "Provence-Alpes-Côte d'Azur", "13211"),
    ("Bordeaux", "33000", "33", "Nouvelle-Aquitaine", "33063"),
    ("Toulouse", "31000", "31", "Occitanie", "31555"),
    ("Nice", "06000", "06", "Provence-Alpes-Côte d'Azur", "06088"),
    ("Nantes", "44000", "44", "Pays de la Loire", "44109"),
    ("Lille", "59000", "59", "Hauts-de-France", "59350"),
    ("Rennes", "35000", "35", "Bretagne", "35238"),
    ("Strasbourg", "67000", "67", "Grand Est", "67482"),
]


def main() -> None:
    rng = random.Random(SEED)
    OUT.parent.mkdir(parents=True, exist_ok=True)

    base = date(2023, 1, 1)
    rows = []
    for i in range(1, N_ROWS + 1):
        commune, code_postal, code_dept, _region, code_commune = rng.choice(COMMUNES)
        nature = rng.choices(NATURE_MUTATION, weights=NATURE_WEIGHTS, k=1)[0]
        type_local = rng.choices(TYPE_LOCAL, weights=TYPE_LOCAL_WEIGHTS, k=1)[0]
        d = base + timedelta(days=rng.randint(0, 364))

        # Realistic-ish surface and price distributions
        if type_local == "Maison":
            surface = rng.randint(70, 220)
            base_per_m2 = rng.choice([2200, 3500, 4500, 6500])
        elif type_local == "Appartement":
            surface = rng.randint(20, 120)
            base_per_m2 = rng.choice([4000, 6000, 8500, 12000])
        else:
            surface = rng.randint(30, 400)
            base_per_m2 = rng.choice([2000, 3000, 5000])

        price_per_m2 = max(500, int(rng.gauss(base_per_m2, base_per_m2 * 0.18)))
        valeur_fonciere = surface * price_per_m2

        # Inject some bad rows: 1% with valeur_fonciere = 0, 0.5% with NULL surface
        if rng.random() < 0.01:
            valeur_fonciere = 0
        if rng.random() < 0.005:
            surface = None  # type: ignore[assignment]

        nb_pieces = (
            rng.choice([1, 2, 3, 4, 5, 6]) if type_local in ("Maison", "Appartement") else None
        )

        rows.append(
            {
                "id_mutation": f"2023-{i:06d}",
                "date_mutation": d.isoformat(),
                "numero_disposition": rng.randint(1, 4),
                "nature_mutation": nature,
                "valeur_fonciere": valeur_fonciere,
                "code_postal": code_postal,
                "code_commune": code_commune,
                "nom_commune": commune,
                "code_departement": code_dept,
                "type_local": type_local,
                "surface_reelle_bati": surface if surface is not None else "",
                "nombre_pieces_principales": nb_pieces if nb_pieces is not None else "",
                "lot1_surface_carrez": (
                    "" if rng.random() < 0.5 else str(int((surface or 0) * 0.95))
                ),
            }
        )

    cols = list(rows[0].keys())
    with OUT.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(rows)

    print(f"Wrote {N_ROWS} rows to {OUT}")


if __name__ == "__main__":
    main()
