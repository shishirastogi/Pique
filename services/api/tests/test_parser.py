"""Mock task parser behavior (docs/03 A.2 contract stays when LLM lands)."""
from app.services import task_parser


def test_parses_goal_topic_level_urgency():
    t = task_parser.parse_task("I need to study thermodynamics for my exam tomorrow, I'm weak at physics")
    assert t.goal == "exam_prep"
    assert "thermodynamics" in t.topic.lower()
    assert t.level == "beginner"
    assert t.urgency == "tomorrow"


def test_clarifies_when_level_missing():
    t = task_parser.parse_task("I need to design a climate change poster")
    q = task_parser.needs_clarification(t)
    assert q is not None and q.field == "level"
    refined = task_parser.refine_with_answer(t, "advanced")
    assert refined.level == "advanced"
    assert task_parser.needs_clarification(refined) is None
