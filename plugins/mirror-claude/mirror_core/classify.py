"""Rule-based labelling of human prompts, English and French. No model, no network.

Kinds: directive, question, approval, challenge, context, pasted, meta.
Rules are deliberately simple and readable. They are a first guess, not a judge:
every kind is a proxy, and the report says so.
"""
from __future__ import annotations
import re

KINDS = ["directive", "question", "approval", "challenge", "context", "pasted", "meta"]

_META = re.compile(r"^\s*(<command-|<local-command|<task-|\[Request interrupted|/[a-z][\w-]*(\s|$))", re.I)

_APPROVAL = re.compile(
    r"^\s*(?:"
    r"ok(?:ay)?|yes|yep|yeah|yup|sure|go|go ahead|go on|do it|apply(?: it)?|sounds good|looks good|lgtm|"
    r"agreed?|i agree|perfect|great|good|nice|done|continue|proceed|approved?|ship it|commit|push|thanks|thank you|thx|"
    r"merci|oui|ouais|d'accord|d’accord|dac|vas-y|vas y|allez-y|allez|parfait|c'est bon|c’est bon|top|nickel|super|génial|"
    r"valide|validé|fais-le|fais le|go pour|on y va|let'?s go|(?:run |do |apply )?step \d+"
    r")\b[\s,.!:;\-]*(?:[^.?!\n]{0,40})?[.!]?\s*$",
    re.I,
)

_CHALLENGE = re.compile(
    r"(i don'?t agree|i disagree|disagree|that'?s (?:not|wrong|incorrect)|not right|incorrect|\bwrong\b|"
    r"why didn'?t you|why did you|you didn'?t|you missed|you forgot|you skipped|doesn'?t work|not working|still (?:not|doesn'?t)|"
    r"\bbroken\b|mistake|are you sure|really\?|no source|which source|where did you get|prove it|double[- ]check|"
    r"not what i (?:asked|said|wanted)|i said|i already|hallucinat|"
    r"pas d'accord|pas d’accord|c'est faux|c’est faux|\bfaux\b|ça ne marche pas|ca ne marche pas|ne marche pas|"
    r"tu as oublié|tu n'as pas|tu n’as pas|pourquoi tu|pourquoi as-tu|es-tu sûr|t'es sûr|t’es sûr|tu es sûr|"
    r"pas ce que j|je t'ai dit|je t’ai dit|c'est pas ça|c’est pas ça|tu te trompes|erreur|"
    r"\bproblem\b|\bissue\b|\bbug\b|friction|confus|i got lost|frustrat|annoy|too (?:much|long|big|small|slow)|"
    r"not (?:easy|clear|shown|showing|user[- ]friendly)|can'?t (?:access|find|see|open|read)|couldn'?t (?:find|access|open)|"
    r"didn'?t (?:work|show|save|appear)|another distraction|"
    r"problème|souci|pas clair|trop (?:long|grand|petit|lent)|je n'arrive pas|je n’arrive pas|impossible de|ne s'affiche pas|"
    r"ne s’affiche pas|je suis perdu|bloqué|compliqué)",
    re.I,
)

_FILLER = re.compile(r"^\s*(?:(?:ok(?:ay)?|yes|yep|great|good|nice|perfect|so|well|and|now|then|also|alright|right|oui|bon|alors|et|ensuite|du coup)\b[\s,.!:;\-]*)+", re.I)
_WANT = re.compile(r"^\s*(?:i want(?: you to)?|i need(?: you to)?|you can|you should|we can|we should|we will|let'?s|je veux|j'aimerais|je voudrais|tu peux|on peut|on va)\b", re.I)
_WONDER = re.compile(r"(i was wondering|i wonder|i'?m curious|what about|how (?:could|would|does|do)|should (?:i|we|the)|is it worth|do you think|je me demande|est-ce que|qu'en penses|que penses)", re.I)
_POLITE = re.compile(r"^\s*(can you|could you|would you|will you|please|peux-tu|peux tu|pourrais-tu|pourrais tu|tu peux|pouvez-vous|pourriez-vous|s'il te plaît|stp)\b", re.I)
_EXPLAIN = re.compile(r"\b(explain|why|what|how|which|pourquoi|comment|quel|quelle|qu'est|explique)\b", re.I)
_QSTART = re.compile(
    r"^\s*(what|why|how|when|where|who|which|is|are|does|do|did|should|shall|can|could|would|will|explain|tell me|any|"
    r"est-ce|pourquoi|comment|quel|quelle|quels|quand|où|qui|qu'est|c'est quoi|explique|dis-moi|y a-t-il|faut-il)\b",
    re.I,
)
_VERB = re.compile(
    r"^\s*(build|make|write|create|run|fix|add|update|change|remove|delete|find|search|check|show|give|draft|use|let'?s|"
    r"install|implement|refactor|generate|list|summari[sz]e|read|open|rename|move|copy|save|test|try|set|start|stop|"
    r"crée|créer|fais|ajoute|modifie|supprime|trouve|cherche|vérifie|montre|donne|écris|utilise|lance|génère|liste|résume|"
    r"lis|ouvre|renomme|déplace|copie|sauvegarde|teste|essaie|installe|corrige|mets|change)\b",
    re.I,
)


def classify(text: str) -> str:
    t = (text or "").strip()
    if not t:
        return "meta"
    if _META.search(t):
        return "meta"
    if t.startswith("<pasted_content") or len(t) > 1500 or t.count("\n") >= 12:
        return "pasted"
    if len(t) <= 60 and _APPROVAL.match(t) and "?" not in t:
        tail = _FILLER.sub("", t)
        if not (tail and (_VERB.match(tail) or _WANT.match(tail)) and not re.match(r"(run |do |apply )?step \d", tail, re.I)):
            return "approval"
    if _CHALLENGE.search(t):
        return "challenge"
    if _POLITE.match(t) and not _EXPLAIN.search(t):
        return "directive"
    core = _FILLER.sub("", t)
    if _WANT.match(core) or _VERB.match(core) or _POLITE.match(core):
        return "directive"
    if t.rstrip().endswith("?") or _QSTART.match(core) or "?" in t or _WONDER.search(t):
        return "question"
    return "context"
