from langchain_core.messages import AIMessage

from retail_support.state import SupportState
from retail_support.supervisor import FINDINGS_FIELD

FAILED_ANSWER = "I could not answer this question."

async def finish_question(state: SupportState) -> dict:
    if state['status'] == 'done':
        summaries = []
        for worker in state['plan']:
            findings = state[FINDINGS_FIELD[worker]]
            if findings is not None:
                summaries.append(findings.summary)
        
        answer = "\n\n".join(summaries)
    else:
        answer = FAILED_ANSWER
    
    return {"messages": [AIMessage(content=answer)]}