# Données Réelles - Forge

## 1. Push par Minute (Graphique d'Activité)

Le document inclut un graphique "Submission per minute" qui trace l'activité sur une journée complète (environ 08:00 à 23:00) :

- **Tendance Générale** : L'activité est relativement constante mais fluctue entre 0 et 20 soumissions par minute pour la majeure partie de la journée.
- **Pic d'Activité** : Un pic significatif est visible entre **20:00 et 21:00**, où les soumissions atteignent jusqu'à **40 par minute**.

---

## 2. Spécificités Techniques

Le système fonctionne selon plusieurs principes fondamentaux :

### Gestion de File

| Caractéristique | Valeur |
|-----------------|--------|
| Priorité | Aucune notion de priorité |
| Traitement | FIFO (First-In, First-Out) |
| Gestion spéciale | Aucune logique de gestion au-delà du flux standard |

### Protection contre le Débordement

Quand la file reçoit trop de tags, il n'y a pas de mécanisme de récupération ; les tags supplémentaires sont simplement **abandonnés** ("c'est juste drop" avec référence à l'"intra" de l'école).

### Monitoring & Cycle de Vie

- **Callbacks** : Un système de callback est en place pour collecter des statistiques.
- **Statuts des Tags** : Chaque tag passe par quatre étapes potentielles :
  1. **Attente** (Waiting)
  2. **En process** (In process)
  3. **Terminé** (Finished)
  4. **Fail** (Failed)

---

## Conclusion

Le document décrit un système de traitement FIFO simple pour les pushs "Forge", caractérisé par l'absence de niveaux de priorité et une politique stricte d'abandon en cas de débordement, avec un pic d'utilisation notable pendant les heures du soir.
