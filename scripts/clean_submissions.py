#!/usr/bin/env python3
"""
Script de nettoyage du fichier submissions.csv

Ce script:
1. Ajoute les noms des colonnes au CSV
2. Ajoute 1h au result_time si result_time < start_time
3. Ajoute une colonne service_time (result_time - start_time)
"""

import pandas as pd
from pathlib import Path
from datetime import timedelta

# Chemins
INPUT_FILE = Path(__file__).parent.parent / "submissions.csv"
OUTPUT_FILE = Path(__file__).parent.parent / "submissions_cleaned.csv"

# Noms des colonnes
COLUMN_NAMES = ["id", "student_id", "start_time", "exercise", "result_time"]


def main():
    print(f"Lecture du fichier: {INPUT_FILE}")
    
    # Lire le CSV sans en-têtes
    df = pd.read_csv(INPUT_FILE, header=None, names=COLUMN_NAMES)
    
    print(f"Nombre de lignes: {len(df)}")
    
    # Convertir les colonnes de temps en datetime
    df["start_time"] = pd.to_datetime(df["start_time"])
    df["result_time"] = pd.to_datetime(df["result_time"])
    
    # Compter les lignes où result_time < start_time
    mask = df["result_time"] < df["start_time"]
    count_to_fix = mask.sum()
    print(f"Lignes avec result_time < start_time: {count_to_fix}")
    
    # Ajouter 1h au result_time si result_time < start_time
    df.loc[mask, "result_time"] = df.loc[mask, "result_time"] + timedelta(hours=1)
    
    # Vérifier s'il reste des anomalies après correction
    mask_after = df["result_time"] < df["start_time"]
    count_remaining = mask_after.sum()
    if count_remaining > 0:
        print(f"⚠️ Anomalies restantes après correction: {count_remaining}")
    else:
        print("✓ Toutes les anomalies ont été corrigées")
    
    # Calculer le service_time (en secondes)
    df["service_time"] = (df["result_time"] - df["start_time"]).dt.total_seconds()
    
    # Afficher quelques statistiques
    print(f"\nStatistiques service_time (secondes):")
    print(f"  Min: {df['service_time'].min():.2f}")
    print(f"  Max: {df['service_time'].max():.2f}")
    print(f"  Moyenne: {df['service_time'].mean():.2f}")
    print(f"  Médiane: {df['service_time'].median():.2f}")
    
    # Sauvegarder le fichier nettoyé avec les en-têtes
    df.to_csv(OUTPUT_FILE, index=False)
    print(f"\nFichier nettoyé sauvegardé: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
