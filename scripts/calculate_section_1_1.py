#!/usr/bin/env python3
"""
Script de calcul des statistiques pour la section 1.1 du rapport.

Ce script analyse le fichier submissions.csv et calcule toutes les métriques
nécessaires pour la section 1.1 (Données Réelles de la Forge).
"""

import pandas as pd
from pathlib import Path
from datetime import datetime
import json

# Chemins
INPUT_FILE = Path(__file__).parent.parent / "data" / "submissions.csv"
OUTPUT_FILE = Path(__file__).parent.parent / "results" / "section_1_1_stats.json"

# Nombre de serveurs d'exécution
K = 4


def main():
    print(f"Lecture du fichier: {INPUT_FILE}")
    
    # Lire le CSV
    df = pd.read_csv(INPUT_FILE)
    
    print(f"Nombre de soumissions: {len(df)}")
    
    # Convertir les colonnes de temps en datetime (format mixte)
    df["start_time"] = pd.to_datetime(df["start_time"], format="ISO8601")
    df["result_time"] = pd.to_datetime(df["result_time"], format="ISO8601")
    
    # ==========================================
    # 1. Période analysée
    # ==========================================
    start_date = df["start_time"].min()
    end_date = df["start_time"].max()
    period_hours = (end_date - start_date).total_seconds() / 3600
    
    print(f"\n=== Période analysée ===")
    print(f"Début: {start_date}")
    print(f"Fin: {end_date}")
    print(f"Durée totale: {period_hours:.0f}h")
    
    # ==========================================
    # 2. Nombre de soumissions et étudiants
    # ==========================================
    n_submissions = len(df)
    n_students = df["student_id"].nunique()
    
    print(f"\n=== Volumes ===")
    print(f"Soumissions valides: {n_submissions}")
    print(f"Étudiants uniques: {n_students}")
    
    # ==========================================
    # 3. Taux d'arrivée (lambda)
    # ==========================================
    # Arrivées par minute (en moyenne sur toute la période)
    arrivals_per_minute = n_submissions / (period_hours * 60)
    arrivals_per_hour = arrivals_per_minute * 60
    
    print(f"\n=== Taux d'arrivée ===")
    print(f"Lambda (soumissions/min): {arrivals_per_minute:.2f}")
    print(f"Lambda (soumissions/h): {arrivals_per_hour:.1f}")
    
    # ==========================================
    # 4. Temps de service
    # ==========================================
    service_mean = df["service_time"].mean()
    service_median = df["service_time"].median()
    service_mean_min = service_mean / 60
    service_median_min = service_median / 60
    
    print(f"\n=== Temps de service ===")
    print(f"Moyenne: {service_mean:.1f}s ({service_mean_min:.1f} min)")
    print(f"Médiane: {service_median:.1f}s ({service_median_min:.1f} min)")
    
    # ==========================================
    # 5. Taux de service (mu)
    # ==========================================
    # μ = 1/temps_moyen_service (par minute)
    mu = 1.0 / service_mean_min
    
    print(f"Taux de service (μ): {mu:.2f}/min")
    
    # ==========================================
    # 6. Intensité du trafic (rho)
    # ==========================================
    # rho = lambda / (K * mu)
    rho = arrivals_per_minute / (K * mu)
    
    print(f"\n=== Intensité ===")
    print(f"ρ (K={K} serveurs): {rho:.2f}")
    print(f"Système stable: {'Oui' if rho < 1 else 'Non'}")
    
    # ==========================================
    # 7. Pics d'activité (par heure de la journée)
    # ==========================================
    df["hour"] = df["start_time"].dt.hour
    hourly_counts = df.groupby("hour").size()
    peak_hour = hourly_counts.idxmax()
    peak_count = hourly_counts.max()
    
    print(f"\n=== Pics d'activité ===")
    print(f"Heure de pointe: {peak_hour}h")
    print(f"Soumissions à l'heure de pointe: {peak_count}")
    
    # Top 3 des heures d'activité
    top_hours = hourly_counts.nlargest(3)
    print(f"Top 3 heures: {list(top_hours.index)}h avec {list(top_hours.values)} soumissions")
    
    # ==========================================
    # Résumé pour le rapport
    # ==========================================
    print("\n" + "=" * 60)
    print("RÉSUMÉ POUR LE RAPPORT (Section 1.1)")
    print("=" * 60)
    print(f"Période: {start_date.strftime('%d %b')} - {end_date.strftime('%d %b %Y')} ({period_hours:.0f}h)")
    print(f"Soumissions valides: {n_submissions}")
    print(f"Étudiants: {n_students}")
    print(f"λ (taux d'arrivée): {arrivals_per_minute:.2f}/min ({arrivals_per_hour:.1f}/h)")
    print(f"Temps de service moyen: {service_mean_min:.1f} min (médiane: {service_median_min:.1f} min)")
    print(f"μ (taux de service): {mu:.2f}/min")
    print(f"ρ (intensité, K={K}): {rho:.2f}")
    print(f"Pic d'activité: {peak_hour}h ({peak_count} soumissions)")
    
    # ==========================================
    # Sauvegarde des résultats
    # ==========================================
    results = {
        "period_start": start_date.strftime("%d %b %Y"),
        "period_end": end_date.strftime("%d %b %Y"),
        "period_hours": round(period_hours),
        "n_submissions": n_submissions,
        "n_students": n_students,
        "lambda_per_min": round(arrivals_per_minute, 2),
        "lambda_per_hour": round(arrivals_per_hour, 1),
        "service_mean_sec": round(service_mean, 1),
        "service_mean_min": round(service_mean_min, 1),
        "service_median_min": round(service_median_min, 1),
        "mu_per_min": round(mu, 2),
        "K_servers": K,
        "rho": round(rho, 2),
        "peak_hour": int(peak_hour),
        "peak_count": int(peak_count)
    }
    
    # Créer le dossier results s'il n'existe pas
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    
    with open(OUTPUT_FILE, "w") as f:
        json.dump(results, f, indent=2)
    
    print(f"\nRésultats sauvegardés dans: {OUTPUT_FILE}")
    
    return results


if __name__ == "__main__":
    main()
