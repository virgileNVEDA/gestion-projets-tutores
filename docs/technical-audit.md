# Audit technique initial — Gestion des projets tutorés

Date de l'audit : 25 novembre 2026
Dépôt audité : virgileNVEDA/gestion-projets-tutores
Branche de travail : rebuild/full-application-audit

## 1. Périmètre vérifié

Lecture du dépôt GitHub (arbre complet, fichiers Python, templates, CSS, JavaScript, configuration et procédure Railway). L'audit est statique : aucun accès à une session authentifiée du navigateur ni à la base PostgreSQL de production n'a été utilisé. Aucun contenu ni compte de production n'a été supprimé ou migré.

## 2. Constat technique

### Socle existant
- Application Flask avec factory create_app(), blueprints auth, main et modules.
- SQLAlchemy / Flask-Migrate, Flask-Login, Flask-WTF et PostgreSQL (SQLite annoncé pour le développement).
- Modèles actuels : User, AcademicProgram, ProjectTopic, WorkflowEvent, Message, DocumentVersion, Meeting, Notification et Institution.
- Interface Jinja avec un template de base, un tableau de bord, un template générique de modules et plusieurs feuilles CSS.

### Défauts structurels observés
1. Contrôleurs trop concentrés : app/modules.py regroupe paramètres, gestion des comptes, programmes, sujets, affectations, décisions, messages, documents, réunions, notifications, rapports et exports dans une seule route générique à actions multiples.
2. Autorisations dispersées : certaines vérifications sont dans le début de la route, d'autres dans chaque branche POST et d'autres dans can_access(). Cela rend les oublis et incohérences difficiles à tester.
3. Migrations de schéma au démarrage : init-db exécute create_all() puis des ALTER TABLE conditionnels. Le schéma applicatif dépend donc du démarrage du service plutôt que d'une suite de migrations versionnées et contrôlées.
4. Stockage documentaire non pérenne : le formulaire et le code indiquent que les documents sont conservés dans le stockage local de l'application. Ce stockage ne doit pas être considéré comme archive durable sur une infrastructure de déploiement éphémère.
5. CSS historique accumulé : app.css contient des règles de structure répétées pour .main-area, .topbar et .page-content; dashboard-fix.css réécrit ces mêmes règles avec !important. Le tableau de bord a encore sa feuille spécifique. Plusieurs sources de vérité se superposent.
6. Templates fortement couplés : module.html contient plusieurs écrans et formulaires conditionnels. La navigation et le contenu de base sont assemblés dans base.html.
7. JavaScript monolithique : app.js rassemble navigation, recherche de matricule, affichage du mot de passe, barre de progression et présence. Les événements sont déclarés en plusieurs blocs DOMContentLoaded.
8. Couverture de tests absente du dépôt : aucun dossier de tests ni dépendance de test n'apparaît dans l'arbre audité.
9. Configuration de sécurité à durcir : SECRET_KEY possède une valeur de secours de développement; les paramètres de cookie et l'environnement sont pilotés par variables d'environnement. Le déploiement doit refuser une clé par défaut en production.
10. État du tableau de bord : la route /dashboard calcule ses données et transmet topics, stats, status_chart, monthly_chart et now. Le template de base rend le bloc content dans .page-content. La cascade CSS est contradictoire. Le statut HTTP 200 seul ne prouve pas que la géométrie visuelle est correcte.

### Risques fonctionnels et sécurité à traiter
- La route générique /modules/<section> combine l'identification de l'écran et l'exécution d'actions POST; il faut isoler chaque cas d'usage et centraliser les politiques d'accès.
- La création d'un sujet par un utilisateur non étudiant doit vérifier explicitement le rôle de l'étudiant cible et le droit du créateur à agir pour lui.
- Les opérations d'affectation doivent vérifier l'existence et le rôle des utilisateurs sélectionnés avant de lire leurs attributs.
- Les fichiers doivent être validés par extension, type réel, taille et droits d'accès; le stockage doit être abstrait et persistant.
- Les exports doivent éviter les requêtes N+1 et appliquer une politique d'accès commune aux vues et aux téléchargements.
- Les opérations destructives doivent préserver les historiques et être couvertes par des tests transactionnels.

## 3. Architecture cible proposée

```text
app/
  __init__.py              # factory et enregistrement des composants
  extensions.py            # extensions Flask
  config.py                # configurations dev/test/prod
  models/                  # modèles et relations métier (migration progressive)
  auth/                    # authentification, profils, sessions
  dashboard/               # agrégats, règles d'affichage, routes
  academic/                # sujets, programmes, affectations, workflow
  people/                  # étudiants, enseignants, rôles
  communication/           # messages, notifications, réunions
  documents/               # validation, stockage, versions, téléchargement
  administration/          # établissement, paramètres, rapports
  services/                # cas d'usage et règles métier
  policies/                # contrôle d'accès centralisé
  templates/
    layouts/
    components/
    pages/
  static/
    css/                    # tokens, layout, components, pages
    js/                     # modules ES par fonctionnalité
migrations/
tests/
  unit/
  integration/
  security/
  ui/
```

Cette cible est une architecture de travail. Le découpage sera effectué progressivement afin de garder les routes et les données existantes compatibles.

## 4. Principes de reconstruction
- Aucun changement destructif sur la base de production.
- Une seule source CSS pour la structure : sidebar, en-tête, zone de contenu et responsive.
- Le contenu suit directement l'en-tête fixe; aucune hauteur vide artificielle, aucun spacer vertical.
- Contrôleurs minces; règles métier dans les services; autorisations dans les policies.
- Migrations versionnées; pas de modification opportuniste du schéma à chaque démarrage.
- Stockage documentaire derrière une interface; aucune promesse de conservation avant configuration du stockage persistant.
- Validation serveur pour chaque entrée, CSRF pour les formulaires, échappement des sorties et contrôle d'accès au téléchargement.
- Accessibilité : titres hiérarchisés, labels, focus visible, boutons nommés, navigation clavier.
- Responsive testé sur largeurs mobiles, tablettes et ordinateurs.
- Déploiement d'abord sur branche de reconstruction / environnement de test; production seulement après tests et validation.

## 5. Plan d'exécution
### Phase 0 — Audit et filet de sécurité
- Cartographier toutes les routes, permissions, modèles, formulaires et actions.
- Ajouter une factory configurable et des tests d'intégration.
- Capturer le comportement de référence avant toute migration.

### Phase 1 — Fondations
- Configurations séparées et validation des variables obligatoires.
- Policies de rôles centralisées.
- Migrations Alembic explicites.
- Journalisation structurée et route de santé.

### Phase 2 — Interface et tableau de bord
- Layout unique, flux vertical documenté et testé.
- Dashboard calculé par rôle, composants indépendants et états vides.
- Suppression progressive des CSS contradictoires.

### Phase 3 — Modules métier
- Comptes et programmes.
- Sujets, affectations et validation.
- Documents et versions.
- Messagerie, notifications et réunions.
- Rapports et exports.

### Phase 4 — Qualité et mise en production
- Tests unitaires, intégration, sécurité et responsive.
- Vérification des migrations sur copie de base.
- Déploiement de préproduction, tests de fumée, puis bascule contrôlée.

## 6. Limites de cet audit

Les conclusions ci-dessus proviennent des fichiers du dépôt et des journaux déjà consultés. Elles ne remplacent pas un audit de la base réelle, des variables secrètes, du stockage monté, ni des calculs de layout dans un navigateur connecté. Ces éléments devront être vérifiés dans un environnement de test sans exposer les secrets.