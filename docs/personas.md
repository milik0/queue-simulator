# Personas - ERO2

Ce document définit trois profils d'utilisateurs clés pour le projet d'optimisation du système de rendu ("moulinette") de l'EPITA.

---

## 1. L'Utilisateur Final : Robert (L'Étudiant)

| Attribut | Valeur |
|----------|--------|
| **Profil** | Étudiant en ING1, stressé par les échéances |
| **État d'esprit** | "Stress & Deadline" |

### Attentes Majeures

- **Immédiateté (Feedback)** : Il utilise la moulinette comme un outil de débogage. Une attente supérieure à 30 secondes lui fait perdre le fil de son travail.
- **Fiabilité** : Il craint par-dessus tout l'erreur technique ou la "page blanche" lors d'un rendu à 23h50. Il a besoin de savoir si son rendu a été pris en compte.
- **Équité** : Il ne supporte pas de voir des camarades obtenir leurs résultats avant lui s'ils ont soumis après.

### Intérêt de l'Étude
Garantir son résultat par une simulation de sauvegarde (back-up) et minimiser la variance du temps d'attente (prévisibilité).

---

## 2. La Décideuse Stratégique : Valérie (Scolarité / Direction des Études)

| Attribut | Valeur |
|----------|--------|
| **Profil** | Responsable de la qualité et garante de la valeur du diplôme |
| **État d'esprit** | "Qualité & Risques" |

### Attentes Majeures

- **Gestion des coûts** : Elle cherche le compromis idéal entre budget serveur et satisfaction étudiante (ex: 95% des étudiants ne doivent pas attendre plus de 2 min).
- **Équité pédagogique** : Doit-on prioriser les examens finaux par rapport aux TP hebdomadaires ?
- **Gestion de crise** : Réduire le nombre de plaintes par mail en cas de panne système.

### Intérêt de l'Étude
Obtenir des recommandations sur les risques UX et comparer les modèles de régulation (Dams) pour optimiser le budget.

---

## 3. L'Opérateur Technique : Alex (L'Assistant / YAKA)

| Attribut | Valeur |
|----------|--------|
| **Profil** | Responsable de l'infrastructure technique (ACU/YAKA) |
| **État d'esprit** | "Performance & Stabilité" |

### Attentes Majeures

- **Protection du système (Throttling)** : Il veut limiter les abus (étudiants qui "poussent" toutes les 10 secondes) via un blocage temporaire (t_b).
- **Dimensionnement** : Configurer précisément la taille des files d'attente (k_s et k_f) pour éviter tant les rejets de connexion que l'explosion de la mémoire serveur.
- **Identification des goulots d'étranglement** : Notamment sur le retour d'information (file unique de renvoi).

### Intérêt de l'Étude
Obtenir les paramètres exacts pour les fichiers de configuration (durée de blocage, taille des files) et savoir si la séparation des flux (Channels) est techniquement rentable.

---

## Tableau de Synthèse

| Critère | Robert (Étudiant) | Valérie (Scolarité) | Alex (Tech/Deployer) |
|---------|-------------------|---------------------|----------------------|
| **Focus** | Expérience Utilisateur (UX) | Qualité de service & Coûts | Robustesse & Paramétrage |
| **Objectif** | Note rapide et sans erreur | Aucun scandale pendant les examens | Le système ne doit pas crasher |
| **Enjeu** | Temps de séjour & Back-up | Taux de rejet & Budget | Algorithme de régulation & Files finies |
| **Question clé** | "Est-ce que j'aurai une page blanche ?" | "Est-ce qu'on traite tout le monde équitablement ?" | "Quelles valeurs je mets dans le fichier de config ?" |
