import http.server 
import urllib.parse as uparse
from random import randint, choice

class handler(http.server.SimpleHTTPRequestHandler):

    # Le dictionnaire `games` associe les identifiants des parties en cours à l'état du jeu, qui est lui-même un dictionnaire.
    # Par exemple :
    # games["0"] = { "jeux" : "pendu", "secret" : "chaise", "score" : 4, "decouvert" : ["_", "_", "a", "i", "_", "e"]}
    # games["3"] = {"jeux" : "pom", "secret" : 42, "score" : 3}
    # L'état de chaque jeu est décrit par un dictionnaire, contenant au moins : 
    # - une clé "jeux" dont la valeur est le nom du jeu
    # - une clé "secret" dont la valeur est le secret à trouver, un mot au pendu, un nombre au POM.    
    # - une clé "score" qui représente la performance du joueur (plus
    #   le score est haut, moins c'est bon). Au PoM, c'est le nombre
    #   d'essaie, au pendu, le nombre de lettres essayées qui n'étaient
    #   pas dans le mot.

    # Attention, cette façon de gérer les parties en cours n'est pas
    # idéale. Je l'ai implémenté comme cela pour faciliter votre
    # compréhension du code. En pratique, il faudrait faire les choses
    # suivantes :

    # 1. Utiliser une classe générique "partie", avec une
    #    sous-classe par type de jeux. La classe générique exposerait
    #    l'interface minimale que le serveur à besoin de manipuler pour
    #    chaque jeu. La sous-classe implémenterait les différentes
    #    variations en fonction du jeu.

    # 2. La génération des identifiants des parties est facile à
    #    deviner : on utiliser la variable nb_games qui dit combien de
    #    partie ont été commencées depuis le lancement du serveur, et
    #    on ajoute 1 pour créer une nouvelle partie. Cela pose un
    #    problème de sécurité : un attaquant pourrait deviner un
    #    numéro de partie et interférer avec votre jeu. Il faudrait
    #    idéalement générer un identifiant unique et complexe, voir
    #    permettre au client de fixer un mot de passe.

    # 3. Une partie inactive (parce que le client a arrêté de jouer ou
    #    a fini sa partie) reste dans `games`. Il faudrait idéalement
    #    nettoyer le dictionnaire régulièrement. 
    
    games = {}
    nb_games = 0
        
    def send_HTML(self, message : str):
        """
        Envoie `message` au client, avec un type MIME text/html.

        Parameters
        ----------
        message : str
        """

        self.send_response(200)
        self.send_header('Content-type','text/html')
        self.end_headers()
        self.wfile.write(bytes(message, "utf-8"))
        return

    def goto_url(self, url : str):
        """
        Redirige le client vers l'url `url`.

        Parameters
        ----------
        url : str
        """
        self.send_response(303)
        self.send_header('Location', url)
        self.end_headers()

    def parse_url(self) -> dict:
        """
        Parse URL into possible actions and parameters
        """
        
        # Normalise l'URL; voir https://docs.python.org/3/library/urllib.parse.html
        url = uparse.urlparse(self.path)
        url_data = url.path.strip("/").split("/")

        r = {"action": "get"}

        if len(url_data) > 0:
            if url_data[0] == "start":
                r["action"] = "start"

            elif url_data[0] == "play" and len(url_data) > 1:
                r["action"] = "play"
                r["game_id"] = url_data[1]

            elif url_data[0] == "new" and len(url_data) > 1:
                r["action"] = "new"
                r["game_id"] = url_data[1]

        return r

        
    def do_GET(self):
        """Action lorsque le client fait une requête HTTP de type GET.

        - Si l'url (self.path) est de la forme /play/id, alors on
          vérifie que id est un identifiant correct de partie et on
          affiche la page correspondante. Sinon, on redirige vers la
          page d'accueil.
        
        - Sinon, on sert le fichier normalement comme dans un serveur
          HTTP. C'est utile par exemple si vous ajoutez une image dans
          vos fichiers HTML. Le navigateur va faire une requête `GET
          /img.png`, on veut que notre serveur envoie effectivement le
          fichier d'image.
        """
        # Parser l'URL
        url_data = self.parse_url()

        # L'URL est de la forme /play/game_id, on va jouer
        if url_data["action"] == "play":
            game_id = url_data["game_id"]
            # Vérifier que la partie existe pour éviter une erreur
            if game_id not in handler.games:
                self.goto_url("/")
                return
            # Sinon, on ouvre la page correspondant au jeu auquel
            # on joue et on remplace <REPONSE> par la dernière
            # réponse du serveur.
            with open(handler.games[game_id]["jeux"]+".html", encoding="utf-8") as f:
                msg = f.read()
                msg = msg.replace("<REPONSE>", handler.games[game_id]["reponse"])
                msg = msg.replace("<GAME_ID>", game_id)
                self.send_HTML(msg)
            return
        elif url_data["action"] in ["start", "err"]: 
            self.goto_url("/")
            return
        elif url_data["action"] == "new":
            game_id = url_data.get("game_id")

            if not game_id or game_id not in handler.games:
                self.goto_url("/")
                return

            jeux = handler.games[game_id]["jeux"]
            handler.games[game_id] = init_game(jeux)

            self.goto_url(f"/play/{game_id}")
            return

        else:
            # Dans les autres cas, on gère le GET normalement (permet
            # entre autre, d'envoyer les fichiers CSS, images etc.)
            super().do_GET()
            return
        
    def do_POST(self):
        """Action lorsque le client fait une requête HTTP de type POST.

        - Si l'url (self.path) est de la forme /play/id, alors on
          vérifie que id est un identifiant correct de partie. Si
          c'est le cas, on inspecte le données transmises par POST
          pour voir si un choix a été proposé. Si c'est le cas, on met
          à jour l'état du jeu et on renvoie la page
          correspondante. Sinon, on affiche la page comme avant. 
         
        - Si l'url est de la forme /start, on regarde les données POST
          pour voir si un jeu valide a été choisi. Si c'est le cas, on
          crée une nouvelle partie (dans la variable globale games) et
          on affiche la page correspondante.

        - Dans les autres cas, on affiche la page d'accueil.
        """
        
        # Parse l'url
        url_data = self.parse_url()

        # Récupère les données POST du formulaire sous forme de dictionnaire.
        content_length = int(self.headers['Content-Length'])
        post_data_byte = self.rfile.read(content_length)
        post_data = post_data_byte.decode('utf-8')
        
        # On construit un dictionnaire
        d = uparse.parse_qs(post_data)
        post_dict = {k : d[k][0] for k in d if len(d[k]) > 0}

        # Dans le cas où la requête POST est de type start
        # On est en train de créer un nouveau jeu
        if url_data["action"] == "start":
            # Le jeu choisi n'existe pas, on renvoie à l'accueil
            if "jeux" not in post_dict or post_dict["jeux"] not in ["pom", "pendu", "vof"]:
                self.goto_url("/")
                return
            else:
                # Le jeu choisi existe, on démarre une nouvelle partie
                jeux = post_dict["jeux"]

                # On ajoute 1 au nombre total de parties
                handler.nb_games += 1

                # On ajoute une entrée dans le dictionnaire qui gère
                # les parties On initialise l'état du jeux avec
                # init_game Par exemple, on va initialiser le score à
                # 0, le secret (un nombre pour PoM, un mot pour pendu)
                # etc.
                handler.games[str(handler.nb_games)] = init_game(jeux)

                # On redirige vers la page du jeu en cours : /play/game_id
                self.goto_url(f"/play/{handler.nb_games}")
                return

        # Dans le cas où on est sur un page /play/game_id, on va gérer le jeu
        
        elif url_data["action"] == "play" and "choix" in post_dict:
            # ici, tout est défini correctement, on récupère donc l'identifiant de la partie
            game_id = url_data["game_id"]
            
            # Vérifier que la partie existe pour éviter une erreur
            if game_id not in handler.games:
                self.goto_url("/")
                return

            # On met l'état de la partie à jour en fonction du choix du joueur et de l'état actuel
            update_state(post_dict["choix"], handler.games[game_id])

            if "prochaine_question" in handler.games[game_id]:
                 handler.games[game_id]["secret"] = handler.games[game_id].pop("prochaine_question")

            # On ouvre la page HTML correspondant au jeu donné
            # (convention : elle s'appelle jeu.html où jeu est le
            # nom du jeu). 
            with open(handler.games[game_id]["jeux"]+".html", encoding="utf-8") as f:
                    msg = f.read()
                    msg = msg.replace("<REPONSE>", handler.games[game_id]["reponse"])
                    msg = msg.replace("<GAME_ID>", game_id)   #  AJOUT ICI
                    self.send_HTML(msg)
                    return
        elif url_data["action"] == "err": # on ne sait pas parser l'URL.
            self.goto_url("/")
            return
        
        
        elif url_data["action"] == "new":
            game_id = url_data.get("game_id")

            if not game_id or game_id not in handler.games:
                self.goto_url("/")
                return

            jeux = handler.games[game_id]["jeux"]
            handler.games[game_id] = init_game(jeux)

            self.goto_url(f"/play/{game_id}")
            return

        else: # dans les autres cas, on reste sur la page.
            # Dans les autres cas, on reste sur la page courante et on ne fait rien.
            self.goto_url(self.path)
            return
            
def init_game(jeux : str):
    """

    Retourne un dictionnaire représentant l'état initial du
    jeu. Initialise le secret, le score, et possiblement d'autres
    variables en fonction du jeu.
-
    """
    # Initialise le score, le nom du jeu
    d = {"score" : 0, "jeux" : jeux}
    # Cas Plus ou Moins
    if jeux == "pom":
        # on choisit le secret entre 0 et 100
        d["secret"] = randint(0,100)
        # on prépare la première réponse du serveur, avant le premier coup.
        d["reponse"] = "<p>Il faut trouver un nombre entre 0 et 100.</p>"
        d["score"] = 0 
        return d
    if jeux == "pendu":
        # Cas du pendu, on choisit un mot au hasard dans une liste. 
        with open("mots.txt", encoding="utf-8") as f:
            w = choice(f.readlines()).strip()
        # On choisit le secret
        d["secret"] = w
        print(w)
        d["score"] = 0
        # On prépare le mot caché, on mettra à jour au fur et à mesure que les lettres sont découvertes.
        d["decouvert"] = ["_"]*len(w)
        # Réponse initial, on donne la forme du mot, le nombre d'essais.
        d["reponse"] = f"<p>Il faut trouver le mot secret !</p><p>{' '.join(d['decouvert'])}</p><p>Il vous reste 10 essais.</p>"
        # décommenter si on veut voir la solution du pendu dans le terminal pour debugger.
        # print(w) 
        d["vies"] = 10  

        d["reponse"] =(
        f"<p>Il faut trouver le mot secret !</p>"
        f"<p>{' '.join(d['decouvert'])}</p>"
        f"<p>Il vous reste {d['vies']} essais.</p>")
        return d
    if jeux == "vof":
        questions = []
        # Lecture des questions depuis le fichier questions.txt
        with open("questions.txt", "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                if "|" in line:
                    q, r = line.strip().split("|")
                    questions.append({"question": q, "reponse": r.lower()})
    
        q = choice(questions)
        d["secret"] = q   # stocke question + bonne réponse
        d["score"] = 0
        d["reponse"] = f"<p>{q['question']}</p>"  # première question affichée
        return d


def update_state(c : str, etat : dict):
    """
    Mise à jour de l'état du jeu ; Modifie etat en fonction du choix c.

    Retourne `False` si le jeu est inconnu.
    """
    if etat["jeux"] == "pom":
        update_pom(c,etat)
        return True
    elif etat["jeux"] == "pendu":
        update_pendu(c,etat)
        return True 
    elif etat["jeux"] == "vof":
        update_vof(c,etat)
        return True
    else:
        return False


def update_pom(c: str, etat: dict):
    """
    Mise à jour pour Plus ou Moins avec score.
    +5 points quand le joueur trouve le nombre.
    Score toujours affiché.
    """

    try:
        x = int(c)

        if x < etat["secret"]:
            msg = "C'est plus."
        
        elif x > etat["secret"]:
            msg = "C'est moins."
        
        else:
            # Bonne réponse
            etat["score"] += 5
            msg = "Bravo ! Tu as trouvé le nombre !"

            # Nouveau nombre pour continuer à jouer
            etat["secret"] = randint(0, 100)

        # Réponse affichée (comme VOF)
        etat["reponse"] = (
            f"<p>{msg}</p>"
            f"<p>SCORE : {etat['score']}</p>"
        )

    except ValueError:
        etat["reponse"] = (
            f"<p>Veuillez entrer un nombre.</p>"
            f"<p>SCORE : {etat['score']}</p>"
        )





def update_pendu(c: str, etat: dict):
    """
    Mise à jour de l'état du jeu de pendu. Le choix doit être une
    lettre unique. Le score est incrémenté seulement si la lettre est
    absente. Les lettres présentes sont découvertes dans la variable
    `etat["decouvert"]`.
    """
    if "_" not in etat["decouvert"]:
         return

    comment = ""
    c = c.lower()

    if len(c) == 1 and "a" <= c <= "z":
        if c in etat["secret"]:
            for k, d in enumerate(etat["secret"]):
                if d.lower() == c:
                    etat["decouvert"][k] = d

            # Vérifie si le mot est entièrement découvert
            if "_" not in etat["decouvert"]:
                # joueur a trouvé le mot : ajoute 5 points
                etat["score"] = etat.get("score", 0) + 5
                comment = f"Bravo ! Vous avez trouvé le mot !"
            else:
                comment = f"Bien joué, continuez !"
        else:
            etat["vies"]-= 1
            comment = f"La lettre {c} n'est pas dans le mot."
    else:
        comment = "Veuillez choisir une lettre."
    if etat["vies"] == 0:
        comment += f" Partie terminée ! Le mot était : {etat['secret']}"
        

    mot_partiel = ' '.join(etat['decouvert']) if etat["vies"] > 0 else etat['secret']

    etat["reponse"] = (
        f"<p>{comment}</p>"
        f"<p>{mot_partiel}</p>"
        f"<p>SCORE : {etat.get('score', 0)}</p>"
        f"<p>Il vous reste {etat.get('vies', 0)} essais.</p>"
    )


from random import choice

def update_vof(c: str, etat: dict):


    question = etat["secret"]

    reponse_joueur = c.strip().lower()
    reponse_correcte = question["reponse"].strip().lower()

    if reponse_joueur == reponse_correcte:
        etat["score"] += 5
        msg = "Bonne réponse !"
    else:
        etat["score"] -= 2
        msg = f"Mauvaise réponse ! La bonne réponse était : {question['reponse'].capitalize()}."

    questions = []
    with open("questions.txt", "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            if "|" in line:
                q, r = line.strip().split("|", 1)
                questions.append({
                    "question": q,
                    "reponse": r.strip().lower()
                })

    prochaine_question = choice(questions)
    etat["secret"] = prochaine_question

    etat["reponse"] = (
        f"<p>{msg}</p>"
        f"<p><b>Nouvelle question :</b> {prochaine_question['question']}</p>"
        f"<p>SCORE : {etat['score']}</p>"
    )

import os

def main():
    port = int(os.environ.get("PORT", 8000))
    with http.server.HTTPServer(('', port), handler) as server:
        print(f"Serveur lancé sur le port {port}")
        server.serve_forever()

if __name__ == "__main__":
    main()