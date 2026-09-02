from dotenv import load_dotenv
load_dotenv()

from vida.agents.Base_agent import Base_Agent  # type: ignore
from agent_framework import Agent, tool  # type: ignore
from typing import Annotated
from pydantic import Field
from ado_tools.base_trail import (
    create_project, list_projects, create_repo, init_repo, list_repos, list_branches, create_branch, list_commits,
    read_file, commit_file, create_pull_request,
    list_pipelines, run_pipeline, get_pipeline_run,
    create_work_item, get_work_item, set_pipeline_variable,
    dispatch_pipeline, approve_pipeline_run,
    list_pipeline_runs, get_pipeline_logs, get_build_timeline,
    create_pipeline, find_files,
)
from vida.utils.config import Github_agent_config as git_config  # type: ignore
from vida.utils.config import Base_agent_config as baconfig
from vida.utils.logger import get_logger  # type: ignore

logger = get_logger(__name__)


class AdoAgent(Base_Agent):
    name = "ado_agent"
    
    model = git_config.model
    AI_endpoint = git_config.AI_endpoint
    instructions = (
        "You are an Azure DevOps agent. Use the available tools to manage repositories, "
        "branches, commits, pull requests, pipelines, work items, and variable groups in Azure DevOps."
    )
    tools = [
        create_project, list_projects, create_repo, init_repo, list_repos, list_branches, create_branch, list_commits,
        read_file, commit_file, create_pull_request,
        list_pipelines, run_pipeline, get_pipeline_run,
        create_work_item, get_work_item, set_pipeline_variable,
        dispatch_pipeline, approve_pipeline_run,
        list_pipeline_runs, get_pipeline_logs, get_build_timeline,
        create_pipeline, find_files,
    ]


@tool(name="ADO_Agent", description="Azure DevOps agent that manages repos, branches, pipelines, work items, and more.", approval_mode="never_require")
async def ado_agent():
    logger.info("[ado_agent] Called.")
    try:
        agent = AdoAgent.get_instance()
        return agent
    except Exception as e:
        logger.error(f"[ado_agent] Error: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    import asyncio
    print(asyncio.run(AdoAgent.get_instance().run("list all repos in project MyProject")))
