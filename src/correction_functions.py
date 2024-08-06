def get_correction_func(geometry: str):
    func_name = f"_correct_{geometry}"
    return globals().get(func_name, None)


def _correct_polygon(obj):
    def _correct_points(points):
        if len(points) > 3 or len(points) == 0:
            return points
        while len(points) < 3:
            points.append(points[-1].copy())
        return points

    ext_points = obj["points"]["exterior"]
    int_points = obj["points"]["interior"]

    obj["points"]["exterior"] = _correct_points(ext_points)
    obj["points"]["interior"] = [_correct_points(p) for p in int_points]
    return obj


def _correct_bitmap(obj):
    return obj
