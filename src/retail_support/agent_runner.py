from langchain_core.messages import HumanMessage, SystemMessage

from retail_support.config import WORKER_ATTEMPTS, WORKER_RECURSION_LIMIT
from retail_support.model_provider import ModelProvider

FORMAT_PROMPT = """Turn the answer below into the required fields.
- summary: the answer, unchanged in meaning. Do not add facts.
- status: choose the one that matches the answer, using this guide.

"""

async def run_agent(agent, messages: list):
    for _ in range(WORKER_ATTEMPTS):
       try:
            result = await agent.ainvoke(
                 {"messages": messages}, 
                 config={"recursion_limit": WORKER_RECURSION_LIMIT}
            )
            answer = result["messages"][-1].content
            if not answer:
                raise ValueError("agent returned no answer")
            return answer
       
       except Exception as e:
               last_error = e
    raise last_error

async def to_findings(role, schema, status_guide: str, answer: str):
    model = ModelProvider.get(role=role)
    structured = model.with_structured_output(schema, method="json_schema")
    messages = [SystemMessage(FORMAT_PROMPT + status_guide), HumanMessage(answer)]
    return await structured.ainvoke(messages)

def worker_messages(state, worker: str) -> list:
     return state["messages"][:-1] + [HumanMessage(state["plan"][worker])]