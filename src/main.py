import os

import supervisely as sly
from dotenv import load_dotenv

import src.functions as f

if sly.is_development():
    load_dotenv("local.env")
    load_dotenv(os.path.expanduser("~/supervisely.env"))


def main():
    api = sly.Api()

    # env variables
    project_id = sly.env.project_id()
    dataset_id = sly.env.dataset_id(raise_not_found=False)
    action = os.environ.get('modal.state.action')
    if action=="tag":
        tag_name = os.environ.get('modal.state.tagName', 'need validation')
    else:
        tag_name = None 

    # get source project and datasets tree
    src_project = api.project.get_info_by_id(project_id, raise_error=True)
    datasets_tree = api.dataset.get_tree(project_id)
    if dataset_id:
        datasets_tree = f.find_destination_dataset_tree(datasets_tree, dataset_id)

    if not datasets_tree:
        raise ValueError("Destination dataset not found")

    # create destination project
    new_project_name = f.new_project_name(src_project.name)
    dst_project = api.project.create(
        sly.env.workspace_id(), new_project_name, change_name_if_conflict=True
    )

    # prepare destination project meta
    meta = sly.ProjectMeta.from_json(api.project.get_meta(src_project.id))
    if tag_name is not None:
        meta = meta.add_tag_meta(sly.TagMeta(tag_name, sly.TagValueType.NONE))
        meta = api.project.update_meta(dst_project.id, meta)

    # process datasets
    for src_ds, children in datasets_tree.items():
        f.process_ds_recursive(api, dst_project.id, meta, src_ds, tag_name, children)

    # set project to task output
    api.task.set_output_project(sly.env.task_id(), dst_project.id)


if __name__ == "__main__":
    sly.main_wrapper("main", f.run_func_and_catch_exceptions(main))
