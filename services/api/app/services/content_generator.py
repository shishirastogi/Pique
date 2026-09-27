"""MockContentGenerator — template fallback for the LLM batch (docs/03 A.5).

Each generated card rotates: (a) FOCUS facet (subtopic/angle) and (b) one of
several template variants per type, so repeats within a session stay unlikely
even before the LLM layer is available. LLM output replaces these bodies via
generation.generate_session_payloads when a provider is configured.
"""
import random

from app.schemas import TaskObject

_TAGS = lambda task: [task.topic.lower(), *[s.lower() for s in task.subtopics[:2]]]

_FACETS = ["{s}", "{t} basics", "why {t} matters", "common mistakes in {t}",
           "the history of {t}", "{t} in real life", "biggest myth about {t}"]


def _facet(task: TaskObject, variant: int) -> tuple[str, str]:
    """(focus label, subtopic) rotated deterministically by variant."""
    subs = task.subtopics or []
    s = subs[variant % len(subs)] if subs else task.topic
    t = task.topic
    facets = [f.format(s=s, t=t) for f in _FACETS]
    return facets[variant % len(facets)], s


def generate_item(ctype: str, task: TaskObject, interests: list[str], rng: random.Random,
                  variant: int = 0) -> dict:
    t = task.topic
    facet, s = _facet(task, variant)
    interest = interests[0] if interests else None
    level = task.level or "beginner"

    variants = {
        "meme": [
            dict(title=f"When {s} finally clicks",
                 body=f"Nobody:\nMy brain at 3 AM: \"wait — {facet}?\""),
            dict(title=f"Me: I know {t}",
                 body=f"Also me, seeing {s} on the exam: *surprised Pikachu*"),
            dict(title=f"{t} professor: \"it's intuitive\"",
                 body=f"The intuition in question: {facet}."),
        ],
        "reaction_gif": [
            dict(title=f"You, opening {t} notes",
                 body=f"Current mood: pretending {s} looks familiar."),
            dict(title="Me resisting the scroll",
                 body=f"10 minutes on {facet}, then we ship it."),
        ],
        "interesting_fact": [
            dict(title=f"The part of {t} nobody warns you about",
                 body=f"Most people grind through {t} and miss that {s} is the piece that makes "
                      f"everything else make sense. Hold that thought for this session."),
            dict(title=f"Quiet truth about {t}",
                 body=f"Experts rarely say it aloud: understanding {facet} is 80% of passing "
                      f"the rest."),
            dict(title=f"Surprising angle",
                 body=f"Once you see {facet}, you can't unsee it in the material. That's the hook — use it."),
        ],
        "trivia": [
            dict(title="Did you know?",
                 body=f"Every expert in {t} once stared at {s} with total confusion. "
                      f"Confusion is the entry ticket, not the exit sign."),
            dict(title="Bet you didn't know",
                 body=f"“{facet}” trips up almost everyone the first time — which means mastering "
                      f"it puts you ahead."),
        ],
        "quote": [
            dict(title=None,
                 body=f"“You don't have to like {t}. You just have to start it.” — FocusWarmup"),
            dict(title=None,
                 body=f"“{s} is hard? Good. Easy wouldn't hold your attention anyway.” — FocusWarmup"),
        ],
        "quote_removed": [],  # placeholder keeps indices stable
        "joke": [
            dict(title=None, body=f"Why did the {t} student bring a ladder?")
        ],
        "question": [
            dict(title="Honest question",
                 body=f"If you had to explain {s} in one sentence right now, what would it be?"),
            dict(title="Poke the gap",
                 body=f"What's the one thing about {facet} you could *not* explain to a friend? Start there."),
        ],
        "poll": [
            dict(title="Quick pulse", body="Which one sounds harder right now?"),
            dict(title="Hot seat", body="Be honest — where's your weak spot?"),
        ],
        "analogy": [
            dict(title=f"{t}, but make it {interest or 'your world'}",
                 body=(f"Think about {interest or 'anything you love'}: you never master it in one "
                       f"sitting — you learn the patterns, fail a little, level up. {t} works the "
                       f"same way. {s} is just the next pattern to learn.")),
            dict(title=f"The {interest or 'life'} of it",
                 body=(f"{facet.capitalize()} is less about memorizing and more like "
                       f"{interest or 'your favorite skill'}: recognize the pattern, then act. "
                       "Pattern first, details later.")),
        ],
        "historical_context": [
            dict(title=f"Where {t} came from",
                 body=f"Someone, someday, was stuck on the exact piece that annoys you now: {s}. "
                      f"The whole field exists because people kept poking that stubborn question."),
            dict(title="Turns out this is old news",
                 body=f"Debates over {facet} are older than the textbook you're avoiding. "
                      f"You're joining a long line of stubborn curiosity."),
        ],
        "mini_story": [
            dict(title="A 30-second story",
                 body=f"A student kept rereading the same {t} chapter, stuck. Then they rewrote {s} "
                      f"in their own words, badly, on purpose. The bad draft became the good answer."),
            dict(title="The 11pm turnaround",
                 body=f"Exam tomorrow. They picked ONE idea — {s} — and explained it to the mirror. "
                      f"The rest of the chapter suddenly made sense. One idea is the crack in the wall."),
        ],
        "visual_explanation": [
            dict(title=f"{s}, sketched in words",
                 body=f"Picture {t} as three layers:\n• What it is: {s}\n"
                      f"• Why it matters: it's the hinge the rest swings on\n"
                      f"• First thing to check: your own notes' definition of {s}"),
            dict(title=f"See {facet} clearly",
                 body=f"If you sketched it from memory: what's on the left, what's on the right, "
                      f"and what connects them? That sketch is 70% of the test."),
        ],
        "diagram": [
            dict(title=f"{t} — mental map",
                 body=f"[mock diagram] {s} → leads to → {facet} → unlocks → the rest of {t}.")
        ],
        "micro_lesson": [
            dict(title=f"{s} in three lines",
                 body=f"1) {s} is the core of {t}.\n"
                      f"2) Most mistakes come from skipping the definition.\n"
                      f"3) Today's win: one clean sentence about {s}."),
            dict(title=f"Mini-lesson: {facet}",
                 body=f"Rule of thumb: if you can't say what it IS and what it ISN'T, "
                      f"you don't own {s} yet. 60 seconds: write both."),
        ],
        "challenge": [
            dict(title="2-minute challenge",
                 body=f"Write down everything you already know about {s} — no notes, no checking. "
                      f"Ugly lists count."),
            dict(title="Prove it fast",
                 body=f"In 90 seconds: explain {facet} out loud. Fumble = exactly what to revise first."),
        ],
        "first_work_action": [
            dict(title="You're ready. First step:", body=_first_step(task))
        ],
    }
    pool = variants.get(ctype) or [dict(title=None, body=t)]
    payload = dict(pool[variant % len(pool)])  # rotate by variant
    # polls need interaction options built from subtopics; per-variant shuffle
    if ctype == "poll":
        opts = [s] + ([sub for sub in task.subtopics if sub != s][:1])
        opts += ["Just starting at all", f"Everything about {t}"]
        payload["interaction"] = {"kind": "poll", "question": payload["title"],
                                  "options": opts[:4] if len(opts) >= 2 else
                                             ["Too easy", "Just right", "Too hard", "Send help"]}
    if ctype == "question":
        payload["interaction"] = {"kind": "question",
                                  "hint": f"Start with: \"{s} is basically…\" and finish the sentence.",
                                  "answer": "There is no wrong draft. The attempt is the warm-up."}
    if ctype == "joke":
        payload["interaction"] = {"kind": "reveal", "reveal": "For the altitude of knowledge, obviously."}
    if ctype == "trivia":
        payload["interaction"] = {"kind": "reveal", "reveal": "You already qualify. Keep going."}
    if ctype == "challenge":
        payload["interaction"] = {"kind": "challenge"}
    if ctype == "first_work_action":
        payload["interaction"] = {"kind": "finish"}

    humor = "relatable" if ctype == "meme" else ("nerdy" if ctype == "joke" else None)
    return {
        "type": ctype, "topic": t, "subtopics": task.subtopics, "tags": _TAGS(task),
        "language": task.language, "difficulty": level, "tone": payload.pop("tone", None),
        "humor_style": humor, "title": payload.pop("title", None),
        "body": payload.pop("body"),
        "media": payload.pop("media", {"kind": "none"}),
        "interaction": payload.pop("interaction", None),
        "gen_source": "mock",
        "scores": {
            "relevance": round(0.6 + rng.random() * 0.4, 2),
            "personalization": round(0.5 + rng.random() * 0.5, 2),
            "curiosity": round(0.5 + rng.random() * 0.5, 2),
            "quality": round(0.7 + rng.random() * 0.3, 2),
            "learning_value": round(0.5 + rng.random() * 0.5, 2),
        },
    }


def _first_step(task: TaskObject) -> str:
    s0 = task.subtopics[0] if task.subtopics else task.topic
    steps = {
        "exam_prep": f"Open your notes at “{s0}”. Read it once, then write one sentence about it in your own words.",
        "design": f"Open your design tool and write the ONE message your piece about {task.topic} must communicate.",
        "create": f"Open the document and write the first ugly sentence about {task.topic}. Ugly counts.",
        "learn": f"Write or run the tiniest possible example of {s0}. The tiniest one.",
    }
    return steps.get(task.goal, f"Open the thing and do the first 2 minutes of {task.topic}.")
