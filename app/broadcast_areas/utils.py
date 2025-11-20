import itertools
from collections import defaultdict

from emergency_alerts_utils.polygons import Polygons

from app.broadcast_areas.models import CustomBroadcastArea


def aggregate_areas(areas):
    areas = _convert_custom_areas_to_wards(areas)
    areas = _aggregate_wards_by_local_authority(areas)
    areas = _aggregate_lower_tier_authorities(areas)
    return sorted(areas)


def _convert_custom_areas_to_wards(areas):
    results = set()

    for area in areas:
        if type(area) is CustomBroadcastArea:
            results |= set(area.overlapping_electoral_wards)
        else:
            results |= {area}

    return results


def _aggregate_wards_by_local_authority(areas):
    return {area.parent if area.is_electoral_ward else area for area in areas}


def _aggregate_lower_tier_authorities(areas):
    results = set()
    clusters = _cluster_lower_tier_authorities(areas)

    for cluster in clusters:
        # always show a single area cluster as itself (aggregation isn't helpful)
        if len(cluster) == 1:
            results |= set(cluster)
        # aggregate a single cluster with lots of areas (too complex to show in full)
        elif len(cluster) > 3:
            results |= {cluster[0].parent}
        # if cluster is 2 or 3 areas, and there are more than 1 cluster, aggregate the cluster
        elif len(clusters) > 1:
            area = cluster[0]
            results |= {area.parent or area}
        # else keep single 2-3 areas cluster in full (easy enough to understand)
        else:
            results |= set(cluster)

    return results


def _cluster_lower_tier_authorities(areas):
    result = defaultdict(lambda: [])

    for area in areas:
        # group lower tier authorities by "county"
        if area.is_lower_tier_local_authority:
            result[area.parent] += [area]
        # leave countries, unitary authorities as-is
        else:
            result[area] = [area]

    return result.values()


def _aggregate_REPPIR_sites_by_local_authority(area):
    # Returns the area name, concatenated with the local authority
    if area.parent:
        return f"{area.name}, {area.parent.name}"
    else:
        return f"{area.name}"


def generate_aggregate_names(areas):
    aggregate_names = []
    for area in areas:
        if area.is_REPPIR_site and (name := _aggregate_REPPIR_sites_by_local_authority(area)):
            aggregate_names.append(name)
        else:
            aggregate_names.append(area.name)
    return aggregate_names


def create_areas_dict(areas):
    polygons = get_polygons_from_areas(areas, "simple_polygons")
    return {
        "ids": [area.id for area in areas],
        "names": [area.name for area in areas],
        "aggregate_names": [area.name for area in aggregate_areas(areas)],
        "simple_polygons": polygons.as_coordinate_pairs_lat_long,
    }


def get_polygons_from_areas(areas, area_attribute):
    areas_polygons = [getattr(area, area_attribute) for area in areas]
    coordinate_reference_systems = {polygons.utm_crs for polygons in areas_polygons}

    if len(coordinate_reference_systems) == 1:
        # All our polygons are defined in the same coordinate
        # reference system so we just have to flatten the list and
        # say which coordinate reference system we are using
        polygons = Polygons(
            list(itertools.chain(*areas_polygons)),
            utm_crs=next(iter(coordinate_reference_systems)),
        )
    else:
        # Our polygons are in different coordinate reference systems
        # We need to convert them back to degrees and make a new
        # instance of `Polygons` which will determine a common
        # coordinate reference system
        polygons = Polygons(
            list(itertools.chain(*(area_polygon.as_wgs84_coordinates for area_polygon in areas_polygons)))
        )

    if area_attribute != "polygons" and len(areas) > 1:
        # We’re combining simplified polygons from multiple areas so we
        # need to re-simplify the combined polygons to keep the point
        # count down
        return polygons.smooth.simplify
    return polygons
