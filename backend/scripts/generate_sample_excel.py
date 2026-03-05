"""
Genera un file Excel di esempio per testare upload e segmentazione.
Esegui: python -m scripts.generate_sample_excel
"""
import random
from pathlib import Path

import pandas as pd

# Assicurati di essere nella cartella backend
ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "sample_arrivi.xlsx"

CANALI = ["corporate", "GDS", "Booking.com", "Expedia", "direct", "sito", "OTA", "phone"]
GIORNI = ["lun", "mar", "mer", "gio", "ven", "sab", "dom"]
CATEGORIE = ["Standard", "Superior", "Deluxe", "Junior Suite", "Suite"]
PRENOTANTI = ["cliente", "agenzia", "azienda", "tour operator", "cliente"]

def main():
    n = 150
    rows = []
    for i in range(n):
        notti = random.choices([1, 2, 3, 4, 5, 7], weights=[15, 25, 20, 15, 15, 10])[0]
        ospiti = random.choices([1, 2, 3, 4, 5], weights=[20, 35, 25, 15, 5])[0]
        canale = random.choice(CANALI)
        giorno = random.choice(GIORNI)
        spesa = round(random.uniform(80, 350), 2)
        data = f"2024-{random.randint(1, 12):02d}-{random.randint(1, 28):02d}"
        camera = random.choice(CATEGORIE)
        anticipo = random.choices([3, 7, 14, 21, 45, 90], weights=[15, 20, 25, 20, 12, 8])[0]
        prenotante = random.choice(PRENOTANTI)
        bambini = random.choices([0, 0, 1, 2], weights=[50, 30, 15, 5])[0]
        rows.append({
            "cliente_id": f"C{i+1000}",
            "data_arrivo": data,
            "numero_notti": notti,
            "numero_ospiti": ospiti,
            "canale": canale,
            "giorno_arrivo": giorno,
            "spesa_media": spesa,
            "categoria_camera": camera,
            "anticipo_giorni": anticipo,
            "prenotante": prenotante,
            "numero_bambini": bambini,
        })
    df = pd.DataFrame(rows)
    df.to_excel(OUT, index=False, engine="openpyxl")
    print(f"Creato {OUT} con {len(df)} righe.")

if __name__ == "__main__":
    main()
