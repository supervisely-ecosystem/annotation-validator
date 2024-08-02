import supervisely as sly

def get_func_by_geometry(geometry):
    func = None
    if isinstance(geometry, sly.Polygon):
        func = _validate_polygon
    elif isinstance(geometry, sly.Bitmap):
        func = _validate_bitmap
    elif isinstance(geometry, sly.Rectangle):
        func = _validate_rectangle
    elif isinstance(geometry, sly.Polyline):
        func = _validate_polyline
    elif isinstance(geometry, sly.Point):
        func = _validate_point
    elif isinstance(geometry, sly.GraphNodes):
        func = _validate_graphNodes
    return func

def _validate_polygon(label):
    is_valid = True

    return is_valid

def _validate_bitmap(label):
    is_valid = True

    return is_valid

def _validate_rectangle(label):
    is_valid = True

    return is_valid

def _validate_polyline(label):
    is_valid = True

    return is_valid

def _validate_point(label):
    is_valid = True

    return is_valid

def _validate_graphNodes(label):
    is_valid = True

    return is_valid