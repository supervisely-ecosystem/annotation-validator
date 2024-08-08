import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from typing import Callable, Dict, Optional, Tuple

import supervisely as sly
from src.validation_functions import get_validation_func
from src.correction_functions import get_correction_func


def validate_annotation(ann_json: Dict, meta: sly.ProjectMeta, tag_id: Optional[int] = None) -> Tuple[bool, Dict]:
    """Main function to validate annotation and add tag to invalid objects"""

    def _deserialization_check(obj, meta):
        try:
            label_obj = sly.Label.from_json(obj, meta)
            if label_obj is not None:
                return True
        except Exception as e:
            sly.logger.warning(
                f"Object (id: {obj["id"]}) deserialization failed. Exception message: {repr(e)}",
                exc_info=True,
            )
        return False

    tags_to_add = []
    geometries_figure_ids = []
    geometries_list = []
    for obj in ann_json.get("objects", []):
        geometry_type = obj.get("geometryType", "")
        object_id = obj.get('id', None)
        if object_id is None:
            sly.logger.error(f'Figure ID not found. Object: {obj}')
            continue # or raise KeyError?
        
        validation_func = get_validation_func(geometry_type)
        correction_func = get_correction_func(geometry_type)

        if not _deserialization_check(obj, meta) or (validation_func and not validation_func(obj)):
            if tag_id:
                tag_fig_dict = {"figureId": object_id, "tagId": tag_id}
                tags_to_add.append(tag_fig_dict)
            else:
                if correction_func:
                    obj = correction_func(obj)
                    sly.logger.info(
                        f"Autocorrecting the object (id: {obj.id}, geometry: {geometry_type})"
                    )
                    geometries_figure_ids.append(object_id)
                    geometries_list.append(obj)
                else:
                    info = f"Geometry type: {geometry_type}, object id: {object_id}"
                    sly.logger.warning(f"Unable to autocorrect faulty annotation object. Skipping...", extra={'info': info})

    return tags_to_add, geometries_figure_ids, geometries_list


def new_project_name(name: str) -> str:
    """Generate destination project name"""

    suffix = "validated"
    return f"{name} ({suffix})" if " " in name else f"{name}_{suffix}"


def find_destination_dataset_tree(tree: Dict, needed_dataset_id: int) -> Optional[Dict]:
    """Find destination dataset tree by dataset id"""

    for dataset_info, children in tree.items():
        if dataset_info.id == needed_dataset_id:
            return {dataset_info: children}

        if children:
            return find_destination_dataset_tree(children, needed_dataset_id)
    return None


################### Old version of process_ds function #############################################
####################################################################################################
# def process_ds(api, dst_ds, meta, src_ds, tag_name):
#     images_count = src_ds.images_count
#     pbar_cb = sly.Progress(f"Processing '{src_ds.name}' dataset", images_count).iters_done

#     # iterate by generator to avoid memory overflow
#     for batch_imgs in api.image.get_list_generator(src_ds.id, batch_size=500):

#         dst_imgs = api.image.copy_batch_optimized(src_ds.id, batch_imgs, dst_ds.id)
#         dst_imgs_ids = [image_info.id for image_info in dst_imgs]

#         for batch_ids in sly.batched(dst_imgs_ids):
#             batch_ann_json = api.annotation.download_json_batch(dst_ds.id, batch_ids)

#             anns_to_upload = {}
#             for image_id, ann_json in zip(batch_ids, batch_ann_json):
#                 is_valid, validated_ann = validate_annotation(ann_json, meta, tag_name)
#                 if not is_valid:
#                     anns_to_upload[image_id] = validated_ann

#             if anns_to_upload:
#                 api.annotation.upload_jsons(
#                     list(anns_to_upload.keys()),
#                     list(anns_to_upload.values()),
#                 )
#             pbar_cb(len(batch_ids))
####################################################################################################


def process_ds(
    api: sly.Api,
    dst_ds: sly.Dataset,
    meta: sly.ProjectMeta,
    src_ds: sly.Dataset,
    tag_name: str,
) -> None:
    """
    Process dataset.
    Download annotations, validate them.
    If some labels are invalid, add tag to them and upload back to Supervisely
    """
    if tag_name:
        tag_meta = meta.get_tag_meta(tag_name)
        tag_id = tag_meta.sly_id
    else:
        tag_id = None
    images_count = src_ds.images_count
    pbar_cb = sly.Progress(f"Processing '{src_ds.name}' dataset", images_count).iters_done_report

    # iterate by generator to avoid memory overflow
    for batch_imgs in api.image.get_list_generator(src_ds.id, batch_size=500):
        download_executor = ThreadPoolExecutor(max_workers=10)
        upload_executor = ThreadPoolExecutor(max_workers=4)
        try:
            is_downloading: Dict[int, bool] = {}
            is_processing: Dict[int, bool] = {}
            is_uploading: Dict[int, bool] = {}
            ann_cache = {}
            anns_to_upload: Dict[int, Dict] = defaultdict(dict)
            dst_imgs = api.image.copy_batch_optimized(src_ds.id, batch_imgs, dst_ds.id)
            dst_imgs_ids = [image_info.id for image_info in dst_imgs]

            def _download_annotations(idx, img_ids):
                if idx in is_downloading and is_downloading[idx]:
                    sly.logger.info(f"Waiting for annotation batch {idx} to be downloaded")
                    while is_downloading[idx]:
                        time.sleep(0.1)
                if idx not in ann_cache:
                    sly.logger.info(f"Downloading annotation batch {idx}")
                    is_downloading[idx] = True
                    ann_cache[idx] = api.annotation.download_json_batch(dst_ds.id, img_ids)
                    is_downloading[idx] = False
                return ann_cache[idx]

            def _upload_annotations(idx, img_ids, anns):
                if idx in is_processing and is_processing[idx] or idx not in is_processing:
                    sly.logger.info(f"Waiting for annotation batch {idx} to be processed")
                    while idx not in is_processing or is_processing[idx]:
                        time.sleep(0.1)
                if idx in anns_to_upload and anns_to_upload[idx]:
                    is_uploading[idx] = True
                    sly.logger.info(f"Uploading annotation batch {idx}")
                    # img_ids = list(anns_to_upload[idx].keys())
                    # anns = list(anns_to_upload[idx].values())
                    # api.annotation.upload_jsons(img_ids, anns)

                    if isinstance(anns, tuple): # action: correction
                        api.image.figure.upload_geometries_batch(*anns)
                    elif isinstance(anns, list): # action: tagging
                        api.image.tag.add_to_objects(project_id, anns)
                    is_uploading[idx] = False

            for idx, batch_ids in enumerate(sly.batched(dst_imgs_ids)):
                download_executor.submit(_download_annotations, idx, batch_ids)
                upload_executor.submit(_upload_annotations, idx, batch_ids, anns_to_upload)

            for idx, batch_ids in enumerate(sly.batched(dst_imgs_ids)):
                batch_ann_json = _download_annotations(idx, batch_ids)

                sly.logger.info(f"Processing annotation batch {idx}")
                is_processing[idx] = True
                batch_tags = [] # List[Dict[str, int]]
                batch_geometries = [] # List[Dict[...]]
                batch_figure_ids = [] # List[int]
                for ann_json in batch_ann_json:
                    tags, figures, geometries = validate_annotation(ann_json, meta, tag_id)
                    batch_tags.extend(tags)
                    batch_figure_ids.extend(figures)
                    batch_geometries.extend(geometries)
                if (len(batch_tags) > 0) and (len(batch_geometries) == 0):
                    anns_to_upload[idx] = batch_tags
                elif (len(batch_geometries) > 0) and (len(batch_tags) == 0):
                    anns_to_upload[idx] = (batch_figure_ids, batch_geometries)

                is_processing[idx] = False
                sly.logger.info(f"Finished processing annotation batch {idx}")

            pbar_cb(len(dst_imgs_ids))

            download_executor.shutdown(wait=True)
            upload_executor.shutdown(wait=True)
        finally:
            download_executor.shutdown(cancel_futures=True)
            upload_executor.shutdown(cancel_futures=True)


def process_ds_recursive(
    api: sly.Api,
    dst_project_id: int,
    meta: sly.ProjectMeta,
    src_ds: sly.Dataset,
    tag_name: str,
    children: Optional[Dict] = None,
    parent_id: Optional[int] = None,
) -> None:
    """Process dataset recursively (with nested datasets)"""
    global project_id
    project_id = dst_project_id

    dst_ds = api.dataset.create(dst_project_id, src_ds.name, parent_id=parent_id)
    process_ds(api, dst_ds, meta, src_ds, tag_name)
    if children:
        for src_child_ds, child_children in children.items():
            process_ds_recursive(
                api, dst_project_id, meta, src_child_ds, tag_name, child_children, dst_ds.id
            )


def run_func_and_catch_exceptions(func: Callable) -> None:
    """
    Run function and catch exceptions.
    If exception is not handled, original exception will be raised
    """
    try:
        func()
    except Exception as e:
        from supervisely.io.exception_handlers import ErrorHandler, handle_exception

        handled_exc = handle_exception(e)
        if handled_exc:
            if isinstance(handled_exc, ErrorHandler.API.PaymentRequired):
                raise e
            else:
                handled_exc.raise_error(has_ui=False)
        else:
            raise e
