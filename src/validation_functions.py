def get_validation_func(geometry: str):
    func_name = f"_validate_{geometry}"
    return globals().get(func_name, None)


def _validate_polygon(obj):
    def _validate_points(points):
        exterior = points["exterior"]
        # if len({*[tuple(p) for p in exterior]}) < 3:
        if len(exterior) < 3:
            return False

        interior = points["interior"]
        for shape in interior:
            # if len({*[tuple(p) for p in shape]}) in [1, 2]:
            if len(shape) < 3:
                return False
        return True

    points = obj["points"]

    return _validate_points(points)


def _validate_polyline(obj):
    if len(obj["points"]["exterior"]) < 2:
        return False
    return True
