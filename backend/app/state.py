from typing import TypedDict, List, Optional, Annotated
import operator


class AgentState(TypedDict):
    question: str
    memory_context: str

    plan: str

    documents: Annotated[List[str], operator.add]
    sql_result: Optional[str]
    code_result: Optional[str]

    answer: str

    critique_passed: bool
    critique_feedback: Optional[str]

    steps: Annotated[List[str], operator.add]
    revisions: int


def new_state(question: str, memory_context: str = "") -> AgentState:
    return AgentState(
        question=question,
        memory_context=memory_context,
        plan="",
        documents=[],
        sql_result=None,
        code_result=None,
        answer="",
        critique_passed=False,
        critique_feedback=None,
        steps=[],
        revisions=0,
    )
