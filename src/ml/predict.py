import os
import pandas as pd
import numpy as np

def generar_pipeline_prediccion():
    print("[INFO] Iniciando pipeline de ingesta y predicción...")
    horas = [f"{i:02d}:00" for i in range(24)]
    np.random.seed(42)
    demanda_base = np.random.uniform(350, 650, size=24)

    df_prediccion = pd.DataFrame({
        'Hora': horas,
        'Demanda_Predicha_MW': np.round(demanda_base, 2),
        'Impacto_Economico_Est_Eur': np.round(demanda_base * 0.15, 2)
    })

    os.makedirs("data/processed", exist_ok=True)
    output_path = "data/processed/prediccion_24h.csv"
    df_prediccion.to_csv(output_path, index=False)
    print(f"[OK] Predicción generada con éxito en: {output_path}")
    print(df_prediccion.head())

if __name__ == "__main__":
    generar_pipeline_prediccion()