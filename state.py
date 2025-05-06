from typing import TypedDict

class ToolCall(TypedDict):
    name: str # function name
    id: str # id of the tool call
    args: dict # function arguments

class AgentState(TypedDict):

    waiting_approval: dict # tool call info

def init_agent_state():
    s = AgentState()
    s["waiting_approval"] = {}
    return s
