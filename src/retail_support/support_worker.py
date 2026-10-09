# ruff: noqa: E501
from langchain.agents import create_agent

from retail_support.agent_runner import run_agent, to_findings, worker_messages
from retail_support.model_provider import ModelProvider
from retail_support.prompt_store import call_metadata, load_prompt
from retail_support.state import SupportFindings, SupportState
from retail_support.tool_source import support_tools

SUPPORT_SYSTEM_PROMPT = load_prompt("support_system")
SUPPORT_STATUS_GUIDE = load_prompt("support_status_guide")


async def support_worker(state: SupportState) -> dict:
    try:
        async with support_tools() as tools:
            agent = create_agent(
                model=ModelProvider.get(role="support"),
                tools=tools,
                system_prompt=SUPPORT_SYSTEM_PROMPT.text,
            )
            answer = await run_agent(
                agent,
                worker_messages(state, "support"),
                call_metadata("support", SUPPORT_SYSTEM_PROMPT),
            )
        
        findings = await to_findings(
            "support", SupportFindings, SUPPORT_STATUS_GUIDE, answer
        )


    except Exception as e:
        return {"errors": [f"{type(e).__name__}: {e}"], "step_count": 1}
    
    return {"support_findings": findings, "step_count": 1}
