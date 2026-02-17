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

def main():
    n = 150
    rows = []
    for i in range(n):
        notti = random.choices([1, 2, 3, 4, 5, 7], weights=[15, 25, 20, 15, 15, 10])[0]
        ospiti = random.choices([1, 2, 3, 4, 5], weights=[20, 35, 25, 15, 5])[0]
        canale = random.choice(CANALI)
        giorno = random.choice(GIORNI)
        storico = random.choices([0, 1, 2, 3, 5], weights=[40, 25, 20, 10, 5])[0]
        spesa = round(random.uniform(80, 350), 2)
        data = f"2024-{random.randint(1, 12):02d}-{random.randint(1, 28):02d}"
        camera = random.choice(CATEGORIE)
        rows.append({
            "cliente_id": f"C{i+1000}",
            "data_arrivo": data,
            "numero_notti": notti,
            "numero_ospiti": ospiti,
            "canale": canale,
            "giorno_arrivo": giorno,
            "storico_soggiorni": storico,
            "spesa_media": spesa,
            "categoria_camera": camera,
        })
    df = pd.DataFrame(rows)
    df.to_excel(OUT, index=False, engine="openpyxl")
    print(f"Creato {OUT} con {len(df)} righe.")

if __name__ == "__main__":
    main()
