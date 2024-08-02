import supervisely as sly

def get_func_by_geometry_type(geometry: str):
    func_name = f'_validate_{geometry}'
    func = globals().get(func_name, None)
    return func

def _validate_polygon(obj):
    exterior_points = obj['points']['exterior']
    interior_points = obj['points']['interior']
    exterior_valid = len(exterior_points) > 3 
    interior_valid = len(interior_points) not in [1, 2]

    return exterior_valid is True and interior_valid is True
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