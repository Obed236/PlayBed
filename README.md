# PlayBed V3

PlayBed est une plateforme gratuite de mini-jeux web, accessible depuis un navigateur sur mobile et ordinateur.

**Créé et développé par Obed Gelly Ousmane Tassango.**

## Fonctionnalités principales
- Flask + Gunicorn
- PostgreSQL en production, SQLite possible en local
- 11 jeux : Pendu, Plus ou Moins, Vrai ou Faux, Quiz Express, Memory, Calcul Mental, Mot Mélangé, Suite Logique, Pair ou Impair, Chrono et Action ou Vérité
- pseudo sans création de compte obligatoire
- scores persistants et classements général, quotidien, hebdomadaire et mensuel
- XP, niveaux, missions quotidiennes et hebdomadaires
- séries quotidiennes et succès
- profils joueurs et profils publics
- favoris, jeux récents et découverte par recherche/catégorie
- défis de score partageables
- affrontements 1 contre 1 avec mise de points virtuels sur tous les jeux à score
- solde de défi lié à la session du navigateur pour éviter qu’un simple pseudo puisse prendre les points d’un autre joueur
- une seule manche par joueur et comparaison automatique des scores
- remboursement des mises en cas d’égalité ou d’annulation avant toute manche
- Chrono avec une cible aléatoire de 5 à 30 secondes, différente de la partie précédente
- Action ou Vérité local à 2–5 joueurs
- classes privées Action ou Vérité à distance avec code à 4 chiffres, réponses et synchronisation des tours
- choix individuel Classique/Osé/Très osé pour chaque joueur majeur dans Action ou Vérité
- verrouillage automatique des niveaux adultes si un mineur est présent
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
| Chrono | Rapidité |
| Action ou Vérité | Groupe |

### Affrontements 1 contre 1

Le mode `/affronter` permet de choisir un jeu à score et une mise de points virtuels. Le créateur partage ensuite le lien du défi à un adversaire.

Chaque navigateur possède un solde de défi séparé du simple texte du pseudo. Le solde commence avec 1 000 points virtuels et les parties terminées dans les jeux à score peuvent le créditer. Quand un défi est accepté, la même mise est retirée aux deux joueurs. Le meilleur score reçoit les deux mises, soit un gain net égal à la mise de l’adversaire. Une égalité rembourse les deux mises.

Les points de défi n’ont aucune valeur monétaire : ils ne peuvent pas être achetés, retirés, convertis en argent ou échangés contre un bien réel. Action ou Vérité est exclu des affrontements car il n’a pas de score permettant de désigner un gagnant.

### Chrono

À chaque nouvelle partie, PlayBed choisit une durée entière entre **5 et 30 secondes**. La nouvelle cible ne peut pas être identique à celle de la partie précédente. Le joueur voit la durée à viser, puis le temps s’écoule sans chronomètre visible. Le score dépend uniquement de l’écart entre le temps réel et la cible.

### Action ou Vérité

Deux modes sont disponibles :
- **local** : 2 à 5 personnes jouent sur un seul téléphone ;
- **classe privée** : le créateur obtient un code à 4 chiffres et les autres joueurs rejoignent depuis leur propre appareil.

Le jeu demande l’âge au démarrage uniquement pour adapter le contenu. Chaque joueur majeur choisit individuellement entre **Classique**, **Osé** et **Très osé**. Un joueur ayant choisi Classique ne reçoit pas de proposition d’un niveau supérieur. Si au moins une personne a moins de 18 ans, les niveaux adultes sont désactivés pour toute la partie afin qu’aucun contenu 18+ ne soit affiché devant un mineur. Un joueur peut toujours passer une question ou une action. Action ou Vérité ne produit pas de score et n’influence pas les classements.

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
- `chrono_variation.py` : cible aléatoire et calcul du Chrono ;
- `versus.py` : solde de défi et affrontements 1 contre 1 avec mise de points virtuels ;
- `action_verite.py` : jeu Action ou Vérité, mode local et classes privées ;
- `action_verite_preferences.py` : préférences individuelles et sélection des propositions ;
- `action_verite_answers.py` : réponses synchronisées des classes privées ;
- `platform_routes.py` : pages publiques, guides et profils ;
- `engagement.py` : séries et classements temporels ;
- `growth.py` : XP, niveaux, missions, profils publics et défis ;
- `editorial_guides.py` : contenus éditoriaux longs ;
- `static/` : CSS, JavaScript et PWA ;
- `templates/` : interfaces Jinja.

## Objectif

PlayBed évolue d’un projet de mini-jeux vers une plateforme web de jeu légère : accès immédiat, progression, compétition, jeu de groupe, partage et catalogue extensible, sans imposer de compte utilisateur pour commencer à jouer.
