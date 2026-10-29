import os
import joblib
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, mean_absolute_percentage_error

def ejecutar_pipeline_mlops():
    print("[INFO] Iniciando pipeline de MLOps y entrenamiento del modelo...")
    
    # 1. Simulación de datos históricos estructurados
    np.random.seed(42)
    horas = pd.date_range(start="2026-10-01", periods=336, freq="h")
    
    df = pd.DataFrame({
        'fecHora': horas,
        'horaDelDia': horas.hour,
        'diaSemana': horas.dayofweek,
        'demandaRealMWH': 22000 + 4000 * np.sin(np.pi * horas.hour / 12) + np.random.normal(0, 300, len(horas)),
        'precioOmieEurMWH': 60 + 20 * np.cos(np.pi * horas.hour / 12) + np.random.normal(0, 5, len(horas))
    })
    
    df['lag_24h'] = df['demandaRealMWH'].shift(24)
    df = df.dropna().copy()
    
    features = ['horaDelDia', 'diaSemana', 'lag_24h', 'precioOmieEurMWH']
    X = df[features]
    y = df['demandaRealMWH']
    
    X_train, X_test = X.iloc[:-168], X.iloc[-168:]
    y_train, y_test = y.iloc[:-168], y.iloc[-168:]
    
    # 2. Entrenamiento del Modelo
    print("[INFO] Entrenando modelo de Machine Learning (Random Forest)...")
    modelo = RandomForestRegressor(n_estimators=100, random_state=42)
    modelo.fit(X_train, y_train)
    
    # 3. Guardar el artefacto físico del modelo
    os.makedirs('models', exist_ok=True)
    ruta_artefacto = 'models/modelo_predicion_24h.joblib'
    joblib.dump(modelo, ruta_artefacto)
    print(f"[OK] Artefacto del modelo guardado exitosamente en: {ruta_artefacto}")
    
    # 4. Generar predicciones
    y_pred = modelo.predict(X_test)
    
    test_df = X_test.copy()
    test_df['fecHora'] = df.iloc[-168:]['fecHora'].values
    test_df['demandaRealMWH'] = y_test.values
    test_df['demandaPredichaMWH'] = y_pred
    test_df['baseline_24h'] = test_df['lag_24h']
    test_df['precioOmieEurMWH'] = df.iloc[-168:]['precioOmieEurMWH'].values
    
    # 5. Cálculo de métricas
    mae = mean_absolute_error(test_df['demandaRealMWH'], test_df['demandaPredichaMWH'])
    rmse = np.sqrt(mean_squared_error(test_df['demandaRealMWH'], test_df['demandaPredichaMWH']))
    mape = mean_absolute_percentage_error(test_df['demandaRealMWH'], test_df['demandaPredichaMWH']) * 100
    
    print(f"--- Métricas del Modelo Entrenado ---")
    print(f"MAE: {mae:.2f} MW | RMSE: {rmse:.2f} MW | MAPE: {mape:.2f} %")
    
    # 6. Exportar resultados al esquema de base de datos
    os.makedirs('data/processed', exist_ok=True)
    
    df_predicciones = pd.DataFrame({
        'fecHora': test_df['fecHora'],
        'idModelo': 1,
        'demandaPredichaMWH': test_df['demandaPredichaMWH'].round(4)
    })
    df_predicciones.to_csv('data/processed/PrediccionesDemanda_export.csv', index=False)
    
    test_df['desviacionMWH'] = test_df['demandaRealMWH'] - test_df['demandaPredichaMWH']
    test_df['costeDesvioEstimadoEur'] = (test_df['desviacionMWH'].abs() * test_df['precioOmieEurMWH']).round(4)
    
    df_impacto = pd.DataFrame({
        'fecHora': test_df['fecHora'],
        'demandaRealMWH': test_df['demandaRealMWH'].round(4),
        'demandaPredichaMWH': test_df['demandaPredichaMWH'].round(4),
        'desviacionMWH': test_df['desviacionMWH'].round(4),
        'precioOmieEurMWH': test_df['precioOmieEurMWH'].round(4),
        'costeDesvioEstimadoEur': test_df['costeDesvioEstimadoEur'],
        'nivelAlerta': np.where(test_df['costeDesvioEstimadoEur'] > 5000, 'ALTO', 'NORMAL')
    })
    df_impacto.to_csv('data/processed/ImpactoDesviaciones_export.csv', index=False)
    
    # 7. Generar gráfica
    os.makedirs('reports/figures', exist_ok=True)
    plt.figure(figsize=(12, 6))
    plt.plot(test_df['fecHora'], test_df['demandaRealMWH'], label='Demanda Real', color='black', linewidth=1.5)
    plt.plot(test_df['fecHora'], test_df['baseline_24h'], label='Baseline (24h)', color='red', linestyle='--', alpha=0.7)
    plt.plot(test_df['fecHora'], test_df['demandaPredichaMWH'], label='Modelo IA (Random Forest)', color='green', linewidth=1.5)
    plt.title('Evaluación de Predicción de Demanda 24h - Modelo Entrenado (EcoGrid-Analytics)')
    plt.xlabel('Fecha y Hora')
    plt.ylabel('Demanda (MWH)')
    plt.legend()
    plt.grid(True, linestyle=':', alpha=0.6)
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig('reports/figures/modelo_vs_baseline.png')
    print("[OK] Pipeline de MLOps ejecutado: artefacto y exportaciones listos.")

if __name__ == "__main__":
    ejecutar_pipeline_mlops()