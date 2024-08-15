import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from typing import Callable, Dict, Optional, Tuple

import supervisely as sly
from src.validation_functions import get_validation_func
from src.correction_functions import get_correction_func

# from requests.exceptions import HTTPError
import src.globals as g


def validate_annotation(
    ann_json: Dict, meta: sly.ProjectMeta, tag: Optional[Dict] = None
) -> Tuple[bool, Dict]:
    """Main function to validate annotation and add tag to invalid objects"""

    def _deserialization_check(obj, meta):
        try:
            label_obj = sly.Label.from_json(obj, meta)
            if label_obj is not None:
                return True
        except Exception as e:
            sly.logger.warning(
                f"Object deserialization failed. Exception message: {repr(e)}",
                extra={"Object info": obj},
                exc_info=True,
            )
        return False

    def _validate_labeler_login(labeler_login):
        if labeler_login not in g.team_members:
            sly.logger.warn(
                f"Labeler '{labeler_login}' is not a member of the destination group. Replacing label's author with '{g.user_self_login}'"
            )
            return g.user_self_login
        return labeler_login

    validated_ann = ann_json
    validated_objects = []
    for obj in ann_json.get("objects", []):
        obj["labelerLogin"] = _validate_labeler_login(obj["labelerLogin"])

        geometry_type = obj.get("geometryType", "")
        validation_func = get_validation_func(geometry_type)
        correction_func = get_correction_func(geometry_type)

        if not _deserialization_check(obj, meta) or (validation_func and not validation_func(obj)):
            sly.logger.debug("FOUND INVALID OBJECT")
            if correction_func:
                obj = correction_func(obj)
                sly.logger.info(
                    f"Autocorrecting the object (id: {obj['id']}, geometry: {geometry_type})"
                )
            else:
                raise NotImplementedError(
                    f"Unable to autocorrect faulty annotation object. Skipping label..."
                )
            if tag:
                obj_tags = obj.get("tags", None)
                if obj_tags is None:
                    obj_tags = []
                obj_tags.append(tag)
                obj["tags"] = obj_tags
        validated_objects.append(obj)
    validated_ann["objects"] = validated_objects
    if tag:
        ann_tags = ann_json["tags"]
        ann_tags.append(tag)
        validated_ann["tags"] = ann_tags
    return validated_ann


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
        tag = sly.Tag(tag_meta).to_json()
    else:
        tag = None
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

            batch_img_names = [img.name for img in batch_imgs]
            batch_img_ids = [img.id for img in batch_imgs]
            dst_imgs = api.image.upload_ids(dst_ds.id, batch_img_names, batch_img_ids)
            dst_imgs_ids = [imginfo.id for imginfo in dst_imgs]

            def _download_annotations(idx, img_ids):
                if idx in is_downloading and is_downloading[idx]:
                    sly.logger.debug(f"Waiting for annotation batch {idx} to be downloaded")
                    while is_downloading[idx]:
                        time.sleep(0.1)
                if idx not in ann_cache:
                    sly.logger.debug(f"Downloading annotation batch {idx}")
                    is_downloading[idx] = True
                    ann_cache[idx] = api.annotation.download_json_batch(src_ds.id, img_ids)
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
                    anns = list(anns_to_upload[idx].values())

                    if len(anns_to_upload) == 1:
                        anns = [anns_to_upload[idx]]
                    api.annotation.upload_jsons(img_ids, anns)
                    is_uploading[idx] = False

            for idx, batch_ids in enumerate(sly.batched(batch_img_ids)):
                download_executor.submit(_download_annotations, idx, batch_ids)

            for idx, batch_ids in enumerate(sly.batched(dst_imgs_ids)):
                upload_executor.submit(_upload_annotations, idx, batch_ids, anns_to_upload)

            for idx, batch_ids in enumerate(sly.batched(batch_img_ids)):
                batch_ann_json = _download_annotations(idx, batch_ids)

                sly.logger.debug(f"Processing annotation batch {idx}")
                is_processing[idx] = True
                for image_id, ann_json in zip(batch_ids, batch_ann_json):
                    sly.logger.debug("Validaing annotations...")
                    try:
                        validated_ann = validate_annotation(ann_json, meta, tag)
                        anns_to_upload[idx] = validated_ann
                    except Exception as e:
                        # ann_json = e.ann_json
                        mode = "tagging" if tag else "correction"
                        sly.logger.error(
                            f"Unexpected error validation annotation. Please, contact technical support. Error message: {repr(e)}",
                            extra={
                                "image id": image_id,
                                "mode": mode,
                                "json annotation": ann_json,
                            },
                        )  # skip уточнить
                        continue
                is_processing[idx] = False
                sly.logger.debug(f"Finished processing annotation batch {idx}")

            pbar_cb(len(dst_imgs_ids))

            download_executor.shutdown(wait=True)
            upload_executor.shutdown(wait=True)
        finally:
            import sys

            if sys.version_info >= (3, 9):
                download_executor.shutdown(wait=False, cancel_futures=True)
                upload_executor.shutdown(wait=False, cancel_futures=True)
            else:
                download_executor.shutdown(wait=False)
                upload_executor.shutdown(wait=False)


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
