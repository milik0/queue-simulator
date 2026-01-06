# Approches de Modélisation - ERO2

## 1. Niveaux de Modélisation

### Niveau 1 : Processus de Poisson Homogène (La Base)

- **Concept** : Les étudiants soumettent leur code de manière indépendante et aléatoire.
- **Modèle** : Les temps inter-arrivées suivent une **distribution exponentielle (λ)**. C'est la fondation standard pour les modèles de files **M/M/k**.

### Niveau 2 : Processus Non-Homogène (Deadlines/Ateliers)

- **Concept** : Les taux d'arrivée ne sont pas constants ; l'activité augmente à l'approche des deadlines.
- **Modèle** : λ est une fonction du temps, **λ(t)**, typiquement représentée par une courbe linéaire ou exponentielle croissante.
- **Observation** : Ce niveau met en évidence comment la stabilité d'un système peut changer au cours du temps (stable au début, instable à la fin).

### Niveau 3 : Arrivées par Lots (Travail de Groupe)

- **Concept** : Les étudiants travaillant en groupe peuvent pousser leur code en successions rapides, ou plusieurs membres peuvent tester simultanément.
- **Modèle** : **Modèle M^X/M/k**, où *X* représente la taille du "lot" de soumissions.

---

## 2. Outils & Métriques

### Outils
- **SimPy** : Simulation à événements discrets
- **NumPy/pandas** : Gestion des données
- **Matplotlib/Seaborn** : Visualisation des résultats

### Métriques Clés

| Métrique | Description |
|----------|-------------|
| **Stabilité** | Analyse de la charge système et longueur de file |
| **Perte** | Surveillance des "Tag Loss" causés par débordement de file ou erreurs serveur |
| **Temps d'attente** | Comparaison des distributions de temps entre différentes filières (ING vs PREPA) |

---

## 3. Propositions d'Optimisation

### Files Prioritaires
Implémentation d'un ordonnancement **Shortest Job First (SJF)** (ex: prioriser les jobs ING sur les jobs PREPA).

### Voies Dédiées
Réservation de serveurs spécifiques pour certains types de tâches (ex: 1 serveur pour ING, K-1 pour tout le monde).

### Scaling Dynamique
Augmentation automatique de la capacité si la longueur de file dépasse un seuil défini.
