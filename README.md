# PlayBed V2

Version autonome de PlayBed.

## Fonctionnalités
- Flask + Gunicorn
- 5 jeux : Pendu, Plus ou Moins, Vrai ou Faux, Quiz Express, Memory
- pseudo sans création de compte
- scores enregistrés dans SQLite
- classement général et records par jeu
- mode sombre / clair
- responsive mobile
- routes SEO de base : robots.txt et sitemap.xml
- endpoint /health

## Lancer en local

```bash
pip install -r requirements.txt
python server.py
```

Puis ouvrir http://127.0.0.1:10000

## Render

Build Command:
```text
pip install -r requirements.txt
```

Start Command:
```text
gunicorn app:app
```

Ajoute idéalement une variable d'environnement `SECRET_KEY`.

### À propos de SQLite sur un hébergement cloud
Le fichier `playbed.db` est créé automatiquement. Pour une conservation durable des scores en production,
utilise un stockage persistant ou remplace SQLite par une base PostgreSQL.
