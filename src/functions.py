import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from typing import Callable, Dict, Optional, Tuple

import supervisely as sly
from src.validation_functions import get_func_by_geometry_type



def validate_annotation(ann_json: Dict, meta: sly.ProjectMeta, tag_name: str) -> Tuple[bool, Dict]:
    """Main function to validate annotation and add tag to invalid objects"""
    def _deserialization_check(obj, meta):
        try:
            label_obj = sly.Label.from_json(obj, meta)
            if label_obj is not None:
                return True
        except Exception as e:
            sly.logger.debug(repr(e))
        return False
    is_valid = True
    add_tag = tag_name is not None
    if add_tag:
        tag_meta = meta.get_tag_meta(tag_name)
        tag = sly.Tag(tag_meta)

    new_objects = []
    for obj in ann_json.get('objects'):
        geometry_type = obj.get('geometryType')
        validation_func = get_func_by_geometry_type(geometry_type)
        if validation_func is None:
            sly.logger.info(f"Geometry type {geometry_type} is not supported. Skipping validation...")
            new_objects.append(obj)
            continue

        if _deserialization_check(obj, meta) is False or validation_func(obj) is False:
            is_valid = False
            if add_tag:
                object_tags = obj.get('tags')
                if isinstance(object_tags, list):
                    object_tags.append(tag)
                else:
                    object_tags = [tag]
                obj['tags'] = object_tags
            else:
                continue
        new_objects.append(obj)

    ann_json['objects'] = new_objects

    return is_valid, ann_json


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
                    img_ids = list(anns_to_upload[idx].keys())
                    anns = list(anns_to_upload[idx].values())
                    api.annotation.upload_jsons(img_ids, anns)
                    is_uploading[idx] = False

            for idx, batch_ids in enumerate(sly.batched(dst_imgs_ids)):
                download_executor.submit(_download_annotations, idx, batch_ids)
                upload_executor.submit(_upload_annotations, idx, batch_ids, anns_to_upload)

            for idx, batch_ids in enumerate(sly.batched(dst_imgs_ids)):
                batch_ann_json = _download_annotations(idx, batch_ids)

                sly.logger.info(f"Processing annotation batch {idx}")
                is_processing[idx] = True
                for image_id, ann_json in zip(batch_ids, batch_ann_json):
                    is_valid, validated_ann = validate_annotation(ann_json, meta, tag_name)
                    if not is_valid:
                        anns_to_upload[idx][image_id] = validated_ann
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
