# Decisions — Binôme `Franck` × `Julien D` (M3-B2 Acerox)

> Document à compléter à 2 pendant la phase sync (15 min avant de coder).
> Servira de référence pendant la phase async + RDV vendredi.

## 1. Source choisie pour l'ingestion

> Quelle source intégrez-vous en M3-B2 ? Argumentez en 3 lignes max.

**Choix** : ☑ `capteurs_iot.csv` (CSV ~51k lignes) ☐ `erp_export.json` (JSON ~2k ordres)

**Argument** :
- IoT : volumétrie réelle — 51k lignes = apprendre à gérer l'échelle, migration + ingestion performantes
- IoT : qualité données complexe — capteurs défaillants (Roubaix L3), valeurs aberrantes, manquants fréquents = enjeu production réel
- IoT : normalisation structurante — timestamps à parser, numériques flottants avec variation, gestion anomalies capteur = apprentissage robustesse

**Raison du rejet d'ERP** : On privilégie le jeux de données basé sur le volume avec un parsing de données plutot que celui sur l'erp avec des enjeux RGPD 

**Réflexe stockage (3 lignes)** :
- SQLite relationnelle ici : données IoT structurées, schéma stable, besoins OLTP légers et volumétrie locale (< 1 Go) ; c'est l'option la plus simple et suffisante.
- MongoDB si la source devient fortement semi-structurée (JSON imbriqué, schéma variable, évolutions fréquentes) et que la flexibilité document apporte plus que les jointures SQL.
- Parquet si l'usage devient surtout analytique/append-only (agrégations massives, lecture colonne, historisation) ou si le volume augmente au-delà du confortable en SQLite.

## 2. Stratégie de gestion des doublons

> Comment gérez-vous les doublons à l'ingestion ? `INSERT OR IGNORE` SQL,
> upsert applicatif, dédup pandas avant insertion ?

**Choix** : Déduplication en 2 temps :
- en amont dans pandas sur la clé métier (`timestamp`, `sensor_id`) avec conservation de la dernière valeur,
- puis garde-fou en base avec contrainte d'unicité (`uq_mesures_iot_timestamp_sensor`) + filtrage applicatif avant insert.

**Argument** :
- L'ingestion doit rester idempotente même si le fichier source contient des doublons.
- Le nettoyage pandas réduit les inserts inutiles et garde une version stable des mesures.
- La contrainte SQL protège l'intégrité même si la logique applicative évolue.

## 3. Stratégie RGPD (si vous prenez ERP)

> Si vous prenez ERP : que faites-vous de `ouvrier_id` ?

- ☐ Suppression pure
- ☐ Hash salé (avec quel sel ?)
- ☐ Conservation pseudonymisée (justifier)

**Argument** : ...

## 4. Stratégie de tests

> Quels 3 tests minimum allez-vous écrire ?

1. Migration appliquée → la table existe : `test_mesures_iot_table_exists_after_schema_creation` vérifie la présence de `mesures_iot`.
2. Ingestion d'un fichier valide → N lignes insérées sans doublon : `test_ingest_valid_file_inserts_n_rows_without_duplicates` attend `inserted == 3` et des clés (`timestamp`, `sensor_id`) uniques.
3. Ingestion fichier malformé → exception claire, BDD inchangée : `test_ingest_malformed_file_raises_exception_without_modifying_db` attend `NormalizationError` et 0 ligne en base avant/après.

## 5. Convention binôme

- Driver / Navigator switch toutes les **30 min** : ☐ oui ☐ adapté à...
- Tous les commits significatifs ont `Co-authored-by:` : ☐ oui ☐ ...
- Branche perso ou main partagée : ...

## 6. Conformité au contrat de données

> Confrontez votre livraison à `ressources/contrat_donnees_modele.md`. Pour
> chaque clause de qualité **honorée** : laquelle, comment, et **où** dans le
> code. (Documenté ici — c'est ce que vous montrez au RDV vendredi.)

| Clause du contrat | Honorée ? | Comment / où dans le code |
|---|---|---|
| Unicité respectée (ingestion idempotente) | ☑ | Clé unique en base via `UniqueConstraint(timestamp, sensor_id)` + dédup pandas `drop_duplicates(subset=["timestamp", "sensor_id"], keep="last")` + filtre des clés déjà présentes avant insert. |
| Manquants traités explicitement | ☑ | `dropna` sur champs obligatoires (`timestamp`, `site`, `line_id`, `sensor_id`, `temperature_c`, `debit_uh`) ; `vibration_mms` conservé nullable (`None` en base). |
| Capteur défaillant Roubaix L3 : repéré + décision tracée (écarter / marquer / aval) *(option A)* | ☑ | Décision : écarter à l'ingestion via `faulty_mask` (site Roubaix, line_id=3, température 140-160, vibration 12.0), puis filtrage `df = df.loc[~faulty_mask]`. |
| `ouvrier_id` hashé ou retiré, jamais en clair *(option B)* | ☐ / s.o. | ... |
| Types conformes (DateTime, numériques typés) | ☑ | Parsing explicite: `pd.to_datetime` pour `timestamp`, `pd.to_numeric` pour numériques, cast `line_id` en `int`; modèle SQLAlchemy typé (`DateTime`, `Float`, `Integer`, `String`). |

---

*Décisions tracées par le binôme `Julien D` × `Franck` — `01/07/2026`.*
