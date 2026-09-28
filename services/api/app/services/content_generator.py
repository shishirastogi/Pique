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
            dict(title=f"The counter-intuitive secret of {s}",
                 body=f"In {t}, behavior often defies ordinary intuition. {s} was once considered impossible "
                      f"until researchers discovered that the underlying mechanism inverts the standard rule."),
            dict(title=f"Why {s} breaks common sense",
                 body=f"If you look closely at {t}, {s} exists because nature (and engineering) had to solve a "
                      f"fundamental trade-off. Once you see that trade-off, the rest of the subject clicks into place."),
            dict(title=f"The hidden engine in {t}",
                 body=f"Most people think {s} is merely a technical detail. In reality, it is the primary engine "
                      f"driving {t}—without it, the entire system falls apart."),
        ],
        "trivia": [
            dict(title=f"The accidental origin of {s}",
                 body=f"Did you know {s} wasn't discovered on purpose? Early pioneers exploring {t} stumbled upon "
                      f"it while trying to prove something completely different."),
            dict(title=f"The strange history of {t}",
                 body=f"When {s} was first proposed to explain {t}, leading experts vehemently rejected the idea "
                      f"as mathematically or physically absurd."),
        ],
        "quote": [
            dict(title=None,
                 body=f"“The most exciting phrase in science, the one that heralds new discoveries, is not 'Eureka!' but 'That's funny...'” — Isaac Asimov"),
            dict(title=None,
                 body=f"“What we observe is not nature itself, but nature exposed to our method of questioning.” — Werner Heisenberg"),
        ],
        "quote_removed": [],  # placeholder keeps indices stable
        "joke": [
            dict(title=f"The {s} Paradox", body=f"Why do experts in {t} always look so closely at {s}?")
        ],
        "question": [
            dict(title=f"Thought Experiment: {s}",
                 body=f"If you could freeze {s} in mid-operation inside {t}, what would happen to the surrounding equilibrium?"),
            dict(title=f"Conceptual Puzzle: {facet}",
                 body=f"Imagine removing {s} entirely from {t}. What is the very first mechanism that breaks down?"),
        ],
        "poll": [
            dict(title=f"The Great {t} Debate", body=f"Which fundamental aspect of {t} is the most counter-intuitive?"),
            dict(title=f"Dilemma in {s}", body=f"When building or analyzing {t}, where do real-world systems fail first?"),
        ],
        "analogy": [
            dict(title=f"{t} through the lens of {interest or 'everyday mechanics'}",
                 body=(f"Think of {interest or 'a complex engine'}: {s} acts like the central gearbox. "
                       f"It translates unpredictable, raw potential into finely tuned, directional momentum in {t}.")),
            dict(title=f"How {facet} mirrors {interest or 'nature'}",
                 body=(f"Much like {interest or 'an ecosystem in balance'}, {s} in {t} isn't a static formula—"
                       "it is dynamic equilibrium where two opposing forces constantly negotiate stability.")),
        ],
        "historical_context": [
            dict(title=f"The breakthrough that unlocked {t}",
                 body=f"Before {s} was formulated, {t} was considered a chaotic collection of disconnected observations. "
                      f"One pivotal paper connected the dots and established modern principles."),
            dict(title=f"The rivalry behind {facet}",
                 body=f"The principles governing {s} were born out of a fierce intellectual debate between competing "
                      f"schools of thought, ultimately resolved by a single definitive experiment."),
        ],
        "mini_story": [
            dict(title="The 3 AM Eureka",
                 body=f"A researcher spent three grueling years trying to make {t} conform to legacy theories. "
                      f"The solution only appeared when they inverted the core assumption about {s}."),
            dict(title="The anomaly that changed everything",
                 body=f"In the early days of studying {t}, an unexplained margin of error in {s} was dismissed as noise. "
                      f"That 'noise' turned out to be the foundational law of the entire phenomenon."),
        ],
        "visual_explanation": [
            dict(title=f"{s}, visualized",
                 body=f"Imagine {t} as a dynamic balance:\n• Equilibrium: state before disturbance\n"
                      f"• Catalyst: {s} controls the rate and threshold of change\n"
                      f"• Emergence: coherent output without runaway instability."),
            dict(title=f"The geometry of {facet}",
                 body=f"If you trace how {s} operates in real time, the energy (or information) follows the path "
                      f"of least resistance, creating a self-reinforcing pattern."),
        ],
        "diagram": [
            dict(title=f"{t} — System Architecture",
                 body=f"[System Map] Initial State → Catalyst [{s}] → Transformation [{facet}] → Stable Output.")
        ],
        "micro_lesson": [
            dict(title=f"Mental Model: {s}",
                 body=f"1) Core principle: {s} balances internal tension in {t}.\n"
                      f"2) The common trap: mistaking the symptom for the root mechanism.\n"
                      f"3) Key takeaway: follow how state transitions happen under stress."),
            dict(title=f"The 60-Second Intuition: {facet}",
                 body=f"Whenever you encounter {s} in {t}, ask: 'What is being conserved, and what is being transformed?' "
                      f"Answer that, and the complexity evaporates."),
        ],
        "challenge": [
            dict(title="60-Second Mental Challenge",
                 body=f"Can you explain the core mechanism of {s} in two sentences without using buzzwords or jargon?"),
            dict(title="Spot the Paradox",
                 body=f"Find the one scenario in {facet} where increasing the input actually decreases the output rate."),
        ],
        "first_work_action": [
            dict(title="You're primed. First step:", body=_first_step(task))
        ],
    }
    pool = variants.get(ctype) or [dict(title=None, body=t)]
    payload = dict(pool[variant % len(pool)])  # rotate by variant
    # polls need interaction options built from subtopics; per-variant shuffle
    if ctype == "poll":
        opts = [
            f"How {s} operates under extreme conditions",
            f"The counter-intuitive math/logic of {t}",
            f"Real-world edge cases where {s} breaks down",
            f"The hidden trade-offs inside {facet}"
        ]
        payload["interaction"] = {"kind": "poll", "question": payload["title"],
                                  "options": opts}
    if ctype == "question":
        payload["interaction"] = {
            "kind": "question",
            "hint": f"Consider how conservation of state and feedback loops regulate {s} in {t}.",
            "answer": f"It creates a self-limiting feedback cycle that prevents runaway instability and restores balance."
        }
    if ctype == "joke":
        payload["interaction"] = {"kind": "reveal", "reveal": "Because without it, the whole framework falls out of equilibrium!"}
    if ctype == "trivia":
        payload["interaction"] = {
            "kind": "reveal",
            "reveal": f"The breakthrough happened when repeated experimental 'failures' occurred in the exact same anomaly zone."
        }
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
