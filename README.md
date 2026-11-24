# Gestion des sujets des projets tutorés

Application web de gestion du cycle de vie des sujets, projets tutorés et mémoires : étudiants, encadreurs, codirecteurs, commissions et coordination académique.

## Socle technique
- Python 3.12+ / Flask
- PostgreSQL (SQLite possible en développement)
- Flask-Login, SQLAlchemy, Flask-WTF
- Interface responsive : bleu nuit, vert émeraude, blanc et accent or

## Démarrage local
```bash
python -m venv .venv
source .venv/bin/activate # Windows : .venv\\Scripts\\activate
pip install -r requirements.txt
cp .env.example .env
flask --app run.py init-db
flask --app run.py run --debug
```

## Variables d'environnement
Voir `.env.example`. Définir impérativement `SECRET_KEY`, `DATABASE_URL` et les identifiants du premier administrateur avant une mise en production.

## Déploiement Railway
1. Créer un projet Railway et ajouter un service PostgreSQL.
2. Connecter ce dépôt GitHub au service web.
3. Définir `DATABASE_URL` (référence au service PostgreSQL) et `SECRET_KEY`.
4. Définir `ADMIN_NAME`, `ADMIN_EMAIL` et `ADMIN_PASSWORD` pour créer le premier administrateur.
5. Railway utilise le `Procfile` pour lancer Gunicorn.

## Sécurité
- Les comptes sont créés par l'administration ; aucune inscription publique.
- Les routes protégées nécessitent une session authentifiée.
- Les autorisations sont vérifiées côté serveur.
- Ne jamais committer le fichier `.env` ni des mots de passe réels.

## État
Socle initial : authentification par rôles, tableau de bord, modèles de données et interface responsive. Les circuits de validation, dépôt/versionnage documentaire, messagerie, notifications et contrôle de similarité seront ajoutés par modules successifs.