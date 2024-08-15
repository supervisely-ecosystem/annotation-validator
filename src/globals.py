import os
import supervisely as sly
from dotenv import load_dotenv

if sly.is_development():
    load_dotenv("local.env")
    load_dotenv(os.path.expanduser("~/supervisely.env"))


def _get_tag_name():
    action = os.environ.get("modal.state.action")
    if action == "tag":
        tag_name = os.environ.get("modal.state.tagName", None)
        if tag_name is None or tag_name == "":
            tag_name = "need validation"
    elif action == "del":
        tag_name = None
    elif action is None:
        raise ValueError("Action cannot be obtained from environment.")
    return tag_name


api = sly.Api()

project_id = sly.env.project_id()
dataset_id = sly.env.dataset_id(raise_not_found=False)
workspace_id = sly.env.workspace_id()
task_id = sly.env.task_id()
tag_name = _get_tag_name()

team_id = api.project.get_info_by_id(project_id).team_id
team_members = api.user.get_team_members(team_id)
user_self_login = api.user.get_my_info()
