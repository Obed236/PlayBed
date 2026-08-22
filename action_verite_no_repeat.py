import re
from datetime import datetime, timedelta, timezone
from random import choice

from flask import request, session

import action_verite_preferences as preferences


USED_PROMPT_TTL_HOURS = 24
LOCAL_USED_KEY = "av_local_used_prompts"

# Niveau Très osé : volontairement très direct et très intime, mais sans
# description sexuelle graphique, sans danger et sans contact imposé.
STRONG_VERY_DARING_TRUTHS = [
    "As-tu déjà eu une relation d’un soir ?",
    "As-tu déjà eu une relation intime avec quelqu’un rencontré le jour même ?",
    "As-tu déjà eu une relation seulement physique sans vouloir être en couple ?",
    "As-tu déjà menti sur ton expérience intime ?",
    "As-tu déjà menti sur le nombre de personnes avec qui tu as eu une relation intime ?",
    "As-tu déjà caché à quelqu’un que tu avais une relation intime avec une autre personne ?",
    "As-tu déjà eu une relation intime avec quelqu’un alors que tu étais déjà en couple ?",
    "As-tu déjà eu une relation intime avec quelqu’un qui était déjà en couple ?",
    "As-tu déjà caché une infidélité ?",
    "As-tu déjà été infidèle sans l’avouer ?",
    "As-tu déjà menti en disant que tu étais célibataire alors que ce n’était pas vrai ?",
    "As-tu déjà eu envie d’une relation intime avec quelqu’un de ce groupe ?",
    "Si tu devais choisir une personne du groupe pour passer une nuit avec elle, qui choisirais-tu ?",
    "Qui dans ce groupe t’attire le plus sexuellement ?",
    "As-tu déjà imaginé passer une nuit avec quelqu’un présent dans ce groupe ?",
    "As-tu déjà eu une attirance sexuelle pour un ami très proche ?",
    "As-tu déjà eu envie d’une relation uniquement physique avec un ami ou une amie ?",
    "As-tu déjà eu une aventure avec un ami ou une amie ?",
    "As-tu déjà eu une relation intime avec l’ex d’un ami ou d’une amie ?",
    "As-tu déjà eu une relation intime avec quelqu’un que tes proches n’auraient jamais imaginé ?",
    "As-tu déjà eu une relation intime avec quelqu’un que tu ne voulais surtout pas présenter à tes proches ?",
    "As-tu déjà regretté d’avoir passé la nuit avec quelqu’un ?",
    "As-tu déjà coupé tout contact avec quelqu’un juste après une relation intime ?",
    "As-tu déjà eu peur que quelqu’un découvre avec qui tu avais passé la nuit ?",
    "As-tu déjà menti sur l’endroit où tu avais passé la nuit ?",
    "As-tu déjà envoyé une photo intime à quelqu’un puis regretté ?",
    "As-tu déjà reçu une photo intime que tu ne t’attendais pas à recevoir ?",
    "As-tu déjà envoyé un message très intime puis regretté juste après ?",
    "As-tu déjà supprimé une conversation parce que tu ne voulais pas que quelqu’un la voie ?",
    "As-tu déjà caché une conversation intime à ton partenaire ?",
    "As-tu déjà menti à ton partenaire sur ton attirance pour une autre personne ?",
    "As-tu déjà voulu recommencer avec un ex uniquement parce que l’attirance était encore forte ?",
    "As-tu déjà accepté un rendez-vous en sachant que tu ne voulais rien de sérieux ?",
    "As-tu déjà fait croire à quelqu’un que tu voulais une relation sérieuse alors que ce n’était pas le cas ?",
    "As-tu déjà continué à voir quelqu’un uniquement parce que l’attirance physique était forte ?",
    "As-tu déjà eu des sentiments pour une personne avec qui la relation devait rester seulement physique ?",
    "As-tu déjà eu une relation seulement physique avec quelqu’un qui voulait plus que toi ?",
    "As-tu déjà voulu une relation seulement physique avec quelqu’un qui était amoureux de toi ?",
    "As-tu déjà embrassé deux personnes différentes le même jour ?",
    "As-tu déjà embrassé quelqu’un en sachant que tu allais le regretter ?",
    "As-tu déjà embrassé quelqu’un uniquement par attirance, sans aucun sentiment ?",
    "As-tu déjà été attiré par le partenaire d’un ami ?",
    "As-tu déjà été attiré par quelqu’un avec qui tu savais que tu ne devais rien tenter ?",
    "Quelle personne du groupe te mettrait le plus mal à l’aise si elle te disait qu’elle te désire ?",
    "Qui du groupe pourrait le plus facilement te faire craquer si vous étiez seuls tous les deux ?",
    "Quelle personne du groupe correspond le plus à ton type physiquement ?",
    "Avec qui dans ce groupe pourrais-tu le plus facilement imaginer une relation seulement physique ?",
    "Quelle est la chose la plus difficile à avouer sur ta vie intime ?",
    "Quel est le plus gros secret de ta vie intime que tu acceptes de raconter ?",
    "Quelle question sur ta vie intime te gênerait le plus si on te la posait maintenant ?",
    "Quelle est la décision la plus risquée que tu aies prise uniquement à cause de l’attirance ?",
    "As-tu déjà regretté de ne pas avoir tenté quelque chose avec une personne qui te plaisait énormément ?",
    "As-tu déjà eu une attirance très forte pour quelqu’un que tu détestais pourtant ?",
    "As-tu déjà caché à tes proches la vraie raison pour laquelle tu voyais quelqu’un ?",
    "As-tu déjà menti pour pouvoir passer la nuit avec quelqu’un ?",
    "As-tu déjà eu peur que ton partenaire lise une conversation avec une autre personne ?",
    "As-tu déjà gardé le contact avec quelqu’un uniquement parce que tu étais encore attiré physiquement ?",
    "As-tu déjà comparé deux personnes avec qui tu avais eu une relation intime ?",
    "As-tu déjà été jaloux d’une personne avec qui tu n’étais même pas en couple ?",
    "As-tu déjà voulu récupérer quelqu’un uniquement parce que tu ne supportais pas de le voir avec une autre personne ?",
]

STRONG_VERY_DARING_DARES = [
    "Dis quelle personne du groupe t’attire le plus sexuellement.",
    "Dis avec quelle personne du groupe tu pourrais le plus facilement imaginer une relation d’un soir.",
    "Choisis une personne volontaire et dis-lui franchement si tu pourrais imaginer passer une nuit avec elle.",
    "Choisis une personne volontaire et dis-lui ce qui t’attire le plus physiquement chez elle.",
    "Dis quelle personne du groupe correspond le plus à ton type physiquement.",
    "Dis qui du groupe pourrait le plus facilement te faire craquer si vous étiez seuls tous les deux.",
    "Dis quelle personne du groupe te mettrait le plus mal à l’aise si elle t’avouait qu’elle te désire.",
    "Dis avec quelle personne du groupe tu pourrais le plus facilement imaginer une relation seulement physique.",
    "Dis devant le groupe si tu as déjà eu envie d’une relation intime avec quelqu’un présent ici ; tu peux dire qui ou passer.",
    "Choisis une personne volontaire et dis-lui franchement si elle pourrait te plaire pour une relation seulement physique.",
    "Dis le secret le plus gênant de ta vie intime que tu acceptes vraiment de partager.",
    "Dis quelle question sur ta vie intime te mettrait le plus mal à l’aise si quelqu’un te la posait.",
    "Dis si tu as déjà caché une relation intime à quelqu’un et, si tu veux, explique pourquoi.",
    "Dis si tu as déjà été infidèle ; tu peux expliquer ou simplement répondre oui ou non.",
    "Dis si tu as déjà eu une relation d’un soir et si tu l’as regrettée ou non.",
    "Dis si tu as déjà eu une relation intime avec quelqu’un rencontré le jour même.",
    "Dis si tu as déjà menti sur ton expérience intime et pourquoi.",
    "Dis si tu as déjà caché une conversation intime à ton partenaire.",
    "Dis si tu pourrais sortir avec quelqu’un uniquement pour l’attirance physique.",
    "Dis si tu as déjà continué à voir quelqu’un uniquement parce que l’attirance était très forte.",
    "Choisis une personne volontaire et dis-lui si elle correspond à ton type physiquement, sans donner de détails sexuels.",
    "Dis quelle limite est la plus importante pour toi dans une relation intime.",
    "Dis ce que tu n’oserais presque jamais avouer à une personne qui te plaît beaucoup.",
    "Dis quelle personne du groupe serait la plus difficile à oublier après une relation très intense.",
    "Dis si tu pourrais avoir une relation intime avec un ami proche sans vouloir être en couple avec lui ou elle.",
    "Dis si tu as déjà regretté une relation intime dès le lendemain.",
    "Dis si tu as déjà menti sur l’endroit où tu avais passé la nuit.",
    "Dis si tu as déjà supprimé une conversation intime pour éviter qu’elle soit découverte.",
    "Dis si tu as déjà été attiré par le partenaire d’un ami.",
    "Dis si tu as déjà voulu récupérer un ex uniquement parce que l’attirance était encore forte.",
]


def _now():
    return datetime.now(timezone.utc).isoformat()


def _pool_for(kind, level):
    level = 2 if level >= 2 else 1 if level == 1 else 0
    if kind == "verite":
        if level == 2:
            return STRONG_VERY_DARING_TRUTHS
        if level == 1:
            return preferences.DARING_TRUTHS
        return preferences.NORMAL_TRUTHS
    if level == 2:
        return STRONG_VERY_DARING_DARES
    if level == 1:
        return preferences.DARING_DARES
    return preferences.NORMAL_DARES


def register_action_verite_no_repeat(app, db_connection):
    # Remplace le paquet Très osé utilisé par le moteur existant.
    preferences.VERY_DARING_TRUTHS = STRONG_VERY_DARING_TRUTHS
    preferences.VERY_DARING_DARES = STRONG_VERY_DARING_DARES

    with db_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS av_used_prompts (
                room_code TEXT NOT NULL,
                prompt TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)
        cutoff = (datetime.now(timezone.utc) - timedelta(hours=USED_PROMPT_TTL_HOURS)).isoformat()
        conn.execute("DELETE FROM av_used_prompts WHERE created_at < ?", (cutoff,))
        conn.commit()

    def remote_code():
        match = re.fullmatch(r"/action-verite/classe/(\d{4})/choisir", request.path)
        return match.group(1) if match else None

    def remote_used(code):
        cutoff = (datetime.now(timezone.utc) - timedelta(hours=USED_PROMPT_TTL_HOURS)).isoformat()
        with db_connection() as conn:
            conn.execute("DELETE FROM av_used_prompts WHERE created_at < ?", (cutoff,))
            rows = conn.execute(
                "SELECT prompt FROM av_used_prompts WHERE room_code = ?",
                (code,),
            ).fetchall()
            conn.commit()
        return {row["prompt"] for row in rows}

    def mark_remote(code, prompt):
        with db_connection() as conn:
            conn.execute(
                "INSERT INTO av_used_prompts (room_code, prompt, created_at) VALUES (?, ?, ?)",
                (code, prompt, _now()),
            )
            conn.commit()

    def local_used():
        value = session.get(LOCAL_USED_KEY)
        return set(value) if isinstance(value, list) else set()

    def mark_local(prompt):
        value = session.get(LOCAL_USED_KEY)
        used = list(value) if isinstance(value, list) else []
        if prompt not in used:
            used.append(prompt)
        session[LOCAL_USED_KEY] = used[-500:]

    def choose_unused(primary_pool, used, fallback_pools):
        candidates = [prompt for prompt in primary_pool if prompt not in used]
        if candidates:
            return choice(candidates)
        # Si un très long jeu épuise tout le paquet du niveau, on descend
        # seulement vers des propositions encore jamais vues plutôt que répéter.
        for fallback in fallback_pools:
            candidates = [prompt for prompt in fallback if prompt not in used]
            if candidates:
                return choice(candidates)
        return None

    def pick_without_repeat(kind, level):
        level = 2 if level >= 2 else 1 if level == 1 else 0
        primary = _pool_for(kind, level)
        if kind == "verite":
            fallbacks = []
            if level >= 2:
                fallbacks.append(preferences.DARING_TRUTHS)
            if level >= 1:
                fallbacks.append(preferences.NORMAL_TRUTHS)
        else:
            fallbacks = []
            if level >= 2:
                fallbacks.append(preferences.DARING_DARES)
            if level >= 1:
                fallbacks.append(preferences.NORMAL_DARES)

        code = remote_code()
        if code:
            used = remote_used(code)
            prompt = choose_unused(primary, used, fallbacks)
            if prompt is None:
                prompt = "Toutes les propositions de ce type ont déjà été utilisées dans cette partie. Choisis l’autre option ou recommence une nouvelle partie."
            mark_remote(code, prompt)
            return prompt

        if request.path == "/action-verite/local":
            used = local_used()
            prompt = choose_unused(primary, used, fallbacks)
            if prompt is None:
                prompt = "Toutes les propositions de ce type ont déjà été utilisées dans cette partie. Choisis l’autre option ou recommence une nouvelle partie."
            mark_local(prompt)
            return prompt

        # Hors d’une partie active, garde le comportement normal.
        return choice(primary)

    # Les routes déjà enregistrées résolvent ce nom au moment de la requête :
    # le remplacement s’applique donc au mode local et au mode à distance.
    preferences._pick_prompt = pick_without_repeat

    @app.after_request
    def clear_used_prompts(response):
        if request.method != "POST" or response.status_code >= 400:
            return response

        if request.path == "/action-verite/local":
            action = (request.form.get("action") or "").strip().lower()
            if action in {"setup", "reset"}:
                session.pop(LOCAL_USED_KEY, None)
            return response

        if request.path == "/action-verite/classe/creer" and 300 <= response.status_code < 400:
            location = response.headers.get("Location", "")
            match = re.search(r"/action-verite/classe/(\d{4})(?:$|[?#])", location)
            if match:
                with db_connection() as conn:
                    conn.execute("DELETE FROM av_used_prompts WHERE room_code = ?", (match.group(1),))
                    conn.commit()
            return response

        match = re.fullmatch(r"/action-verite/classe/(\d{4})/fermer", request.path)
        if match:
            with db_connection() as conn:
                conn.execute("DELETE FROM av_used_prompts WHERE room_code = ?", (match.group(1),))
                conn.commit()
        return response
