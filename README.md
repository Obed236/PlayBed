# PlayBed V3

PlayBed est une plateforme gratuite de mini-jeux web, accessible depuis un navigateur sur mobile et ordinateur.

**Créé et développé par Obed Gelly Ousmane Tassango.**

## Fonctionnalités principales
- Flask + Gunicorn
- PostgreSQL en production, SQLite possible en local
- 11 jeux : Pendu, Plus ou Moins, Vrai ou Faux, Quiz Express, Memory, Calcul Mental, Mot Mélangé, Suite Logique, Pair ou Impair, Chrono 10 et Action ou Vérité
- pseudo sans création de compte obligatoire
- scores persistants et classements général, quotidien, hebdomadaire et mensuel
- XP, niveaux, missions quotidiennes et hebdomadaires
- séries quotidiennes et succès
- profils joueurs et profils publics
- favoris, jeux récents et découverte par recherche/catégorie
- défis de score partageables
- Quiz Duel asynchrone entre deux joueurs
- Action ou Vérité local à 2–5 joueurs
- classes privées Action ou Vérité à distance avec code à 4 chiffres, réponses et synchronisation des tours
- choix individuel Classique/Osé pour chaque joueur majeur dans Action ou Vérité
- verrouillage automatique du niveau Osé si un mineur est présent
- PWA installable
- analytics d’interaction et suivi des Core Web Vitals
- pages éditoriales, guides, FAQ, mentions légales et politique de confidentialité
- `robots.txt`, `sitemap.xml`, canonical et données structurées
- endpoint de santé `/health`

## Jeux disponibles

| Jeu | Catégorie |
| --- | --- |
| Pendu | Lettres |
| Plus ou Moins | Logique |
| Vrai ou Faux | Culture |
| Quiz Express | Quiz |
| Memory | Mémoire |
| Calcul Mental | Logique |
| Mot Mélangé | Lettres |
| Suite Logique | Logique |
| Pair ou Impair | Rapidité |
| Chrono 10 | Rapidité |
| Action ou Vérité | Groupe |

### Action ou Vérité

Deux modes sont disponibles :
- **local** : 2 à 5 personnes jouent sur un seul téléphone ;
- **classe privée** : le créateur obtient un code à 4 chiffres et les autres joueurs rejoignent depuis leur propre appareil.

Le jeu demande l’âge au démarrage uniquement pour adapter le contenu. Chaque joueur majeur choisit individuellement entre **Classique** et **Osé**. Le niveau Osé contient des propositions plus gênantes, romantiques ou suggestives, mais reste non explicite et non dangereux. Un joueur ayant choisi Classique ne reçoit pas de proposition Osée. Si au moins une personne a moins de 18 ans, le niveau Osé est désactivé pour toute la partie afin qu’aucun contenu 18+ ne soit affiché devant un mineur. Action ou Vérité ne produit pas de score et n’influence pas les classements.

## Lancer en local

```bash
pip install -r requirements.txt
python server.py
```

Puis ouvrir `http://127.0.0.1:10000`.

## Render

Build Command :

```text
pip install -r requirements.txt
```

Start Command :

```text
gunicorn app:app
```

Variables recommandées :
- `SECRET_KEY` : clé secrète Flask forte ;
- `DATABASE_URL` : URL PostgreSQL de production ;
- `CONTACT_EMAIL` : adresse de support affichée sur les pages concernées.

## Architecture

- `core.py` : application Flask, jeux historiques, scores et base de données ;
- `extra_games.py` : jeux additionnels ;
- `action_verite.py` : jeu Action ou Vérité, mode local et classes privées ;
- `action_verite_preferences.py` : préférences individuelles Classique/Osé et sélection des propositions ;
- `action_verite_answers.py` : réponses synchronisées des classes privées ;
- `platform_routes.py` : pages publiques, guides et profils ;
- `engagement.py` : séries et classements temporels ;
- `growth.py` : XP, niveaux, missions, profils publics et défis ;
- `duels.py` : Quiz Duel ;
- `editorial_guides.py` : contenus éditoriaux longs ;
- `static/` : CSS, JavaScript et PWA ;
- `templates/` : interfaces Jinja.

## Objectif

PlayBed évolue d’un projet de mini-jeux vers une plateforme web de jeu légère : accès immédiat, progression, compétition, jeu de groupe, partage et catalogue extensible, sans imposer de compte utilisateur pour commencer à jouer.
