import math
from typing import Optional

import shapely.affinity
import shapely.ops
from shapely.geometry import Polygon, MultiPolygon, LineString


def split(polygon: Polygon) -> Optional[MultiPolygon]:
    """Splits a single WGS84 polygon into a multipolygon across the antimeridian.

    If the polygon does not cross the antimeridian, returns None. Only handles
    exterior rings (can't handle interior).

    Args:
        polygon (shapely.geometry.Polygon): The input polygon.

    Returns:
        Optional[shapely.geometry.MultiPolygon]: The output polygons, or None if
            no split occurred.
    """
    normalized = normalize(polygon)
    if normalized.bounds[0] < -180:
        longitude = -180
    elif normalized.bounds[2] > 180:
        longitude = 180
    else:
        return None
    splitter = LineString(((longitude, -90), (longitude, 90)))
    split = shapely.ops.split(normalized, splitter)
    if len(split.geoms) < 2:
        return None
    geoms = list()
    for geom in split.geoms:
        bounds = geom.bounds
        if bounds[0] < -180:
            geoms.append(shapely.affinity.translate(geom, xoff=360))
        elif bounds[2] > 180:
            geoms.append(shapely.affinity.translate(geom, xoff=-360))
        else:
            geoms.append(geom)
    return MultiPolygon(geoms)


def normalize(polygon: Polygon) -> Polygon:
    """'Normalizes' a WGS84 lat/lon polygon.

    This converts the polygon's x coordinates to all be the same sign, even if
    the polygon crosses the antimeridian. E.g.:

    ```
    canonical = Polygon(((170, 40), (170, 50), (-170, 50), (-170, 40), (170, 40)))
    normalized = stactools.core.utils.antimeridian.normalize(canonical)
    assert normalized.equals(shapely.geometry.box(170, 40, 190, 50))
    ```

    Inspired by
    https://towardsdatascience.com/around-the-world-in-80-lines-crossing-the-antimeridian-with-python-and-shapely-c87c9b6e1513.

    Args:
        polygon (shapely.geometry.Polygon): The input polygon.

    Returns:
        shapely.geometry.Polygon: The normalized polygon.
    """
    coords = list(polygon.exterior.coords)
    for index, (start, end) in enumerate(zip(coords, coords[1:])):
        delta = end[0] - start[0]
        if abs(delta) > 180:
            coords[index + 1] = (end[0] - math.copysign(360, delta), end[1])
    return Polygon(coords)
