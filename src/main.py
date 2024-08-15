import os

import supervisely as sly
from dotenv import load_dotenv

import src.functions as f
import src.globals as g


def main():
    # get source project and datasets tree
    src_project = g.api.project.get_info_by_id(g.project_id, raise_error=True)
    datasets_tree = g.api.dataset.get_tree(g.project_id)
    if g.dataset_id:
        datasets_tree = f.find_destination_dataset_tree(datasets_tree, g.dataset_id)

    if not datasets_tree:
        raise ValueError("Destination dataset not found")

    # create destination project
    new_project_name = f.new_project_name(src_project.name)
    dst_project = g.api.project.create(
        g.workspace_id, new_project_name, change_name_if_conflict=True
    )

    # prepare destination project meta
    meta = sly.ProjectMeta.from_json(g.api.project.get_meta(src_project.id))
    if g.tag_name is not None:
        meta = meta.add_tag_meta(sly.TagMeta(g.tag_name, sly.TagValueType.NONE))
    meta = g.api.project.update_meta(dst_project.id, meta)

    # process datasets
    for src_ds, children in datasets_tree.items():
        f.process_ds_recursive(g.api, dst_project.id, meta, src_ds, g.tag_name, children)

    # set project to task output
    g.api.task.set_output_project(g.task_id, dst_project.id)


if __name__ == "__main__":
    sly.main_wrapper("main", f.run_func_and_catch_exceptions, main)
