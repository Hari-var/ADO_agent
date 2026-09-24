"""
Temporary ADO adapter — mirrors vida.adapters.github pattern.
Will be moved into vida library later.
"""
import os
from typing import Optional
from azure.devops.connection import Connection  # type: ignore
from msrest.authentication import BasicAuthentication  # type: ignore
from vida.utils.clientConnection import get_credential  # type: ignore
from vida.utils.logger import get_logger  # type: ignore

logger = get_logger(__name__)


class _AzureIdentityCredential(BasicAuthentication):
    """Wraps azure-identity credential into msrest BasicAuthentication for ADO SDK."""
    _ADO_SCOPE = "499b84ac-1321-427f-aa17-267ca6975798/.default"  # Azure DevOps resource

    def __init__(self):
        self._credential = get_credential()

    def signed_session(self, session=None):
        import requests
        session = session or requests.Session()
        token = self._credential.get_token(self._ADO_SCOPE).token
        session.headers["Authorization"] = f"Bearer {token}"
        return session


# def get_ado_client():
#     org_url = os.environ.get("ADO_ORG_URL")
#     if not org_url:
#         logger.error("[ado_adapter] ADO_ORG_URL environment variable is not set.")
#         raise EnvironmentError("ADO_ORG_URL is not set.")
#     logger.info(f"[ado_adapter] Creating ADO connection to {org_url}")
#     return Connection(base_url=org_url, creds=_AzureIdentityCredential())

def get_ado_client():
    org_url = os.environ.get("ADO_ORG_URL")
    pat = os.environ.get("ADO_PAT")
    if not org_url:
        raise EnvironmentError("ADO_ORG_URL is not set.")
    creds = BasicAuthentication("", pat) if pat else _AzureIdentityCredential()
    return Connection(base_url=org_url, creds=creds)



# ── Projects ──────────────────────────────────────────────────────────────────

def ado_create_project(name: str, description: str = "", visibility: str = "private",
                       source_control: str = "Git", process_template: str = "Agile") -> dict:
    logger.info(f"[ado_adapter] [create_project] Creating project '{name}', visibility='{visibility}'.")
    try:
        import time
        from azure.devops.v7_1.core.models import TeamProject  # type: ignore
        conn = get_ado_client()
        core_client = conn.clients.get_core_client()
        processes = core_client.get_processes()
        process = next((p for p in processes if p.name.lower() == process_template.lower()), None)
        if not process:
            return {"error": f"Process template '{process_template}' not found. Available: {[p.name for p in processes]}"}
        project = TeamProject(
            name=name,
            description=description,
            visibility=visibility,
            capabilities={
                "versioncontrol": {"sourceControlType": source_control},
                "processTemplate": {"templateTypeId": process.id},
            },
        )
        operation = core_client.queue_create_project(project_to_create=project)
        logger.info(f"[ado_adapter] [create_project] Project queued. Operation ID: {operation.id}")
        ops_client = conn.clients.get_operations_client()
        for _ in range(12):
            time.sleep(5)
            op = ops_client.get_operation(operation_id=operation.id)
            logger.info(f"[ado_adapter] [create_project] Operation status: {op.status}")
            if op.status in ("succeeded", "failed", "cancelled"):
                break
        if op.status != "succeeded":
            return {"error": f"Project creation ended with status '{op.status}'."}
        created = core_client.get_project(project_id=name)
        logger.info(f"[ado_adapter] [create_project] Project '{name}' created. ID: {created.id}")
        return {"id": created.id, "name": created.name, "state": created.state, "url": created.url}
    except Exception as e:
        logger.error(f"[ado_adapter] [create_project] Failed. Error: {e}", exc_info=True)
        raise


def ado_list_projects() -> list[dict]:
    logger.info("[ado_adapter] [list_projects] Listing all projects in the organization.")
    try:
        conn = get_ado_client()
        client = conn.clients.get_core_client()
        projects = client.get_projects()
        result = [{"id": p.id, "name": p.name, "state": p.state, "visibility": p.visibility} for p in projects]
        logger.info(f"[ado_adapter] [list_projects] Found {len(result)} projects.")
        return result
    except Exception as e:
        logger.error(f"[ado_adapter] [list_projects] Failed to list projects. Error: {e}", exc_info=True)
        raise


# ── Repos ─────────────────────────────────────────────────────────────────────

def ado_create_repo(project: str, repo_name: str) -> dict:
    logger.info(f"[ado_adapter] [create_repo] Creating repo '{repo_name}' in project '{project}'.")
    try:
        conn = get_ado_client()
        client = conn.clients.get_git_client()
        from azure.devops.v7_1.git.models import GitRepositoryCreateOptions  # type: ignore
        repo = client.create_repository(
            git_repository_to_create=GitRepositoryCreateOptions(name=repo_name),
            project=project,
        )
        logger.info(f"[ado_adapter] [create_repo] Repo '{repo_name}' created successfully. ID: {repo.id}")
        return {"id": repo.id, "name": repo.name, "default_branch": repo.default_branch, "url": repo.remote_url}
    except Exception as e:
        logger.error(f"[ado_adapter] [create_repo] Failed to create repo '{repo_name}' in project '{project}'. Error: {e}", exc_info=True)
        raise


def ado_list_repos(project: str) -> list[dict]:
    logger.info(f"[ado_adapter] [list_repos] Listing repos in project '{project}'.")
    try:
        conn = get_ado_client()
        client = conn.clients.get_git_client()
        repos = client.get_repositories(project)
        result = [{"id": r.id, "name": r.name, "default_branch": r.default_branch, "url": r.remote_url} for r in repos]
        logger.info(f"[ado_adapter] [list_repos] Found {len(result)} repos in project '{project}'.")
        return result
    except Exception as e:
        logger.error(f"[ado_adapter] [list_repos] Failed to list repos in project '{project}'. Error: {e}", exc_info=True)
        raise


def ado_init_repo(project: str, repo_name: str, branch: str = "main", file_path: str = "/README.md", content: str = "# Repository", commit_message: str = "Initial commit") -> str:
    logger.info(f"[ado_adapter] [init_repo] Initializing repo '{repo_name}' in project '{project}' with branch '{branch}'.")
    try:
        from azure.devops.v7_1.git.models import GitPush, GitCommitRef, Change, ItemContent, GitRefUpdate  # type: ignore
        conn = get_ado_client()
        client = conn.clients.get_git_client()
        push = GitPush(
            ref_updates=[GitRefUpdate(
                name=f"refs/heads/{branch}",
                old_object_id="0000000000000000000000000000000000000000",
            )],
            commits=[GitCommitRef(
                comment=commit_message,
                changes=[Change(
                    change_type="add",
                    item={"path": file_path},
                    new_content=ItemContent(content=content, content_type="rawtext"),
                )],
            )],
        )
        client.create_push(push, repository_id=repo_name, project=project)
        logger.info(f"[ado_adapter] [init_repo] Repo '{repo_name}' initialized with branch '{branch}'.")
        return f"Repo '{repo_name}' initialized with branch '{branch}' and file '{file_path}'."
    except Exception as e:
        logger.error(f"[ado_adapter] [init_repo] Failed. Error: {e}", exc_info=True)
        raise


# ── Branches ──────────────────────────────────────────────────────────────────

def ado_list_branches(project: str, repo_name: str) -> list[str]:
    logger.info(f"[ado_adapter] [list_branches] Listing branches in repo '{repo_name}', project '{project}'.")
    try:
        conn = get_ado_client()
        client = conn.clients.get_git_client()
        branches = client.get_branches(project=project, repository_id=repo_name)
        result = [b.name for b in branches]
        logger.info(f"[ado_adapter] [list_branches] Found {len(result)} branches in repo '{repo_name}'.")
        return result
    except Exception as e:
        logger.error(f"[ado_adapter] [list_branches] Failed to list branches in repo '{repo_name}', project '{project}'. Error: {e}", exc_info=True)
        raise


def ado_create_branch(project: str, repo_name: str, branch_name: str, source_branch: str) -> str:
    logger.info(f"[ado_adapter] [create_branch] Creating branch '{branch_name}' from '{source_branch}' in repo '{repo_name}', project '{project}'.")
    try:
        from azure.devops.v7_1.git.models import GitRefUpdate  # type: ignore
        conn = get_ado_client()
        client = conn.clients.get_git_client()
        refs = client.get_refs(repository_id=repo_name, project=project, filter=f"heads/{source_branch}")
        if not refs:
            logger.error(f"[ado_adapter] [create_branch] Source branch '{source_branch}' not found in repo '{repo_name}'.")
            return f"Source branch '{source_branch}' not found."
        old_sha = refs[0].object_id
        ref_update = GitRefUpdate(
            name=f"refs/heads/{branch_name}",
            old_object_id="0000000000000000000000000000000000000000",
            new_object_id=old_sha,
        )
        result = client.update_refs(ref_updates=[ref_update], repository_id=repo_name, project=project)
        if result:
            logger.info(f"[ado_adapter] [create_branch] Branch '{branch_name}' created successfully from '{source_branch}'.")
            return f"Branch '{branch_name}' created from '{source_branch}'."
        logger.error(f"[ado_adapter] [create_branch] ADO returned empty result when creating branch '{branch_name}' in repo '{repo_name}'.")
        return "Failed to create branch."
    except Exception as e:
        logger.error(f"[ado_adapter] [create_branch] Failed to create branch '{branch_name}' in repo '{repo_name}', project '{project}'. Error: {e}", exc_info=True)
        raise


# ── Commits ───────────────────────────────────────────────────────────────────

def ado_list_commits(project: str, repo_name: str, branch: str, top: int = 10) -> list[dict]:
    logger.info(f"[ado_adapter] [list_commits] Listing top {top} commits on branch '{branch}' in repo '{repo_name}', project '{project}'.")
    try:
        from azure.devops.v7_1.git.models import GitQueryCommitsCriteria  # type: ignore
        conn = get_ado_client()
        client = conn.clients.get_git_client()
        from azure.devops.v7_1.git.models import GitVersionDescriptor  # type: ignore
        criteria = GitQueryCommitsCriteria(item_version=GitVersionDescriptor(version=branch, version_type="branch"), top=top)
        commits = client.get_commits_batch(search_criteria=criteria, repository_id=repo_name, project=project)
        result = [{"sha": c.commit_id[:7], "message": c.comment.splitlines()[0], "author": c.author.name} for c in commits]
        logger.info(f"[ado_adapter] [list_commits] Retrieved {len(result)} commits from branch '{branch}' in repo '{repo_name}'.")
        return result
    except Exception as e:
        logger.error(f"[ado_adapter] [list_commits] Failed to list commits on branch '{branch}' in repo '{repo_name}', project '{project}'. Error: {e}", exc_info=True)
        raise


# ── File read/write ───────────────────────────────────────────────────────────

def ado_read_file(project: str, repo_name: str, path: str, branch: str = "main") -> str:
    logger.info(f"[ado_adapter] [read_file] Reading '{path}' from branch '{branch}' in repo '{repo_name}', project '{project}'.")
    try:
        from azure.devops.v7_1.git.models import GitVersionDescriptor  # type: ignore
        conn = get_ado_client()
        client = conn.clients.get_git_client()
        item = client.get_item(
            repository_id=repo_name, project=project,
            path=path, version_descriptor=GitVersionDescriptor(version=branch, version_type="branch"),
            include_content=True
        )
        logger.info(f"[ado_adapter] [read_file] Successfully read '{path}' from repo '{repo_name}'.")
        return item.content
    except Exception as e:
        logger.error(f"[ado_adapter] [read_file] Failed to read '{path}' from branch '{branch}' in repo '{repo_name}', project '{project}'. Error: {e}", exc_info=True)
        raise


def ado_commit_file(project: str, repo_name: str, branch: str, file_path: str, content: str, commit_message: str) -> str:
    logger.info(f"[ado_adapter] [commit_file] Committing '{file_path}' to branch '{branch}' in repo '{repo_name}', project '{project}'.")
    try:
        from azure.devops.v7_1.git.models import (  # type: ignore
            GitPush, GitCommitRef, Change, ItemContent, GitRefUpdate, GitVersionDescriptor
        )
        conn = get_ado_client()
        client = conn.clients.get_git_client()

        refs = client.get_refs(repository_id=repo_name, project=project, filter=f"heads/{branch}")
        if not refs:
            logger.error(f"[ado_adapter] [commit_file] Branch '{branch}' not found in repo '{repo_name}', project '{project}'.")
            return f"Branch '{branch}' not found."
        old_sha = refs[0].object_id

        try:
            client.get_item(repository_id=repo_name, project=project, path=file_path,
                            version_descriptor=GitVersionDescriptor(version=branch, version_type="branch"))
            change_type = "edit"
        except Exception:
            change_type = "add"

        logger.info(f"[ado_adapter] [commit_file] Change type for '{file_path}': {change_type}.")
        push = GitPush(
            ref_updates=[GitRefUpdate(name=f"refs/heads/{branch}", old_object_id=old_sha)],
            commits=[GitCommitRef(
                comment=commit_message,
                changes=[Change(
                    change_type=change_type,
                    item={"path": file_path},
                    new_content=ItemContent(content=content, content_type="rawtext"),
                )]
            )]
        )
        client.create_push(push, repository_id=repo_name, project=project)
        logger.info(f"[ado_adapter] [commit_file] Successfully committed '{file_path}' to branch '{branch}' in repo '{repo_name}'.")
        return f"File '{file_path}' {change_type}d on branch '{branch}'."
    except Exception as e:
        logger.error(f"[ado_adapter] [commit_file] Failed to commit '{file_path}' to branch '{branch}' in repo '{repo_name}', project '{project}'. Error: {e}", exc_info=True)
        raise


# ── Pull Requests ─────────────────────────────────────────────────────────────

def ado_create_pull_request(project: str, repo_name: str, title: str, description: str, source_branch: str, target_branch: str) -> dict:
    logger.info(f"[ado_adapter] [create_pull_request] Creating PR '{title}' from '{source_branch}' -> '{target_branch}' in repo '{repo_name}', project '{project}'.")
    try:
        from azure.devops.v7_1.git.models import GitPullRequest  # type: ignore
        conn = get_ado_client()
        client = conn.clients.get_git_client()
        pr = client.create_pull_request(
            git_pull_request_to_create=GitPullRequest(
                title=title,
                description=description,
                source_ref_name=f"refs/heads/{source_branch}",
                target_ref_name=f"refs/heads/{target_branch}",
            ),
            repository_id=repo_name,
            project=project,
        )
        logger.info(f"[ado_adapter] [create_pull_request] PR created successfully. ID: {pr.pull_request_id}, URL: {pr.url}")
        return {"id": pr.pull_request_id, "url": pr.url, "status": pr.status}
    except Exception as e:
        logger.error(f"[ado_adapter] [create_pull_request] Failed to create PR '{title}' in repo '{repo_name}', project '{project}'. Error: {e}", exc_info=True)
        raise


# ── Pipelines ─────────────────────────────────────────────────────────────────

def ado_list_pipelines(project: str) -> list[dict]:
    logger.info(f"[ado_adapter] [list_pipelines] Listing pipelines in project '{project}'.")
    try:
        conn = get_ado_client()
        client = conn.clients.get_pipelines_client()
        pipelines = client.list_pipelines(project=project)
        result = [{"id": p.id, "name": p.name, "folder": p.folder} for p in pipelines]
        logger.info(f"[ado_adapter] [list_pipelines] Found {len(result)} pipelines in project '{project}'.")
        return result
    except Exception as e:
        logger.error(f"[ado_adapter] [list_pipelines] Failed to list pipelines in project '{project}'. Error: {e}", exc_info=True)
        raise


def ado_run_pipeline(project: str, pipeline_id: int, branch: str = "main", variables: dict = None) -> dict:
    logger.info(f"[ado_adapter] [run_pipeline] Triggering pipeline ID {pipeline_id} on branch '{branch}' in project '{project}'.")
    try:
        from azure.devops.v7_1.pipelines.models import RunPipelineParameters, Variable  # type: ignore
        conn = get_ado_client()
        client = conn.clients.get_pipelines_client()
        params = RunPipelineParameters(
            resources={"repositories": {"self": {"ref_name": f"refs/heads/{branch}"}}},
            variables={k: Variable(value=v) for k, v in (variables or {}).items()},
        )
        run = client.run_pipeline(run_parameters=params, project=project, pipeline_id=pipeline_id)
        logger.info(f"[ado_adapter] [run_pipeline] Pipeline {pipeline_id} triggered. Run ID: {run.id}, State: {run.state}")
        url = run._links.links.get("web", {}).get("href") if (run._links and run._links.links) else None
        return {"run_id": run.id, "state": run.state, "url": url}
    except Exception as e:
        logger.error(f"[ado_adapter] [run_pipeline] Failed to trigger pipeline ID {pipeline_id} in project '{project}'. Error: {e}", exc_info=True)
        raise


def ado_get_pipeline_run(project: str, pipeline_id: int, run_id: int) -> dict:
    logger.info(f"[ado_adapter] [get_pipeline_run] Fetching run ID {run_id} for pipeline {pipeline_id} in project '{project}'.")
    try:
        conn = get_ado_client()
        client = conn.clients.get_pipelines_client()
        run = client.get_run(project=project, pipeline_id=pipeline_id, run_id=run_id)
        logger.info(f"[ado_adapter] [get_pipeline_run] Run {run_id} state: {run.state}, result: {run.result}")
        url = run._links.links.get("web", {}).get("href") if (run._links and run._links.links) else None
        return {"run_id": run.id, "state": run.state, "result": run.result, "url": url}
    except Exception as e:
        logger.error(f"[ado_adapter] [get_pipeline_run] Failed to fetch run ID {run_id} for pipeline {pipeline_id} in project '{project}'. Error: {e}", exc_info=True)
        raise


import time

def ado_wait_for_pipeline_run(
    project: str,
    pipeline_id: int,
    run_id: int,
    poll_interval: int = 15,
    timeout: int = 1800,
) -> dict:
    logger.info(
        f"[ado_adapter] [wait_for_pipeline_run] Polling run {run_id} for pipeline {pipeline_id} "
        f"in project '{project}' (interval={poll_interval}s, timeout={timeout}s)."
    )
    start_time = time.monotonic()
    try:
        while True:
            run = ado_get_pipeline_run(project=project, pipeline_id=pipeline_id, run_id=run_id)
            state = run.get("state")
            logger.info(f"[ado_adapter] [wait_for_pipeline_run] Run {run_id} state='{state}'.")

            if state == "completed":
                logger.info(
                    f"[ado_adapter] [wait_for_pipeline_run] Run {run_id} completed "
                    f"with result='{run.get('result')}'."
                )
                return run

            if time.monotonic() - start_time > timeout:
                logger.error(
                    f"[ado_adapter] [wait_for_pipeline_run] Timed out after {timeout}s waiting for run {run_id}."
                )
                raise TimeoutError(f"Timed out after {timeout}s waiting for pipeline run {run_id} to complete.")

            time.sleep(poll_interval)
    except Exception as e:
        logger.error(f"[ado_adapter] [wait_for_pipeline_run] Failed. Error: {e}", exc_info=True)
        raise


# ── Work Items ────────────────────────────────────────────────────────────────

def ado_create_work_item(project: str, work_item_type: str, title: str, description: str = None) -> dict:
    logger.info(f"[ado_adapter] [create_work_item] Creating '{work_item_type}' work item '{title}' in project '{project}'.")
    try:
        from azure.devops.v7_1.work_item_tracking.models import JsonPatchOperation  # type: ignore
        conn = get_ado_client()
        client = conn.clients.get_work_item_tracking_client()
        patch = [JsonPatchOperation(op="add", path="/fields/System.Title", value=title)]
        if description:
            patch.append(JsonPatchOperation(op="add", path="/fields/System.Description", value=description))
        item = client.create_work_item(document=patch, project=project, type=work_item_type)
        logger.info(f"[ado_adapter] [create_work_item] Work item created. ID: {item.id}, State: {item.fields.get('System.State')}")
        return {"id": item.id, "url": item.url, "state": item.fields.get("System.State")}
    except Exception as e:
        logger.error(f"[ado_adapter] [create_work_item] Failed to create '{work_item_type}' work item '{title}' in project '{project}'. Error: {e}", exc_info=True)
        raise


def ado_get_work_item(work_item_id: int) -> dict:
    logger.info(f"[ado_adapter] [get_work_item] Fetching work item ID {work_item_id}.")
    try:
        conn = get_ado_client()
        client = conn.clients.get_work_item_tracking_client()
        item = client.get_work_item(id=work_item_id)
        logger.info(f"[ado_adapter] [get_work_item] Work item {work_item_id} fetched. Title: {item.fields.get('System.Title')}, State: {item.fields.get('System.State')}")
        return {"id": item.id, "title": item.fields.get("System.Title"), "state": item.fields.get("System.State"), "url": item.url}
    except Exception as e:
        logger.error(f"[ado_adapter] [get_work_item] Failed to fetch work item ID {work_item_id}. Error: {e}", exc_info=True)
        raise


# ── Create Pipeline ──────────────────────────────────────────────────────────

def ado_create_pipeline(project: str, name: str, repo_name: str, yaml_path: str,
                        branch: str = "main", folder: str = "\\") -> dict:
    logger.info(f"[ado_adapter] [create_pipeline] Creating pipeline '{name}' in project '{project}', repo '{repo_name}', yaml='{yaml_path}'.")
    try:
        from azure.devops.v7_1.build.models import BuildDefinition, BuildRepository, AgentPoolQueue  # type: ignore
        conn = get_ado_client()
        git_client = conn.clients.get_git_client()
        repos = git_client.get_repositories(project)
        repo = next((r for r in repos if r.name.lower() == repo_name.lower()), None)
        if not repo:
            return {"error": f"Repository '{repo_name}' not found in project '{project}'."}
        definition = BuildDefinition(
            name=name,
            path=folder,
            repository=BuildRepository(
                id=repo.id,
                name=repo.name,
                type="TfsGit",
                default_branch=f"refs/heads/{branch}",
            ),
            process={"type": 2, "yamlFilename": yaml_path},
            queue=AgentPoolQueue(name="Azure Pipelines"),
        )
        build_client = conn.clients.get_build_client()
        result = build_client.create_definition(definition=definition, project=project)
        logger.info(f"[ado_adapter] [create_pipeline] Pipeline '{name}' created. ID: {result.id}")
        return {"id": result.id, "name": result.name, "path": result.path, "url": result.url}
    except Exception as e:
        logger.error(f"[ado_adapter] [create_pipeline] Failed. Error: {e}", exc_info=True)
        raise


# ── Dispatch ─────────────────────────────────────────────────────────────────

def ado_dispatch_pipeline(project: str, pipeline_name: str, branch: str = "main", variables: dict = None) -> dict:
    """Trigger a pipeline by name (resolves ID automatically)."""
    logger.info(f"[ado_adapter] [dispatch_pipeline] Dispatching pipeline '{pipeline_name}' on branch '{branch}' in project '{project}'.")
    try:
        pipelines = ado_list_pipelines(project)
        match = next((p for p in pipelines if p["name"].lower() == pipeline_name.lower()), None)
        if not match:
            return {"error": f"Pipeline '{pipeline_name}' not found in project '{project}'."}
        return ado_run_pipeline(project=project, pipeline_id=match["id"], branch=branch, variables=variables)
    except Exception as e:
        logger.error(f"[ado_adapter] [dispatch_pipeline] Failed. Error: {e}", exc_info=True)
        raise


def ado_approve_pipeline_run(project: str, approval_id: str, comment: str = "Approved by agent") -> dict:
    """Approve a pending pipeline run gate/approval."""
    logger.info(f"[ado_adapter] [approve_pipeline_run] Approving approval ID '{approval_id}' in project '{project}'.")
    try:
        import requests
        conn = get_ado_client()
        org_url = os.environ["ADO_ORG_URL"].rstrip("/")
        session = conn.authentication_handler.signed_session()
        url = f"{org_url}/{project}/_apis/pipelines/approvals/{approval_id}?api-version=7.1-preview.1"
        payload = [{"approvalId": approval_id, "status": "approved", "comment": comment}]
        resp = session.patch(url, json=payload)
        resp.raise_for_status()
        logger.info(f"[ado_adapter] [approve_pipeline_run] Approval '{approval_id}' approved.")
        return resp.json()
    except Exception as e:
        logger.error(f"[ado_adapter] [approve_pipeline_run] Failed. Error: {e}", exc_info=True)
        raise


# ── Monitoring ────────────────────────────────────────────────────────────────

def ado_list_pipeline_runs(project: str, pipeline_id: int, top: int = 10) -> list[dict]:
    logger.info(f"[ado_adapter] [list_pipeline_runs] Listing last {top} runs for pipeline {pipeline_id} in project '{project}'.")
    try:
        conn = get_ado_client()
        client = conn.clients.get_pipelines_client()
        runs = client.list_runs(project=project, pipeline_id=pipeline_id)
        result = [
            {"run_id": r.id, "name": r.name, "state": r.state, "result": r.result,
             "created_date": str(r.created_date), "url": r._links.links.get("web", {}).get("href") if (r._links and r._links.links) else None}
            for r in list(runs)[:top]
        ]
        logger.info(f"[ado_adapter] [list_pipeline_runs] Retrieved {len(result)} runs.")
        return result
    except Exception as e:
        logger.error(f"[ado_adapter] [list_pipeline_runs] Failed. Error: {e}", exc_info=True)
        raise



def ado_get_pipeline_logs(project: str, pipeline_id: int, run_id: int) -> list[dict]:
    logger.info(f"[ado_adapter] [get_pipeline_logs] Fetching logs for run {run_id}, pipeline {pipeline_id}, project '{project}'.")
    try:
        conn = get_ado_client()
        client = conn.clients.get_pipelines_client()
        logs = client.list_logs(project=project, pipeline_id=pipeline_id, run_id=run_id)
        result = [{"log_id": l.id, "url": l.url} for l in (logs.logs or [])]
        logger.info(f"[ado_adapter] [get_pipeline_logs] Retrieved {len(result)} log entries.")
        return result
    except Exception as e:
        logger.error(f"[ado_adapter] [get_pipeline_logs] Failed. Error: {e}", exc_info=True)
        raise


def ado_get_build_timeline(project: str, build_id: int) -> list[dict]:
    logger.info(f"[ado_adapter] [get_build_timeline] Fetching timeline for build {build_id} in project '{project}'.")
    try:
        conn = get_ado_client()
        client = conn.clients.get_build_client()
        timeline = client.get_build_timeline(project=project, build_id=build_id)
        if timeline is None:
            logger.warning(f"[ado_adapter] [get_build_timeline] No timeline found for build {build_id} in project '{project}'.")
            return []
        result = [
            {"id": r.id, "name": r.name, "type": r.type, "state": r.state,
             "result": r.result, "start_time": str(r.start_time), "finish_time": str(r.finish_time)}
            for r in (timeline.records or [])
        ]
        logger.info(f"[ado_adapter] [get_build_timeline] Retrieved {len(result)} timeline records.")
        return result
    except Exception as e:
        logger.error(f"[ado_adapter] [get_build_timeline] Failed. Error: {e}", exc_info=True)
        raise


# ── File Search ──────────────────────────────────────────────────────────────

def ado_find_files(project: str, repo_name: str, branch: str = "main",
                   pattern: str = None, extensions: list[str] = None,
                   scope_path: str = "/") -> list[dict]:
    """Find files in a repo by regex pattern and/or file extensions."""
    import re
    logger.info(f"[ado_adapter] [find_files] project='{project}', repo='{repo_name}', branch='{branch}', pattern='{pattern}', extensions={extensions}, scope='{scope_path}'")
    try:
        from azure.devops.v7_1.git.models import GitVersionDescriptor  # type: ignore
        conn = get_ado_client()
        client = conn.clients.get_git_client()
        items = client.get_items(
            repository_id=repo_name, project=project,
            scope_path=scope_path, recursion_level="full",
            version_descriptor=GitVersionDescriptor(version=branch, version_type="branch"),
        )
        compiled = re.compile(pattern) if pattern else None
        exts = [e.lower() if e.startswith(".") else f".{e.lower()}" for e in (extensions or [])]
        results = []
        for item in items:
            if item.is_folder:
                continue
            path = item.path
            if exts and not any(path.lower().endswith(e) for e in exts):
                continue
            if compiled and not compiled.search(path):
                continue
            results.append({"path": path, "url": item.url})
        logger.info(f"[ado_adapter] [find_files] Found {len(results)} matching files.")
        return results
    except Exception as e:
        logger.error(f"[ado_adapter] [find_files] Failed. Error: {e}", exc_info=True)
        raise


# ── Variable Groups ───────────────────────────────────────────────────────────

def _ado_update_variable_group(conn, project: str, group_name: str, variables: dict) -> str:
    """Internal helper: fetch group by exact name, merge variables dict, push update. Never call with secret values from agent."""
    from azure.devops.v7_1.task_agent.models import VariableGroupParameters, VariableGroupProjectReference, ProjectReference  # type: ignore
    core_client = conn.clients.get_core_client()
    project_obj = core_client.get_project(project)
    client = conn.clients.get_task_agent_client()
    groups = client.get_variable_groups(project=project, group_name=group_name)
    if not groups:
        raise ValueError(f"Variable group '{group_name}' not found in project '{project}'.")
    # groupName filter is a contains match — enforce exact name
    group = next((g for g in groups if g.name == group_name), None)
    if group is None:
        raise ValueError(f"Variable group '{group_name}' not found in project '{project}' (found: {[g.name for g in groups]}).")
    # Re-fetch by ID to get the freshest copy
    group = client.get_variable_group(project=project, group_id=group.id)
    # Convert existing variables to plain dicts to avoid v7_0/v7_1 model mismatch
    merged = {
        k: {"value": v.value, "isSecret": v.is_secret}
        for k, v in (group.variables or {}).items()
    }
    # Overlay the new/updated variables (also as plain dicts)
    for k, v in variables.items():
        merged[k] = {"value": v.value, "isSecret": v.is_secret}
    params = VariableGroupParameters(
        name=group.name,
        description=group.description,
        type=group.type,
        provider_data=group.provider_data,
        variables=merged,
        variable_group_project_references=[
            VariableGroupProjectReference(
                name=group.name,
                description=group.description,
                project_reference=ProjectReference(id=project_obj.id, name=project_obj.name),
            )
        ],
    )
    client.update_variable_group(variable_group_parameters=params, group_id=group.id)
    return group.name


def ado_set_pipeline_variable(project: str, group_name: str, var_name: str, var_value: str, is_secret: bool = False) -> str:
    logger.info(f"[ado_adapter] [set_pipeline_variable] Setting variable '{var_name}' in group '{group_name}', project '{project}'. is_secret={is_secret}")
    try:
        from azure.devops.v7_1.task_agent.models import VariableValue  # type: ignore
        conn = get_ado_client()
        _ado_update_variable_group(conn, project, group_name, {var_name: VariableValue(value=var_value, is_secret=is_secret)})
        logger.info(f"[ado_adapter] [set_pipeline_variable] Variable '{var_name}' set in group '{group_name}'.")
        return f"Variable '{var_name}' set in group '{group_name}'."
    except Exception as e:
        logger.error(f"[ado_adapter] [set_pipeline_variable] Failed. project='{project}', group='{group_name}', var='{var_name}'. Error: {e}", exc_info=True)
        raise


def ado_sync_kv_secret_to_pipeline_variable(
    project: str,
    group_name: str,
    kv_secret_name: str,
    var_name: str | None = None,
    vault_name: str | None = None,
    is_secret: bool = True,
) -> str:
    """Read a secret from Key Vault and write it as a pipeline variable. Secret value never leaves this function."""
    from azure.devops.v7_1.task_agent.models import VariableValue  # type: ignore
    resolved_var_name = var_name or kv_secret_name
    vault = vault_name or _vault_name_from_env()
    logger.info(f"[ado_adapter] [sync_kv_secret_to_pipeline_variable] Syncing KV secret '{kv_secret_name}' -> variable '{resolved_var_name}' in group '{group_name}', project '{project}', is_secret={is_secret}.")
    try:
        value = ado_get_keyvault_secret(kv_secret_name, vault)
        conn = get_ado_client()
        _ado_update_variable_group(conn, project, group_name, {resolved_var_name: VariableValue(value=value, is_secret=is_secret)})
        del value
        logger.info(f"[ado_adapter] [sync_kv_secret_to_pipeline_variable] Secret '{kv_secret_name}' synced as variable '{resolved_var_name}' in group '{group_name}'.")
        return f"Secret '{kv_secret_name}' from vault '{vault}' set as {'secret' if is_secret else 'non-secret'} variable '{resolved_var_name}' in group '{group_name}'."
    except Exception as e:
        logger.error(f"[ado_adapter] [sync_kv_secret_to_pipeline_variable] Failed. project='{project}', group='{group_name}', secret='{kv_secret_name}'.")
        raise


# ── Key Vault & GitHub Secrets ────────────────────────────────────────────────

def ado_list_keyvault_secrets(vault_name: str | None = None) -> list[str]:
    """List all secret names from an Azure Key Vault."""
    from vida.utils.AzureSecretsV2 import KeyVaultManager  # type: ignore
    name = vault_name or _vault_name_from_env()
    logger.info(f"[ado_adapter] [list_keyvault_secrets] Listing secrets from vault '{name}'.")
    try:
        result = KeyVaultManager(name).list_secrets()
        logger.info(f"[ado_adapter] [list_keyvault_secrets] Found {len(result)} secrets.")
        return result
    except Exception as e:
        logger.error(f"[ado_adapter] [list_keyvault_secrets] Failed. Error: {e}", exc_info=True)
        raise


def ado_get_keyvault_secret(secret_name: str, vault_name: str | None = None) -> str:
    """Retrieve a secret value from an Azure Key Vault. Internal use only — never return to agent."""
    from vida.utils.AzureSecretsV2 import KeyVaultManager  # type: ignore
    name = vault_name or _vault_name_from_env()
    logger.info(f"[ado_adapter] [get_keyvault_secret] Fetching secret '{secret_name}' from vault '{name}'.")
    try:
        value = KeyVaultManager(name).get_secret(secret_name)
        print(f"[ado_adapter] [get_keyvault_secret] Secret '{secret_name}' retrieved from vault '{name}'.")
        if value is None:
            raise ValueError(f"Secret '{secret_name}' not found in vault '{name}'.")
        logger.info(f"[ado_adapter] [get_keyvault_secret] Secret '{secret_name}' retrieved.")
        return value
    except Exception as e:
        logger.error(f"[ado_adapter] [get_keyvault_secret] Failed to retrieve secret '{secret_name}' from vault '{name}'.")
        raise


def ado_sync_secret_to_keyvault(
    secret_name: str,
    target_vault_name: str,
    source_vault_name: str | None = None,
    override_value: str | None = None,
) -> str:
    """Copy a secret from the source Key Vault (or use override_value) into a target Key Vault."""
    from vida.utils.AzureSecretsV2 import KeyVaultManager  # type: ignore
    src_name = source_vault_name or _vault_name_from_env()
    logger.info(f"[ado_adapter] [sync_secret_to_keyvault] Syncing '{secret_name}' from '{src_name}' -> '{target_vault_name}'.")
    try:
        value = override_value or KeyVaultManager(src_name).get_secret(secret_name)
        if value is None:
            raise ValueError(f"Secret '{secret_name}' not found in source vault '{src_name}'.")
        KeyVaultManager(target_vault_name).set_secret(secret_name, value)
        logger.info(f"[ado_adapter] [sync_secret_to_keyvault] Secret '{secret_name}' synced to '{target_vault_name}'.")
        return f"Secret '{secret_name}' synced to vault '{target_vault_name}'."
    except Exception as e:
        logger.error(f"[ado_adapter] [sync_secret_to_keyvault] Failed to sync secret '{secret_name}' to '{target_vault_name}'.")
        raise


async def ado_sync_secret_to_github_repo(
    repo: str,
    secret_name: str,
    source_vault_name: str | None = None,
    override_value: str | None = None,
) -> str:
    """Read a secret from Azure Key Vault and upsert it as a GitHub Actions repo secret."""
    from vida.utils.AzureSecretsV2 import KeyVaultManager  # type: ignore
    from vida.adapters.github.git_write import set_github_secret  # type: ignore
    src_name = source_vault_name or _vault_name_from_env()
    # KV uses hyphens; GitHub secrets require underscores
    kv_secret_name = secret_name
    github_secret_name = secret_name.replace("-", "_")
    logger.info(f"[ado_adapter] [sync_secret_to_github_repo] Syncing '{kv_secret_name}' (KV) -> '{github_secret_name}' (GitHub) on repo '{repo}'.")
    try:
        value = override_value or KeyVaultManager(src_name).get_secret(kv_secret_name)
        if value is None:
            raise ValueError(f"Secret '{kv_secret_name}' not found in source vault '{src_name}'.")
        await set_github_secret(repo_full_name=repo, secret_name=github_secret_name, secret_value=value)
        logger.info(f"[ado_adapter] [sync_secret_to_github_repo] Secret '{kv_secret_name}' synced as '{github_secret_name}' to GitHub repo '{repo}'.")
        return f"Secret '{kv_secret_name}' synced as '{github_secret_name}' to GitHub repo '{repo}'."
    except Exception as e:
        logger.error(f"[ado_adapter] [sync_secret_to_github_repo] Failed to sync secret '{kv_secret_name}' to repo '{repo}'.")
        raise


def ado_sync_secret_to_github_org(
    org: str,
    secret_name: str,
    source_vault_name: str | None = None,
    override_value: str | None = None,
    visibility: str = "all",
) -> str:
    """Read a secret from Azure Key Vault and upsert it as a GitHub Actions org-level secret."""
    from vida.utils.AzureSecretsV2 import KeyVaultManager  # type: ignore
    from vida.adapters.github.git_write import org_create_or_update_secret  # type: ignore
    src_name = source_vault_name or _vault_name_from_env()
    kv_secret_name = secret_name
    github_secret_name = secret_name.replace("-", "_")
    logger.info(f"[ado_adapter] [sync_secret_to_github_org] Syncing '{kv_secret_name}' (KV) -> '{github_secret_name}' (GitHub) on org '{org}'.")
    try:
        value = override_value or KeyVaultManager(src_name).get_secret(kv_secret_name)
        if value is None:
            raise ValueError(f"Secret '{kv_secret_name}' not found in source vault '{src_name}'.")
        org_create_or_update_secret(name=github_secret_name, value=value, org_name=org, visibility=visibility)
        logger.info(f"[ado_adapter] [sync_secret_to_github_org] Secret '{kv_secret_name}' synced as '{github_secret_name}' to GitHub org '{org}'.")
        return f"Secret '{kv_secret_name}' synced as '{github_secret_name}' to GitHub org '{org}' (visibility='{visibility}')."
    except Exception as e:
        logger.error(f"[ado_adapter] [sync_secret_to_github_org] Failed to sync secret '{kv_secret_name}' to org '{org}'.")
        raise


def ado_list_github_repo_secrets(repo: str) -> list[dict]:
    """List all GitHub Actions secrets (name + timestamps) for a repo."""
    from vida.adapters.github.git_read import list_git_secrets  # type: ignore
    logger.info(f"[ado_adapter] [list_github_repo_secrets] Listing secrets for repo '{repo}'.")
    try:
        result = list_git_secrets(repo_name=repo)
        logger.info(f"[ado_adapter] [list_github_repo_secrets] Found {len(result)} secrets.")
        return result
    except Exception as e:
        logger.error(f"[ado_adapter] [list_github_repo_secrets] Failed. Error: {e}", exc_info=True)
        raise


def ado_list_github_org_secrets(org: str) -> list[dict]:
    """List all GitHub Actions secrets for an org."""
    from vida.adapters.github.git_read import org_get_all_secrets  # type: ignore
    logger.info(f"[ado_adapter] [list_github_org_secrets] Listing secrets for org '{org}'.")
    try:
        result = org_get_all_secrets(org_name=org)
        logger.info(f"[ado_adapter] [list_github_org_secrets] Found {len(result)} secrets.")
        return result
    except Exception as e:
        logger.error(f"[ado_adapter] [list_github_org_secrets] Failed. Error: {e}", exc_info=True)
        raise


def ado_sync_kv_to_github_repo_variable(
    repo: str,
    kv_secret_name: str,
    var_name: str | None = None,
    vault_name: str | None = None,
) -> str:
    """Read a secret from Key Vault and upsert it as a GitHub Actions repo variable. Value never exposed to agent."""
    from vida.adapters.github.git_write import repo_create_or_update_variable  # type: ignore
    src_name = vault_name or _vault_name_from_env()
    github_var_name = (var_name or kv_secret_name).replace("-", "_")
    logger.info(f"[ado_adapter] [sync_kv_to_github_repo_variable] Syncing KV secret '{kv_secret_name}' -> GitHub variable '{github_var_name}' on repo '{repo}'.")
    try:
        value = ado_get_keyvault_secret(kv_secret_name, src_name)
        repo_create_or_update_variable(name=github_var_name, value=value, repo_name=repo)
        del value
        logger.info(f"[ado_adapter] [sync_kv_to_github_repo_variable] Variable '{github_var_name}' set on repo '{repo}'.")
        return f"KV secret '{kv_secret_name}' set as GitHub variable '{github_var_name}' on repo '{repo}'."
    except Exception as e:
        logger.error(f"[ado_adapter] [sync_kv_to_github_repo_variable] Failed. repo='{repo}', kv_secret='{kv_secret_name}'.")
        raise


def ado_sync_kv_to_github_org_variable(
    org: str,
    kv_secret_name: str,
    var_name: str | None = None,
    vault_name: str | None = None,
    visibility: str = "all",
) -> str:
    """Read a secret from Key Vault and upsert it as a GitHub Actions org variable. Value never exposed to agent."""
    from vida.adapters.github.git_write import org_create_or_update_variable  # type: ignore
    src_name = vault_name or _vault_name_from_env()
    github_var_name = (var_name or kv_secret_name).replace("-", "_")
    logger.info(f"[ado_adapter] [sync_kv_to_github_org_variable] Syncing KV secret '{kv_secret_name}' -> GitHub variable '{github_var_name}' on org '{org}'.")
    try:
        value = ado_get_keyvault_secret(kv_secret_name, src_name)
        org_create_or_update_variable(name=github_var_name, value=value, org_name=org, visibility=visibility)
        del value
        logger.info(f"[ado_adapter] [sync_kv_to_github_org_variable] Variable '{github_var_name}' set on org '{org}'.")
        return f"KV secret '{kv_secret_name}' set as GitHub variable '{github_var_name}' on org '{org}' (visibility='{visibility}')."
    except Exception as e:
        logger.error(f"[ado_adapter] [sync_kv_to_github_org_variable] Failed. org='{org}', kv_secret='{kv_secret_name}'.")
        raise


def _vault_name_from_env() -> str:
    """Derive Key Vault name from Azure_Secrets_URL env var."""
    url = os.environ.get("Azure_Secrets_URL", "")
    if not url:
        raise EnvironmentError("Azure_Secrets_URL is not set and no vault_name was provided.")
    # https://<vault-name>.vault.azure.net/ -> <vault-name>
    return url.rstrip("/").split("//")[-1].split(".")[0]