import supervisely as sly


def get_func_by_geometry_type(geometry: str):
    func_name = f"_validate_{geometry}"
    return globals().get(func_name, None)


def _validate_polygon(obj):
    def _validate_points(points):
        exterior = points["exterior"]
        if len({*[tuple(p) for p in exterior]}) < 3:
            return False

        interior = points["interior"]
        for shape in interior:
            if len({*[tuple(p) for p in shape]}) in [1, 2]:
                return False
        return True

    points = obj["points"]

    return _validate_points(points)


def _validate_bitmap(obj):
    is_valid = True

    return is_valid


def _validate_rectangle(obj):
    is_valid = True

    return is_valid


def _validate_polyline(obj):
    is_valid = True
    exterior = obj.geometry.exterior
    if len(exterior) < 2:
        is_valid = False
    return is_valid


def _validate_point(obj):
    is_valid = True

    return is_valid


def _validate_graphNodes(obj):
    is_valid = True
    return is_valid
