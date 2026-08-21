# PlayBed V3

PlayBed est une plateforme gratuite de mini-jeux web, accessible depuis un navigateur sur mobile et ordinateur.

**Créé et développé par Obed Gelly Ousmane Tassango.**

## Fonctionnalités principales
- Flask + Gunicorn
- PostgreSQL en production, SQLite possible en local
- 10 jeux : Pendu, Plus ou Moins, Vrai ou Faux, Quiz Express, Memory, Calcul Mental, Mot Mélangé, Suite Logique, Pair ou Impair et Chrono 10
- pseudo sans création de compte obligatoire
- scores persistants et classements général, quotidien, hebdomadaire et mensuel
- XP, niveaux, missions quotidiennes et hebdomadaires
- séries quotidiennes et succès
- profils joueurs et profils publics
- favoris, jeux récents et découverte par recherche/catégorie
- défis de score partageables
- Quiz Duel asynchrone entre deux joueurs
- PWA installable
- analytics d’interaction et suivi des Core Web Vitals
- pages éditoriales, guides, FAQ, mentions légales et politique de confidentialité
- `robots.txt`, `sitemap.xml`, canonical et données structurées
- base expérimentale PlayBed Developer / SDK
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
- `platform_routes.py` : pages publiques, guides et profils ;
- `engagement.py` : séries et classements temporels ;
- `growth.py` : XP, niveaux, missions, profils publics et défis ;
- `duels.py` : Quiz Duel ;
- `editorial_guides.py` : contenus éditoriaux longs ;
- `static/` : CSS, JavaScript, PWA et SDK ;
- `templates/` : interfaces Jinja.

## Objectif

PlayBed évolue d’un projet de mini-jeux vers une plateforme web de jeu légère : accès immédiat, progression, compétition, partage et catalogue extensible, sans imposer de compte utilisateur pour commencer à jouer.
