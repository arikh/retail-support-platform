from langchain_core.messages import HumanMessage, SystemMessage

from retail_support.config import WORKER_ATTEMPTS, WORKER_RECURSION_LIMIT
from retail_support.model_provider import ModelProvider
from retail_support.prompt_store import Prompt, call_metadata, load_prompt

FORMAT_PROMPT = load_prompt("format_findings")    

async def run_agent(agent, messages: list, metadata: dict):
    for _ in range(WORKER_ATTEMPTS):
       try:
            result = await agent.ainvoke(
                 {"messages": messages}, 
                 config={
                     "recursion_limit": WORKER_RECURSION_LIMIT,
                     "metadata": metadata,
                 },
            )
            answer = result["messages"][-1].content
            if not answer:
                raise ValueError("agent returned no answer")
            return answer
       
       except Exception as e:
               last_error = e
    raise last_error

async def to_findings(role, schema, status_guide: Prompt, answer: str):
    model = ModelProvider.get(role=role)
    structured = model.with_structured_output(schema, method="json_schema")
    messages = [
        SystemMessage(FORMAT_PROMPT.text + status_guide.text),
        HumanMessage(answer),
    ]
    metadata = call_metadata(role, FORMAT_PROMPT, status_guide)
    return await structured.ainvoke(messages, config={"metadata": metadata})

def worker_messages(state, worker: str) -> list:
     return state["messages"][:-1] + [HumanMessage(state["plan"][worker])]
