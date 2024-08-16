import os
import supervisely as sly
from dotenv import load_dotenv

if sly.is_development():
    load_dotenv("local.env")
    load_dotenv(os.path.expanduser("~/supervisely.env"))


def _get_tag_name():
    use_tag = bool(os.environ.get("modal.state.tag"))
    if use_tag:
        tag_name = os.environ.get("modal.state.tagName", None)
        if tag_name is None or tag_name == "":
            tag_name = "Invalid Annotation"
        return tag_name
    else:
        return None


api = sly.Api()

project_id = sly.env.project_id()
dataset_id = sly.env.dataset_id(raise_not_found=False)
workspace_id = sly.env.workspace_id()
task_id = sly.env.task_id()
tag_name = _get_tag_name()

team_id = api.project.get_info_by_id(project_id).team_id
team_members = [user.login for user in api.user.get_team_members(team_id)]
user_self_login = api.user.get_my_info()
