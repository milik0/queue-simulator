# Évaluation en situation : Analyse de la Moulinette

## Contexte

Cette section regroupe les éléments nécessaires pour effectuer l'évaluation sommative du cours. Il s'agit d'un nanoprojet à réaliser en groupe (4 à 6 étudiants). L'objectif pour l'équipe enseignante est de recueillir des informations utiles quant à vos compétences dans le traitement de sujets ouverts.

## Parti Pris

Dans la démarche proposée, nous cherchons à analyser le comportement d'un système d'attente via deux perspectives complémentaires :

1. **La compréhension des modèles théoriques simples.**
2. **La simulation maîtrisée de systèmes plus complexes.**

Ces deux perspectives sont reliées : la première est nécessaire pour réaliser la simulation des composants de la seconde, et la seconde est utile pour étudier les comportements pathologiques de tous les modèles, y compris les plus simples.

## Énoncé de la SAÉ

On propose, dans cette activité, de s’attarder sur l’infrastructure de correction automatique de l’École, **la moulinette**. Notre objectif est d’en effectuer une analyse sous l’angle des systèmes d’attente.
Les éléments présentés constituent une simplification de la réalité, mais les questionnements relèvent de considérations réelles ayant été au cœur de son développement.

**Qu'est-ce qu'une moulinette ?**
Une moulinette est une infrastructure logicielle qui permet l’exécution de tests unitaires sur un code fourni par un tiers. Ces tests décrivent les spécifications fonctionnelles et techniques attendues, et leur exécution fournit un retour sur la conformité du code.

**Format du sujet**
Le sujet ne s’articule pas comme une évaluation fermée classique. Il prend une forme descriptive proche des constats préliminaires d'une phase d'analyse. On attend de vous que vous proposiez une **modélisation du contexte**, en explicitant vos hypothèses.

## Terminologie

### Utilisateur

Personne ayant accès à l’infrastructure dans le cadre d’une activité pédagogique. Actions possibles :

* **Pousser son code** : Mécanique standard de versionnage.
* **Pousser un tag** : Déclenche l'exécution des test-suites associées pour obtenir un retour sur la conformité.

### Moulinette

Une moulinette est constituée de :

* **Une test-suite** : Ensemble de tests unitaires (éventuellement stratifiés).
* **Un niveau d’information de retour** : Erreur précise, aide spécifique, ou simple message de rejet.
* **Des ressources** : Nombre de push tags autorisés (total, par heure, plages horaires).

### Workflow Nominal

1. L'étudiant code (exercices, projet, TP) dans un repository git dédié (commits/pushs classiques).
2. Lorsqu’un **tag réservé** est utilisé, une vérification est effectuée.
3. Si valide, la test-suite est exécutée selon le schéma du système d’attente (immédiat, file d'attente, etc.).
4. Le résultat est affiché à l’étudiant selon les contraintes définies.

## Étude de Cas

L’étude implique des choix dépendants du contexte. Les cas suivants sont présentés par ordre croissant de complexité. Une analyse de comportement est attendue pour chacun.

### 1. Waterfall

**Modèle :**

1. Un *push tag* place le code dans une file d’attente FIFO infinie (K serveurs disponibles).
2. Une fois exécuté, le résultat est placé dans une file d’attente FIFO infinie (1 serveur unique) pour l'envoi vers le front.

**Votre tâche :**

1. **Modélisation et Simulation** : Proposez un système d’attente modélisant ce contexte. Simulez et analysez son comportement selon les paramètres.
2. **Hypothèse de charge (Files finies)** : Avec beaucoup d'étudiants, les files infinies sont irréalistes. Soient $k_s$ et $k_f$ les tailles des files d’exécution et de renvoi.
   * Si refus au push tag : Message d'erreur.
   * Si refus au renvoi (seconde file) : Retour vide ("page blanche").
   * *Analyse* : Discutez des proportions de refus selon les paramètres.
3. **Back-up** : Un back-up des résultats est mis en place avant l'envoi vers la seconde file pour éviter la perte de données.
   * *Questions* : Quel impact sur la proportion de pages blanches ? Quels problèmes peuvent surgir ? Avantages d'un back-up aléatoire vs systématique ?
   * *Calcul* : Calculez le temps de séjour moyen et la variance empirique.

### 2. Channels and Dams

**Observation :** Disparités de temps d'attente. Ex: Population ING (arrivées fréquentes) vs Population PREPA (rendus rares mais longs).

**Votre tâche :**

1. **Simulation** : Simulez les variations de temps de séjour par population décrites.
2. **Régulation** : Introduction d'un blocage de la moulinette pour la population ING pendant un temps $t_b$, puis ouverture pour $t_b/2$, etc.
   * *Comparaison* : Comparez ce modèle avec le précédent (temps de séjour).
   * *Optimisation* : Proposez un autre système d’attente pour minimiser le temps de séjour moyen pour les deux populations.

## Livrables et Modalités

**Travail de groupe** : 4 à 6 étudiants.
**Livrables attendus** :

* Code de simulation.
* Analyse du comportement pour chaque cas :
  * (a) Paramètres en jeu.
  * (b) Comportement et stabilité.
  * (c) Évaluation (métriques standard : nombre d’agents, temps de séjour, taux de blocage...).
  * (d) Synthèse et recommandations (plages de paramètres, analyse des risques UX).
* Résultats bruts des simulations.

**Important** : Vos arguments doivent être étayés par des éléments factuels et un benchmarking statistique. Une occurrence unique ne suffit pas.

**Suivi** : Évaluations formatives, séance de coaching (30 min), soutenance (15 min + questions).

---

## Évaluation par Compétences

Le projet est évalué selon le référentiel de compétences de la formation ingénieur (RC@EPITA).
**Compétence cible** : *Concevoir des solutions répondant à des besoins et des problèmes complexes*.
**Niveau visé (Expert)** : *Installer une solution dans son écosystème et dans le temps*.

L'évaluation se fera lors de la soutenance et via le rapport, sur la base de la grille critériée suivante :

### 1. Installer une démarche itérative de conception (Métriques)

*Objectif : S'appuyer sur des métriques prédéfinies pour guider la conception.*

* **Attendu** : Métriques qualifiées et priorisées. Alignement de l'historique des itérations sur ces métriques. Comparatif des solutions isolées au regard de métriques explicites.
* **Dépasse les attentes** : Contextualisation des métriques au regard des différents acteurs. Préconisations appuyées par une variété de simulations quantifiables. Prise en compte des risques encourus.

### 2. Analyser les limites et émettre des recommandations (Validité)

*Objectif : Améliorer le comportement et le périmètre de validité de la solution.*

* **Attendu** : Démarche systémique de tests du périmètre de validité. Qualification du comportement de la solution au sein de ce périmètre, au regard de comportements théoriques standards.
* **Dépasse les attentes** : Benchmark versionné comprenant une identification du périmètre de validité. Qualification du comportement (comparaison aux modèles théoriques). Consolidation des résultats par une analyse statistique des métriques en sortie.

### 3. Intégrer des facteurs externes (Humains, Organisationnels)

*Objectif : Formuler une solution tenant compte de son environnement.*

* **Attendu** : Qualification des facteurs externes et analyse des enjeux de la solution pour chacun. Identification des contraintes humaines et organisationnelles.
* **Dépasse les attentes** : Qualification de l'impact de la solution. Test contre des scénarios distincts en s'appuyant sur une étude de terrain ou des interviews.

**Note** : Les soutenances auront lieu entre le 15/01/2025 et le 19/02/2025.
