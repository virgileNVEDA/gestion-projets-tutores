# Plan de migrations et de conservation des données

## État constaté

- Flask-Migrate est initialisé dans l'application.
- Aucun répertoire `migrations/` ni historique Alembic n'est présent dans la branche audit au moment de cette vérification.
- La commande `init-db` appelle actuellement `db.create_all()` et exécute des `ALTER TABLE` conditionnels.
- Les tests utilisent une base SQLite isolée et recréent leurs tables; ils ne prouvent pas la compatibilité avec la base PostgreSQL de production.

## Règle de sécurité

Aucune migration initiale ne doit être générée puis appliquée directement à la production sans comparer le schéma réel de PostgreSQL avec les modèles. Une migration de base mal calibrée pourrait tenter de recréer des tables existantes ou supprimer/altérer des données.

## Procédure prévue

1. Obtenir une sauvegarde PostgreSQL vérifiée et un environnement de staging isolé.
2. Inventorier le schéma réel (tables, colonnes, index, contraintes, clés étrangères).
3. Comparer cet inventaire aux modèles SQLAlchemy et à l'historique réel de l'application.
4. Créer une révision Alembic de référence adaptée au schéma existant, sans opération destructive.
5. Tester la migration sur une copie de la base, puis vérifier les comptes, dossiers, documents et historiques.
6. Faire valider le plan de déploiement avant toute application en production.
7. Remplacer progressivement les modifications de schéma cachées dans `init-db` par des migrations versionnées, après validation du scénario de transition.

## Stockage documentaire

Le service `LocalDocumentStorage` accepte une racine configurable via `DOCUMENT_STORAGE_ROOT`. En hébergement Railway, cette variable doit pointer vers un volume persistant monté sur le service. Sans volume persistant, les documents écrits dans le système de fichiers éphémère ne sont pas garantis après redéploiement ou remplacement d'instance.

## Vérifications encore nécessaires

- Vérifier la configuration effective du volume Railway et ses permissions d'écriture.
- Vérifier la restauration d'une sauvegarde PostgreSQL.
- Vérifier la compatibilité de toutes les routes avec le schéma réel.
- Ajouter les tests d'intégration PostgreSQL et de migration avant l'autorisation de test utilisateur.
