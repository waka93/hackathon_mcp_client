from typing import TypedDict

class AgentState(TypedDict):

    waiting_approval: bool

def init_agent_state():
    s = AgentState()
    s["waiting_approval"] = False
    return s