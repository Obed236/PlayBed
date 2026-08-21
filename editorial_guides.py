EDITORIAL_GUIDES = {
    "mieux-jouer-au-pendu": {
        "title": "Comment progresser au Pendu",
        "description": "Une méthode complète pour choisir de meilleures lettres, exploiter la forme des mots et réduire les erreurs au Pendu.",
        "read_time": "7 min",
        "game": "pendu",
        "sections": [
            ("Commencer par les lettres les plus utiles", [
                "Au Pendu, toutes les lettres n’apportent pas la même quantité d’information. Les voyelles courantes comme E, A, I ou O sont souvent de bons premiers choix parce qu’elles permettent de révéler rapidement la structure générale du mot.",
                "Les consonnes fréquentes comme S, R, N, T ou L deviennent ensuite très utiles pour préciser la forme du mot. L’objectif n’est pas de réciter une liste fixe, mais de choisir des lettres qui ont de bonnes chances d’apparaître tout en donnant un maximum d’indices."
            ]),
            ("Lire le motif plutôt que jouer au hasard", [
                "La longueur du mot, les espaces déjà révélés et les lettres répétées forment un motif. Plus la partie avance, plus ce motif devient important. Un mot de huit lettres contenant deux E n’offre pas les mêmes possibilités qu’un mot court sans voyelle révélée.",
                "Au lieu de proposer immédiatement une nouvelle lettre, essaie de construire mentalement plusieurs mots compatibles avec ce que tu vois. Si plusieurs hypothèses partagent la même lettre, cette lettre devient un choix intéressant."
            ]),
            ("Utiliser les terminaisons et les familles de mots", [
                "Certaines positions donnent des indices particuliers. Une suite de lettres en fin de mot peut faire penser à une terminaison courante, tandis qu’un début déjà révélé peut évoquer un préfixe connu.",
                "Il faut cependant éviter de s’enfermer trop tôt dans une seule hypothèse. Une bonne stratégie consiste à garder deux ou trois possibilités en tête et à choisir la lettre qui permet de les départager."
            ]),
            ("Garder les lettres rares pour le bon moment", [
                "Les lettres comme W, K, X ou Z peuvent être décisives, mais elles sont rarement les meilleurs choix au début d’une partie. Les jouer trop tôt peut coûter une vie sans apporter beaucoup d’information.",
                "Elles deviennent plus pertinentes lorsque le motif du mot les rend plausibles. Plus tu disposes d’indices, plus tu peux te permettre un choix précis et moins fréquent."
            ]),
            ("Transformer chaque erreur en information", [
                "Une mauvaise lettre n’est pas seulement une vie perdue : elle élimine aussi toute une famille d’hypothèses. Si une lettre importante n’est pas présente, certains mots deviennent immédiatement impossibles.",
                "Les meilleurs joueurs ne cherchent donc pas à éviter toute erreur à n’importe quel prix. Ils essaient plutôt de faire des choix qui restent utiles, même lorsqu’ils sont faux."
            ]),
            ("Améliorer son score sur PlayBed", [
                "Sur PlayBed, une victoire au Pendu rapporte une base de points complétée par un bonus lié aux vies restantes. Gagner rapidement et proprement est donc plus intéressant que trouver le mot au dernier moment.",
                "Pour progresser, compare surtout tes propres parties : nombre d’erreurs, ordre des lettres choisies et moment où le mot devient identifiable. Cette analyse simple permet souvent d’améliorer ses décisions dès les parties suivantes."
            ]),
        ],
    },
    "dichotomie-plus-ou-moins": {
        "title": "Plus ou Moins : comprendre la stratégie de la dichotomie",
        "description": "Une explication pas à pas de la recherche dichotomique et de la manière de l’utiliser pour trouver le nombre secret avec très peu d’essais.",
        "read_time": "7 min",
        "game": "pom",
        "sections": [
            ("Réduire l’espace de recherche", [
                "Dans Plus ou Moins, le nombre secret est compris entre 0 et 100. Au départ, 101 valeurs sont donc possibles. La stratégie la plus efficace consiste à réduire cet ensemble de possibilités le plus vite possible.",
                "Si tu commences autour de 50, une seule réponse permet d’éliminer environ la moitié des nombres. C’est beaucoup plus efficace que de tester 1, puis 2, puis 3, ou de choisir des valeurs au hasard."
            ]),
            ("Recalculer le milieu à chaque étape", [
                "Supposons que tu proposes 50 et que PlayBed réponde « plus ». Le nombre se trouve alors entre 51 et 100. Le milieu de ce nouvel intervalle se situe autour de 75 : c’est donc un excellent deuxième choix.",
                "Si la réponse est ensuite « moins », l’intervalle devient approximativement 51 à 74. Tu recommences exactement le même raisonnement avec le milieu de cette nouvelle zone."
            ]),
            ("Pourquoi cette méthode est rapide", [
                "À chaque bonne étape, la dichotomie divise presque par deux le nombre de possibilités restantes. Après quelques essais seulement, il ne reste plus qu’un petit nombre de valeurs possibles.",
                "Cette idée explique pourquoi certaines recherches informatiques sont très rapides : au lieu de parcourir tous les éléments un par un, elles éliminent de grandes portions de données à chaque comparaison."
            ]),
            ("Le lien avec l’algorithmique", [
                "La recherche dichotomique est une notion classique en algorithmique. Pour l’utiliser sur une liste triée, on regarde l’élément du milieu, on compare la valeur recherchée, puis on conserve seulement la moitié pertinente de la liste.",
                "Le jeu Plus ou Moins permet donc d’expérimenter une idée informatique sans écrire une seule ligne de code. Chaque réponse « plus » ou « moins » joue le rôle d’une comparaison dans l’algorithme."
            ]),
            ("Les erreurs courantes", [
                "Une erreur fréquente consiste à choisir une valeur trop proche de l’une des bornes. Par exemple, tester 90 alors que l’intervalle est encore 0 à 100 ne coupe pas l’espace de recherche de manière équilibrée.",
                "Une autre erreur consiste à oublier la nouvelle borne après une réponse. Garde toujours en tête le plus petit et le plus grand nombre encore possibles avant de calculer ton prochain milieu."
            ]),
            ("Optimiser son score sur PlayBed", [
                "Sur PlayBed, le score diminue avec le nombre d’essais. Une méthode régulière est donc directement récompensée. L’objectif n’est pas seulement de trouver le nombre, mais de le trouver en utilisant chaque indice efficacement.",
                "Essaie de refaire plusieurs parties en suivant strictement la dichotomie. Tu constateras rapidement que tes résultats deviennent plus stables et que les longues séries de tentatives deviennent rares."
            ]),
        ],
    },
    "reussir-memory": {
        "title": "5 techniques pour mieux réussir au Memory",
        "description": "Une méthode détaillée pour mémoriser les cartes, réduire les coups inutiles et améliorer progressivement ses performances au Memory.",
        "read_time": "7 min",
        "game": "memory",
        "sections": [
            ("1. Balayer la grille méthodiquement", [
                "Jouer totalement au hasard oblige ton cerveau à retenir des cartes dispersées sans organisation. Une méthode plus efficace consiste à explorer progressivement la grille, par ligne, par colonne ou par zone.",
                "Ce parcours régulier crée des repères spatiaux. Il devient plus facile de se rappeler qu’un symbole se trouvait dans le coin supérieur droit ou au milieu de la deuxième ligne."
            ]),
            ("2. Associer le symbole à une position", [
                "Voir un symbole ne suffit pas : il faut l’associer immédiatement à un emplacement. Essaie de formuler mentalement une petite étiquette comme « fusée, première ligne à gauche » ou « ballon, centre droit ».",
                "Cette double information, symbole plus position, aide à reconstruire plus vite la grille lorsque la paire correspondante apparaît quelques tours plus tard."
            ]),
            ("3. Exploiter immédiatement une paire connue", [
                "Lorsque la première carte retournée correspond à un symbole que tu as déjà vu, ton deuxième choix devrait presque toujours être la position mémorisée de sa paire.",
                "Retarder volontairement une paire connue augmente le risque d’oublier sa position et ajoute des coups inutiles. Une information fraîche vaut donc mieux lorsqu’elle est utilisée immédiatement."
            ]),
            ("4. Ne pas confondre vitesse et précipitation", [
                "Une partie rapide n’est pas forcément une bonne partie si elle comporte beaucoup de mauvaises associations. La précipitation peut faire oublier des informations vues quelques secondes auparavant.",
                "Prends juste assez de temps pour enregistrer chaque nouvelle carte. Une courte pause mentale peut éviter plusieurs coups supplémentaires plus tard."
            ]),
            ("5. Utiliser les erreurs comme une carte mentale", [
                "Quand deux cartes ne correspondent pas, tu viens malgré tout d’obtenir deux informations nouvelles. Essaie de considérer chaque erreur comme l’ajout de deux points sur une carte mentale de la grille.",
                "À mesure que la partie avance, le nombre de cartes inconnues diminue. La fin de partie devient alors moins dépendante du hasard et davantage de la qualité de ta mémoire accumulée."
            ]),
            ("Comprendre le score PlayBed", [
                "Dans Memory sur PlayBed, le nombre de coups et le temps participent au calcul du score. La meilleure stratégie consiste donc à trouver un équilibre entre précision et rapidité.",
                "Pour progresser, observe tes propres tendances : fais-tu beaucoup de coups mais très vite, ou peu de coups mais lentement ? Cette comparaison permet de savoir quel aspect travailler en priorité."
            ]),
        ],
    },
    "progresser-en-culture-generale": {
        "title": "Progresser en culture générale avec les quiz",
        "description": "Comment transformer Vrai ou Faux et Quiz Express en petits exercices d’apprentissage plutôt qu’en simples jeux de hasard.",
        "read_time": "8 min",
        "game": "quiz",
        "sections": [
            ("Transformer une erreur en information", [
                "Une mauvaise réponse devient utile lorsqu’elle laisse une trace. Après une partie, essaie de retenir les deux ou trois questions qui t’ont le plus surpris au lieu de te concentrer uniquement sur le score final.",
                "Le but n’est pas de mémoriser mécaniquement toutes les réponses, mais de comprendre ce qui t’a conduit à l’erreur : une confusion de dates, un mot mal lu, une association trop rapide ou un manque de connaissance sur le sujet."
            ]),
            ("Éliminer avant de choisir", [
                "Dans un QCM, tu peux souvent progresser même sans connaître immédiatement la réponse. Commence par éliminer les propositions manifestement incompatibles avec la question.",
                "Réduire quatre possibilités à deux transforme déjà la situation. Cette habitude développe le raisonnement et limite les choix complètement aléatoires."
            ]),
            ("Se méfier des formulations absolues", [
                "Dans un Vrai ou Faux, les mots comme « toujours », « jamais », « uniquement » ou « tous » méritent une attention particulière. Une seule exception suffit parfois à rendre une affirmation fausse.",
                "Cela ne signifie pas qu’une phrase absolue est forcément incorrecte. L’idée est simplement de ralentir et de vérifier mentalement si l’affirmation laisse réellement aucune place à une exception."
            ]),
            ("Jouer régulièrement plutôt que longtemps", [
                "Des sessions courtes et répétées sont souvent plus faciles à intégrer dans une routine qu’une longue session occasionnelle. Revenir régulièrement permet aussi de rencontrer des questions différentes et de réactiver des connaissances anciennes.",
                "Tu peux par exemple te fixer un objectif simple : une partie de Quiz Express ou de Vrai ou Faux, puis noter mentalement un fait nouveau appris pendant la session."
            ]),
            ("Relier les connaissances entre elles", [
                "La culture générale devient plus solide lorsque les informations ne restent pas isolées. Une question sur un pays peut être reliée à sa géographie, son histoire, sa langue ou un événement connu.",
                "Plus tu crées de liens entre les notions, plus il devient facile de retrouver l’information au bon moment. Le quiz sert alors de point de départ à un réseau de connaissances plus large."
            ]),
            ("Mesurer ses progrès autrement que par un seul score", [
                "Un score parfait est satisfaisant, mais ce n’est pas le seul indicateur intéressant. Tu peux aussi observer si certaines erreurs disparaissent, si tu hésites moins sur certains thèmes ou si tu réussis mieux à éliminer les mauvaises réponses.",
                "Sur PlayBed, les parties sont courtes. Cette répétition permet de comparer facilement tes performances et de voir si tes connaissances deviennent plus stables avec le temps."
            ]),
        ],
    },
    "comprendre-les-scores-playbed": {
        "title": "Comprendre les scores et le classement PlayBed",
        "description": "Comment les points sont calculés selon les jeux, ce que mesure le classement et comment suivre sa progression de manière utile.",
        "read_time": "7 min",
        "game": None,
        "sections": [
            ("Des règles différentes selon le jeu", [
                "PlayBed ne calcule pas tous les scores de la même manière, car chaque mini-jeu met en avant une compétence différente. Les quiz récompensent les bonnes réponses, le Pendu tient compte des vies restantes, Plus ou Moins du nombre d’essais et Memory combine efficacité et rapidité.",
                "Cette différence évite de réduire toutes les parties à un simple compteur identique. Un bon résultat doit refléter ce qui constitue réellement une bonne performance dans le jeu concerné."
            ]),
            ("Le classement général", [
                "Les points obtenus à la fin des parties sont additionnés par pseudo. Le classement général récompense donc à la fois la régularité et la performance.",
                "Un joueur très fort sur un seul jeu peut être bien classé, mais un joueur qui obtient régulièrement de bons résultats sur plusieurs jeux peut également progresser grâce à l’accumulation de points."
            ]),
            ("Les classements par période", [
                "PlayBed propose aussi des classements liés à différentes périodes. Cela permet de comparer les performances récentes sans que les joueurs présents depuis longtemps gardent automatiquement un avantage définitif.",
                "Un classement quotidien, hebdomadaire ou mensuel crée de nouveaux objectifs. Même si le classement général paraît difficile à rattraper, une nouvelle période permet de repartir sur une compétition plus courte."
            ]),
            ("Pourquoi le nombre de parties compte", [
                "Accumuler les parties peut augmenter le total de points, mais jouer beaucoup ne garantit pas une bonne progression. Une série de faibles performances peut révéler qu’une stratégie mérite d’être améliorée.",
                "Le meilleur usage du classement consiste donc à l’accompagner d’objectifs personnels : améliorer son meilleur score, réussir un sans-faute ou terminer un jeu avec moins d’erreurs."
            ]),
            ("Se comparer sans perdre l’objectif principal", [
                "Un classement est un outil de motivation, pas une mesure absolue de niveau. Les joueurs n’ont pas tous le même temps de jeu, les mêmes habitudes ni les mêmes forces.",
                "Comparer ton score actuel à tes propres performances précédentes reste souvent la manière la plus utile de constater une progression réelle."
            ]),
            ("Comprendre la persistance des scores", [
                "Les scores enregistrés par PlayBed sont associés au pseudo choisi et servent à alimenter les classements et statistiques. La plateforme n’impose pas de création de compte pour jouer.",
                "Il est donc important de choisir un pseudo qui ne contient pas de données personnelles sensibles, puisqu’il peut apparaître publiquement dans un classement."
            ]),
        ],
    },
    "comment-fonctionne-un-mini-jeu-web": {
        "title": "Comment fonctionne un mini-jeu web comme ceux de PlayBed ?",
        "description": "Du navigateur au serveur : une introduction simple au fonctionnement technique d’un mini-jeu en ligne, des routes aux sessions et aux scores.",
        "read_time": "8 min",
        "game": None,
        "sections": [
            ("Le navigateur affiche l’interface", [
                "Quand tu ouvres PlayBed, ton navigateur reçoit du HTML pour la structure de la page, du CSS pour l’apparence et du JavaScript pour certaines interactions dynamiques. Ces trois technologies jouent des rôles complémentaires.",
                "Le HTML décrit les éléments visibles, le CSS organise leur présentation et le JavaScript peut réagir à des actions sans recharger toute la page, comme dans le Memory."
            ]),
            ("Le serveur gère la logique", [
                "Une partie de la logique de PlayBed est exécutée côté serveur avec Python et Flask. Lorsqu’une route est appelée, le serveur décide quelle page afficher, quelles données utiliser et quelle réponse renvoyer au navigateur.",
                "Dans un jeu comme Plus ou Moins, le serveur peut conserver le nombre secret et comparer les propositions successives du joueur avant de répondre « plus », « moins » ou « trouvé »."
            ]),
            ("Les routes relient les URL aux fonctions", [
                "Une application web associe des URL à des fonctions. Une route peut afficher la page d’accueil, une autre lancer une partie, une autre montrer un classement ou recevoir un score.",
                "Cette organisation rend le projet plus lisible : chaque adresse correspond à un rôle clair dans l’application."
            ]),
            ("Les sessions conservent un état temporaire", [
                "Le web est naturellement composé de requêtes séparées. Pour qu’une partie puisse continuer d’un écran au suivant, l’application doit conserver certaines informations temporaires.",
                "PlayBed utilise notamment une session pour retenir le pseudo et l’état de certains jeux. Cela permet de continuer une partie sans créer obligatoirement un compte utilisateur complet."
            ]),
            ("La base de données conserve les scores", [
                "Lorsqu’une partie se termine, certaines informations comme le pseudo, le jeu, les points et la date peuvent être enregistrées dans une base de données. Ces données servent ensuite à construire les classements et statistiques.",
                "Une base de données est différente d’une session : la session est surtout utile pour l’état temporaire de navigation, alors que la base sert à conserver des informations plus durablement."
            ]),
            ("Pourquoi séparer front-end et back-end", [
                "Le navigateur est très pratique pour l’interface et les interactions visuelles, tandis que le serveur est mieux placé pour protéger certaines règles, centraliser les scores ou travailler avec une base de données.",
                "Un projet comme PlayBed combine donc plusieurs couches. Comprendre cette séparation permet de mieux voir comment un petit jeu peut devenir une véritable application web publique."
            ]),
        ],
    },
    "entrainer-sa-memoire-avec-des-jeux": {
        "title": "Comment entraîner sa mémoire avec des jeux courts",
        "description": "Des méthodes simples pour utiliser les jeux de mémoire et de réflexion comme exercices réguliers d’attention, de rappel et d’organisation mentale.",
        "read_time": "7 min",
        "game": "memory",
        "sections": [
            ("La mémoire n’est pas une seule capacité", [
                "Dans un jeu, plusieurs mécanismes peuvent être sollicités en même temps : retenir une position pendant quelques secondes, reconnaître un symbole déjà vu ou retrouver une information apprise lors d’une partie précédente.",
                "Le Memory travaille surtout la mémoire visuelle et spatiale à court terme, tandis que les quiz font davantage appel au rappel de connaissances."
            ]),
            ("Créer des repères", [
                "Une information isolée est plus difficile à retrouver qu’une information reliée à un contexte. Dans une grille, associer une carte à une zone précise crée un repère spatial.",
                "Dans un quiz, relier une réponse à une histoire, une image mentale ou une autre connaissance joue un rôle similaire : le cerveau dispose de plusieurs chemins pour retrouver l’information."
            ]),
            ("Répéter sans jouer mécaniquement", [
                "Répéter une activité peut aider, mais la répétition devient plus utile lorsqu’elle reste attentive. Refaire dix fois le même geste sans réfléchir apporte moins que quelques parties où tu observes réellement tes erreurs.",
                "Après chaque session, identifie un point précis à améliorer : une zone de la grille que tu oublies souvent, une catégorie de questions difficile ou une tendance à répondre trop vite."
            ]),
            ("Espacer les sessions", [
                "Des sessions courtes réparties dans le temps peuvent être plus faciles à maintenir qu’une longue session unique. Revenir plus tard oblige aussi le cerveau à reconstruire l’information plutôt qu’à simplement la garder active quelques secondes.",
                "Sur une plateforme de mini-jeux, quelques minutes régulières suffisent pour créer cette habitude sans transformer l’exercice en contrainte."
            ]),
            ("Protéger l’attention", [
                "La mémoire fonctionne moins bien lorsque l’attention est constamment interrompue. Pour une partie courte, réduire les distractions pendant quelques minutes peut déjà améliorer les performances.",
                "Cela permet aussi de distinguer un problème de mémoire d’un simple manque d’attention au moment où l’information a été présentée."
            ]),
            ("Suivre sa progression", [
                "Une amélioration ne se résume pas à un record. Tu peux observer une baisse du nombre de coups au Memory, une meilleure régularité ou moins d’oublis sur des cartes déjà vues.",
                "Ces petits indicateurs sont utiles parce qu’ils montrent comment ta stratégie change, pas seulement si une partie particulière s’est bien passée."
            ]),
        ],
    },
    "quiz-esprit-critique-et-deduction": {
        "title": "Quiz, esprit critique et déduction : mieux raisonner avant de répondre",
        "description": "Une méthode pour analyser une question, détecter les pièges de formulation et utiliser la déduction lorsque la réponse n’est pas immédiatement connue.",
        "read_time": "8 min",
        "game": "quiz",
        "sections": [
            ("Lire exactement ce qui est demandé", [
                "Beaucoup d’erreurs de quiz viennent d’une lecture trop rapide. Une question peut porter sur une date, une première occurrence, une capitale, une exception ou une définition précise.",
                "Avant de regarder les réponses, reformule mentalement la question en une phrase simple. Cela réduit le risque de répondre à une question légèrement différente de celle qui est réellement posée."
            ]),
            ("Classer les réponses par plausibilité", [
                "Lorsque tu ne connais pas la réponse avec certitude, toutes les propositions ne se valent pas forcément. Certaines peuvent être incompatibles avec la période, le lieu ou la catégorie évoquée.",
                "Commence par éliminer ce qui paraît impossible, puis compare les choix restants. Cette démarche transforme une devinette en petit problème de raisonnement."
            ]),
            ("Détecter les mots qui changent le sens", [
                "Des mots comme « premier », « principal », « uniquement », « avant », « après » ou « jamais » peuvent complètement changer la bonne réponse.",
                "Ils méritent donc d’être repérés avant de répondre. Dans un Vrai ou Faux, une seule nuance de formulation peut suffire à transformer une affirmation globalement plausible en affirmation incorrecte."
            ]),
            ("Ne pas confondre familiarité et connaissance", [
                "Une réponse peut sembler correcte simplement parce que son nom est plus familier. C’est un piège classique : reconnaître un terme n’est pas la même chose que savoir qu’il répond à la question.",
                "Lorsque deux options te semblent possibles, cherche un argument précis en faveur de l’une plutôt que de choisir automatiquement celle que tu connais le mieux."
            ]),
            ("Accepter l’incertitude", [
                "Il est normal de ne pas connaître toutes les réponses. L’objectif d’un quiz n’est pas seulement de confirmer ce que tu sais déjà, mais aussi de rencontrer des informations nouvelles.",
                "Une erreur bien comprise est souvent plus utile qu’une bonne réponse obtenue au hasard. Après la correction, essaie donc d’identifier ce qui permettait de trouver ou de retenir la bonne réponse."
            ]),
            ("Construire une méthode répétable", [
                "Une bonne routine peut tenir en quelques étapes : lire précisément, repérer les mots importants, éliminer les options impossibles, comparer les restantes, puis répondre.",
                "Avec l’habitude, cette méthode devient rapide. Elle améliore non seulement les scores de quiz, mais aussi la manière d’aborder des questions à choix multiples dans d’autres contextes."
            ]),
        ],
    },
}
