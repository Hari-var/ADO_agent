from agent_framework import tool  # type: ignore
from typing import Annotated, Optional
from pydantic import Field
from vida.utils.logger import get_logger  # type: ignore
from ado_tools.ado_adapter import (
    ado_create_project, ado_list_projects, ado_create_repo, ado_init_repo, ado_list_repos, ado_list_branches, ado_create_branch,
    ado_list_commits, ado_read_file, ado_commit_file,
    ado_create_pull_request, ado_list_pipelines, ado_run_pipeline,
    ado_get_pipeline_run, ado_create_work_item, ado_get_work_item,
    ado_set_pipeline_variable,
    ado_dispatch_pipeline, ado_approve_pipeline_run,
    ado_list_pipeline_runs, ado_get_pipeline_logs, ado_get_build_timeline,
    ado_create_pipeline, ado_find_files,
)

logger = get_logger(__name__)


@tool(name="ado_list_projects", description="List all projects available in the Azure DevOps organization.", approval_mode="never_require")
def list_projects() -> list:
    logger.info("[ado_tools] [list_projects] Tool called.")
    try:
        return ado_list_projects()
    except Exception as e:
        logger.error(f"[ado_tools] [list_projects] Tool failed. Error: {e}", exc_info=True)
        raise


@tool(name="ado_create_repo", description="Create a new Git repository in an Azure DevOps project.", approval_mode="never_require")
def create_repo(
    project: Annotated[str, Field(description="Azure DevOps project name.")],
    repo_name: Annotated[str, Field(description="Name of the new repository to create.")],
) -> dict:
    logger.info(f"[ado_tools] [create_repo] Tool called. project='{project}', repo_name='{repo_name}'")
    try:
        return ado_create_repo(project=project, repo_name=repo_name)
    except Exception as e:
        logger.error(f"[ado_tools] [create_repo] Tool failed. project='{project}', repo_name='{repo_name}'. Error: {e}", exc_info=True)
        raise


@tool(name="ado_init_repo", description="Initialize an empty Azure DevOps Git repository with a first commit, creating the default branch. Must be called after creating a new repo before any other git operations.", approval_mode="never_require")
def init_repo(
    project: Annotated[str, Field(description="Azure DevOps project name.")],
    repo_name: Annotated[str, Field(description="Repository name to initialize.")],
    branch: Annotated[str, Field(description="Default branch name to create.")] = "main",
    file_path: Annotated[str, Field(description="Path of the initial file to commit.")] = "/README.md",
    content: Annotated[str, Field(description="Content of the initial file.")] = "# Repository",
    commit_message: Annotated[str, Field(description="Initial commit message.")] = "Initial commit",
) -> str:
    logger.info(f"[ado_tools] [init_repo] Tool called. project='{project}', repo='{repo_name}', branch='{branch}'")
    try:
        return ado_init_repo(project=project, repo_name=repo_name, branch=branch,
                             file_path=file_path, content=content, commit_message=commit_message)
    except Exception as e:
        logger.error(f"[ado_tools] [init_repo] Tool failed. project='{project}', repo='{repo_name}'. Error: {e}", exc_info=True)
        raise


@tool(name="ado_list_repos", description="List all Git repositories in an Azure DevOps project.", approval_mode="never_require")
def list_repos(
    project: Annotated[str, Field(description="Azure DevOps project name.")],
) -> list:
    logger.info(f"[ado_tools] [list_repos] Tool called. project='{project}'")
    try:
        return ado_list_repos(project=project)
    except Exception as e:
        logger.error(f"[ado_tools] [list_repos] Tool failed. project='{project}'. Error: {e}", exc_info=True)
        raise


@tool(name="ado_list_branches", description="List all branches in an Azure DevOps Git repository.", approval_mode="never_require")
def list_branches(
    project: Annotated[str, Field(description="Azure DevOps project name.")],
    repo_name: Annotated[str, Field(description="Repository name or ID.")],
) -> list:
    logger.info(f"[ado_tools] [list_branches] Tool called. project='{project}', repo='{repo_name}'")
    try:
        return ado_list_branches(project=project, repo_name=repo_name)
    except Exception as e:
        logger.error(f"[ado_tools] [list_branches] Tool failed. project='{project}', repo='{repo_name}'. Error: {e}", exc_info=True)
        raise


@tool(name="ado_create_branch", description="Create a new branch in an Azure DevOps Git repository from a source branch.", approval_mode="never_require")
def create_branch(
    project: Annotated[str, Field(description="Azure DevOps project name.")],
    repo_name: Annotated[str, Field(description="Repository name or ID.")],
    branch_name: Annotated[str, Field(description="Name of the new branch to create.")],
    source_branch: Annotated[str, Field(description="Source branch to create from (e.g. 'main').")],
) -> str:
    logger.info(f"[ado_tools] [create_branch] Tool called. project='{project}', repo='{repo_name}', branch='{branch_name}', source='{source_branch}'")
    try:
        return ado_create_branch(project=project, repo_name=repo_name, branch_name=branch_name, source_branch=source_branch)
    except Exception as e:
        logger.error(f"[ado_tools] [create_branch] Tool failed. project='{project}', repo='{repo_name}', branch='{branch_name}'. Error: {e}", exc_info=True)
        raise


@tool(name="ado_list_commits", description="List recent commits on a branch in an Azure DevOps repository.", approval_mode="never_require")
def list_commits(
    project: Annotated[str, Field(description="Azure DevOps project name.")],
    repo_name: Annotated[str, Field(description="Repository name or ID.")],
    branch: Annotated[str, Field(description="Branch name to list commits from.")],
    top: Annotated[int, Field(description="Number of commits to return.")] = 10,
) -> list:
    logger.info(f"[ado_tools] [list_commits] Tool called. project='{project}', repo='{repo_name}', branch='{branch}', top={top}")
    try:
        return ado_list_commits(project=project, repo_name=repo_name, branch=branch, top=top)
    except Exception as e:
        logger.error(f"[ado_tools] [list_commits] Tool failed. project='{project}', repo='{repo_name}', branch='{branch}'. Error: {e}", exc_info=True)
        raise


@tool(name="ado_read_file", description="Read the contents of a file from an Azure DevOps Git repository.", approval_mode="never_require")
def read_file(
    project: Annotated[str, Field(description="Azure DevOps project name.")],
    repo_name: Annotated[str, Field(description="Repository name or ID.")],
    path: Annotated[str, Field(description="File path relative to repo root (e.g. '/src/main.py').")],
    branch: Annotated[str, Field(description="Branch to read from.")] = "main",
) -> str:
    logger.info(f"[ado_tools] [read_file] Tool called. project='{project}', repo='{repo_name}', path='{path}', branch='{branch}'")
    try:
        return ado_read_file(project=project, repo_name=repo_name, path=path, branch=branch)
    except Exception as e:
        logger.error(f"[ado_tools] [read_file] Tool failed. project='{project}', repo='{repo_name}', path='{path}', branch='{branch}'. Error: {e}", exc_info=True)
        raise


@tool(name="ado_commit_file", description="Create or update a file in an Azure DevOps Git repository by committing content.", approval_mode="never_require")
def commit_file(
    project: Annotated[str, Field(description="Azure DevOps project name.")],
    repo_name: Annotated[str, Field(description="Repository name or ID.")],
    branch: Annotated[str, Field(description="Branch to commit to.")],
    file_path: Annotated[str, Field(description="File path relative to repo root (e.g. '/src/main.py').")],
    content: Annotated[str, Field(description="Full file content to commit.")],
    commit_message: Annotated[str, Field(description="Commit message.")],
) -> str:
    logger.info(f"[ado_tools] [commit_file] Tool called. project='{project}', repo='{repo_name}', branch='{branch}', file='{file_path}'")
    try:
        return ado_commit_file(project=project, repo_name=repo_name, branch=branch,
                               file_path=file_path, content=content, commit_message=commit_message)
    except Exception as e:
        logger.error(f"[ado_tools] [commit_file] Tool failed. project='{project}', repo='{repo_name}', branch='{branch}', file='{file_path}'. Error: {e}", exc_info=True)
        raise


@tool(name="ado_create_pull_request", description="Create a pull request in an Azure DevOps Git repository.", approval_mode="never_require")
def create_pull_request(
    project: Annotated[str, Field(description="Azure DevOps project name.")],
    repo_name: Annotated[str, Field(description="Repository name or ID.")],
    title: Annotated[str, Field(description="Pull request title.")],
    description: Annotated[str, Field(description="Pull request description.")],
    source_branch: Annotated[str, Field(description="Source branch (feature branch).")],
    target_branch: Annotated[str, Field(description="Target branch (e.g. 'main').")],
) -> dict:
    logger.info(f"[ado_tools] [create_pull_request] Tool called. project='{project}', repo='{repo_name}', '{source_branch}' -> '{target_branch}'")
    try:
        return ado_create_pull_request(project=project, repo_name=repo_name, title=title,
                                       description=description, source_branch=source_branch, target_branch=target_branch)
    except Exception as e:
        logger.error(f"[ado_tools] [create_pull_request] Tool failed. project='{project}', repo='{repo_name}', title='{title}'. Error: {e}", exc_info=True)
        raise


@tool(name="ado_list_pipelines", description="List all pipelines in an Azure DevOps project.", approval_mode="never_require")
def list_pipelines(
    project: Annotated[str, Field(description="Azure DevOps project name.")],
) -> list:
    logger.info(f"[ado_tools] [list_pipelines] Tool called. project='{project}'")
    try:
        return ado_list_pipelines(project=project)
    except Exception as e:
        logger.error(f"[ado_tools] [list_pipelines] Tool failed. project='{project}'. Error: {e}", exc_info=True)
        raise


@tool(name="ado_run_pipeline", description="Trigger a pipeline run in Azure DevOps.", approval_mode="never_require")
def run_pipeline(
    project: Annotated[str, Field(description="Azure DevOps project name.")],
    pipeline_id: Annotated[int, Field(description="Numeric pipeline ID.")],
    branch: Annotated[str, Field(description="Branch to run the pipeline on.")] = "main",
    variables: Optional[Annotated[dict, Field(description="Optional key-value pipeline variables.")]] = None,
) -> dict:
    logger.info(f"[ado_tools] [run_pipeline] Tool called. project='{project}', pipeline_id={pipeline_id}, branch='{branch}'")
    try:
        return ado_run_pipeline(project=project, pipeline_id=pipeline_id, branch=branch, variables=variables)
    except Exception as e:
        logger.error(f"[ado_tools] [run_pipeline] Tool failed. project='{project}', pipeline_id={pipeline_id}, branch='{branch}'. Error: {e}", exc_info=True)
        raise


@tool(name="ado_get_pipeline_run", description="Get the status and result of a specific Azure DevOps pipeline run.", approval_mode="never_require")
def get_pipeline_run(
    project: Annotated[str, Field(description="Azure DevOps project name.")],
    pipeline_id: Annotated[int, Field(description="Numeric pipeline ID.")],
    run_id: Annotated[int, Field(description="Numeric run ID.")],
) -> dict:
    logger.info(f"[ado_tools] [get_pipeline_run] Tool called. project='{project}', pipeline_id={pipeline_id}, run_id={run_id}")
    try:
        return ado_get_pipeline_run(project=project, pipeline_id=pipeline_id, run_id=run_id)
    except Exception as e:
        logger.error(f"[ado_tools] [get_pipeline_run] Tool failed. project='{project}', pipeline_id={pipeline_id}, run_id={run_id}. Error: {e}", exc_info=True)
        raise


@tool(name="ado_create_work_item", description="Create a work item (Bug, Task, User Story, etc.) in Azure DevOps.", approval_mode="never_require")
def create_work_item(
    project: Annotated[str, Field(description="Azure DevOps project name.")],
    work_item_type: Annotated[str, Field(description="Work item type (e.g. 'Bug', 'Task', 'User Story').")],
    title: Annotated[str, Field(description="Work item title.")],
    description: Annotated[Optional[str], Field(description="Work item description.")] = None,
) -> dict:
    logger.info(f"[ado_tools] [create_work_item] Tool called. project='{project}', type='{work_item_type}', title='{title}'")
    try:
        return ado_create_work_item(project=project, work_item_type=work_item_type, title=title, description=description)
    except Exception as e:
        logger.error(f"[ado_tools] [create_work_item] Tool failed. project='{project}', type='{work_item_type}', title='{title}'. Error: {e}", exc_info=True)
        raise


@tool(name="ado_get_work_item", description="Get details of a work item by ID from Azure DevOps.", approval_mode="never_require")
def get_work_item(
    work_item_id: Annotated[int, Field(description="Numeric work item ID.")],
) -> dict:
    logger.info(f"[ado_tools] [get_work_item] Tool called. work_item_id={work_item_id}")
    try:
        return ado_get_work_item(work_item_id=work_item_id)
    except Exception as e:
        logger.error(f"[ado_tools] [get_work_item] Tool failed. work_item_id={work_item_id}. Error: {e}", exc_info=True)
        raise


@tool(name="ado_set_pipeline_variable", description="Set or update a variable in an Azure DevOps variable group.", approval_mode="never_require")
def set_pipeline_variable(
    project: Annotated[str, Field(description="Azure DevOps project name.")],
    group_name: Annotated[str, Field(description="Variable group name.")],
    var_name: Annotated[str, Field(description="Variable name.")],
    var_value: Annotated[str, Field(description="Variable value.")],
    is_secret: Annotated[bool, Field(description="Mark variable as secret.")] = False,
) -> str:
    logger.info(f"[ado_tools] [set_pipeline_variable] Tool called. project='{project}', group='{group_name}', var='{var_name}', is_secret={is_secret}")
    try:
        return ado_set_pipeline_variable(project=project, group_name=group_name,
                                         var_name=var_name, var_value=var_value, is_secret=is_secret)
    except Exception as e:
        logger.error(f"[ado_tools] [set_pipeline_variable] Tool failed. project='{project}', group='{group_name}', var='{var_name}'. Error: {e}", exc_info=True)
        raise


# ── Dispatch Tools ────────────────────────────────────────────────────────────

@tool(name="ado_dispatch_pipeline", description="Trigger an Azure DevOps pipeline by name (resolves pipeline ID automatically).", approval_mode="never_require")
def dispatch_pipeline(
    project: Annotated[str, Field(description="Azure DevOps project name.")],
    pipeline_name: Annotated[str, Field(description="Exact pipeline name to dispatch.")],
    branch: Annotated[str, Field(description="Branch to run the pipeline on.")] = "main",
    variables: Optional[Annotated[dict, Field(description="Optional key-value pipeline variables.")]] = None,
) -> dict:
    logger.info(f"[ado_tools] [dispatch_pipeline] Tool called. project='{project}', pipeline_name='{pipeline_name}', branch='{branch}'")
    try:
        return ado_dispatch_pipeline(project=project, pipeline_name=pipeline_name, branch=branch, variables=variables)
    except Exception as e:
        logger.error(f"[ado_tools] [dispatch_pipeline] Tool failed. project='{project}', pipeline_name='{pipeline_name}'. Error: {e}", exc_info=True)
        raise


@tool(name="ado_approve_pipeline_run", description="Approve a pending pipeline run gate or approval check in Azure DevOps.", approval_mode="never_require")
def approve_pipeline_run(
    project: Annotated[str, Field(description="Azure DevOps project name.")],
    approval_id: Annotated[str, Field(description="The approval ID to approve (UUID).")],
    comment: Annotated[str, Field(description="Optional comment for the approval.")] = "Approved by agent",
) -> dict:
    logger.info(f"[ado_tools] [approve_pipeline_run] Tool called. project='{project}', approval_id='{approval_id}'")
    try:
        return ado_approve_pipeline_run(project=project, approval_id=approval_id, comment=comment)
    except Exception as e:
        logger.error(f"[ado_tools] [approve_pipeline_run] Tool failed. project='{project}', approval_id='{approval_id}'. Error: {e}", exc_info=True)
        raise


# ── Monitoring Tools ──────────────────────────────────────────────────────────

@tool(name="ado_list_pipeline_runs", description="List recent runs for a specific Azure DevOps pipeline, including state and result.", approval_mode="never_require")
def list_pipeline_runs(
    project: Annotated[str, Field(description="Azure DevOps project name.")],
    pipeline_id: Annotated[int, Field(description="Numeric pipeline ID.")],
    top: Annotated[int, Field(description="Number of recent runs to return.")] = 10,
) -> list:
    logger.info(f"[ado_tools] [list_pipeline_runs] Tool called. project='{project}', pipeline_id={pipeline_id}, top={top}")
    try:
        return ado_list_pipeline_runs(project=project, pipeline_id=pipeline_id, top=top)
    except Exception as e:
        logger.error(f"[ado_tools] [list_pipeline_runs] Tool failed. project='{project}', pipeline_id={pipeline_id}. Error: {e}", exc_info=True)
        raise


@tool(name="ado_get_pipeline_logs", description="Get log entries for a specific Azure DevOps pipeline run.", approval_mode="never_require")
def get_pipeline_logs(
    project: Annotated[str, Field(description="Azure DevOps project name.")],
    pipeline_id: Annotated[int, Field(description="Numeric pipeline ID.")],
    run_id: Annotated[int, Field(description="Numeric run ID.")],
) -> list:
    logger.info(f"[ado_tools] [get_pipeline_logs] Tool called. project='{project}', pipeline_id={pipeline_id}, run_id={run_id}")
    try:
        return ado_get_pipeline_logs(project=project, pipeline_id=pipeline_id, run_id=run_id)
    except Exception as e:
        logger.error(f"[ado_tools] [get_pipeline_logs] Tool failed. project='{project}', pipeline_id={pipeline_id}, run_id={run_id}. Error: {e}", exc_info=True)
        raise


@tool(name="ado_get_build_timeline", description="Get the detailed step-by-step timeline of an Azure DevOps build, showing each task's state and result.", approval_mode="never_require")
def get_build_timeline(
    project: Annotated[str, Field(description="Azure DevOps project name.")],
    build_id: Annotated[int, Field(description="Numeric build ID (same as run ID for classic/YAML pipelines).")],
) -> list:
    logger.info(f"[ado_tools] [get_build_timeline] Tool called. project='{project}', build_id={build_id}")
    try:
        return ado_get_build_timeline(project=project, build_id=build_id)
    except Exception as e:
        logger.error(f"[ado_tools] [get_build_timeline] Tool failed. project='{project}', build_id={build_id}. Error: {e}", exc_info=True)
        raise


# ── Create Pipeline ───────────────────────────────────────────────────────────

@tool(name="ado_create_pipeline", description="Create a new YAML pipeline in Azure DevOps and add it to the project's pipeline list.", approval_mode="never_require")
def create_pipeline(
    project: Annotated[str, Field(description="Azure DevOps project name.")],
    name: Annotated[str, Field(description="Name for the new pipeline.")],
    repo_name: Annotated[str, Field(description="Repository name where the YAML file lives.")],
    yaml_path: Annotated[str, Field(description="Path to the YAML pipeline file in the repo (e.g. '/azure-pipelines.yml').")],
    branch: Annotated[str, Field(description="Default branch for the pipeline.")] = "main",
    folder: Annotated[str, Field(description="Pipeline folder path in ADO (e.g. '\\\\MyFolder'). Defaults to root.")] = "\\",
) -> dict:
    logger.info(f"[ado_tools] [create_pipeline] Tool called. project='{project}', name='{name}', repo='{repo_name}', yaml='{yaml_path}'")
    try:
        return ado_create_pipeline(project=project, name=name, repo_name=repo_name,
                                   yaml_path=yaml_path, branch=branch, folder=folder)
    except Exception as e:
        logger.error(f"[ado_tools] [create_pipeline] Tool failed. project='{project}', name='{name}'. Error: {e}", exc_info=True)
        raise


# ── Find Files ───────────────────────────────────────────────────────────────

@tool(name="ado_find_files", description="Search for files in an Azure DevOps repository by file extension (e.g. '.yml', '.json') and/or a regex pattern matched against file paths.", approval_mode="never_require")
def find_files(
    project: Annotated[str, Field(description="Azure DevOps project name.")],
    repo_name: Annotated[str, Field(description="Repository name or ID.")],
    branch: Annotated[str, Field(description="Branch to search in.")] = "main",
    pattern: Annotated[Optional[str], Field(description="Regex pattern to match against file paths. Leave empty to skip regex filtering.")] = None,
    extensions: Annotated[Optional[list], Field(description="List of file extensions to filter by (e.g. ['.yml', '.json']). Leave empty to skip extension filtering.")] = None,
    scope_path: Annotated[str, Field(description="Repo folder path to search under (e.g. '/src'). Defaults to repo root.")] = "/",
) -> list:
    logger.info(f"[ado_tools] [find_files] Tool called. project='{project}', repo='{repo_name}', branch='{branch}', pattern='{pattern}', extensions={extensions}, scope='{scope_path}'")
    try:
        return ado_find_files(project=project, repo_name=repo_name, branch=branch,
                              pattern=pattern, extensions=extensions, scope_path=scope_path)
    except Exception as e:
        logger.error(f"[ado_tools] [find_files] Tool failed. project='{project}', repo='{repo_name}'. Error: {e}", exc_info=True)
        raise


# ── Create Project ────────────────────────────────────────────────────────────

@tool(name="ado_create_project", description="Create a new Azure DevOps project in the organization. Waits for the project to be fully provisioned before returning.", approval_mode="never_require")
def create_project(
    name: Annotated[str, Field(description="Name of the new project.")],
    description: Annotated[str, Field(description="Optional project description.")] = "",
    visibility: Annotated[str, Field(description="Project visibility: 'private' or 'public'.")] = "private",
    source_control: Annotated[str, Field(description="Source control type: 'Git' or 'Tfvc'.")] = "Git",
    process_template: Annotated[str, Field(description="Process template name: 'Agile', 'Scrum', 'CMMI', or 'Basic'.")] = "Agile",
) -> dict:
    logger.info(f"[ado_tools] [create_project] Tool called. name='{name}', visibility='{visibility}', process='{process_template}'")
    try:
        return ado_create_project(name=name, description=description, visibility=visibility,
                                   source_control=source_control, process_template=process_template)
    except Exception as e:
        logger.error(f"[ado_tools] [create_project] Tool failed. name='{name}'. Error: {e}", exc_info=True)
        raise
