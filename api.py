from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional
from ado_agent import ado_agent
from vida.utils.preprocess import try_parse_json  # type: ignore
from vida.models.requests.Agent_Task_requests import AgentTaskDetailsCreateRequest, AgentTaskDetailsUpdateRequest  # type: ignore
from vida.database.database import sessionlocal  # type: ignore
from vida.utils.request_context import task_id_ctx  # type: ignore
from vida.utils.crud_ops import AgentTaskOps as ato  # type: ignore
from datetime import datetime, timezone

router = APIRouter()


class ado_agent_request(BaseModel):
    prompt: str
    task_id: Optional[int] = None
    session: Optional[str] = None


@router.post("/ado_agent")
async def ado_agent_call(request: ado_agent_request):
    task_id = request.task_id
    db = sessionlocal()

    if not task_id:
        payload = AgentTaskDetailsCreateRequest(
            agent_id=6,
            task_status="pending",
            task_prompt=request.prompt,
            task_name=request.prompt[:20],
            start_time=datetime.now(timezone.utc),
        )
        task_id = ato().add_task(db=db, task=payload)
        if not task_id:
            ato().update_task(db=db, task_id=task_id, task=AgentTaskDetailsUpdateRequest(
                task_status="failed", end_time=datetime.now(timezone.utc), issue="Failed to create task"
            ))
            return {"message": "Failed to create task"}

    task_id_ref = task_id_ctx.set(task_id)

    try:
        agent = await ado_agent()
        response = await agent.run(request.prompt, session=request.session, task_id=task_id)

        if response:
            output, is_json = try_parse_json(response.text)
            ato().update_task(db=db, task_id=task_id, task=AgentTaskDetailsUpdateRequest(
                task_status="success", end_time=datetime.now(timezone.utc)
            ))
            return {"response": "ADO agent executed successfully", "raw": response, "is_json": is_json, "output": output}

        ato().update_task(db=db, task_id=task_id, task=AgentTaskDetailsUpdateRequest(
            task_status="failed", end_time=datetime.now(timezone.utc), issue="No response from agent"
        ))
        return {"message": "Failed to get response from agent"}

    except Exception as e:
        ato().update_task(db=db, task_id=task_id, task=AgentTaskDetailsUpdateRequest(
            task_status="failed", end_time=datetime.now(timezone.utc), issue=str(e)
        ))
        raise

    finally:
        task_id_ctx.reset(task_id_ref)
        db.close()
