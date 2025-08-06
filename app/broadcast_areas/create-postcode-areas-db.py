#!/usr/bin/env python

import os
from pathlib import Path

import geojson
from emergency_alerts_utils.formatters import formatted_list
from emergency_alerts_utils.polygons import Polygons
from repo import BroadcastAreasRepository
from rtreelib import RTree
from shapely import wkt
from shapely.geometry import MultiPolygon, Polygon

postcode_files_path = Path(__file__).resolve().parent / "postcode_areas"
point_counts = []
invalid_polygons = []
rtree_index = RTree()

# The hard limit in the CBCs is 6,000 points per polygon. But we also
# care about optimising how quickly we can process and display polygons
# so we aim for something lower, i.e. enough to give us a good amount of
# precision relative to the accuracy of a cell broadcast
MAX_NUMBER_OF_POINTS_PER_POLYGON = 250

repo = BroadcastAreasRepository()


def simplify_geometry(feature):
    if feature["type"] == "Polygon":
        return [feature["coordinates"][0]]
    elif feature["type"] == "MultiPolygon":
        return [polygon for polygon, *_holes in feature["coordinates"]]
    else:
        raise Exception("Unknown type: {}".format(feature["type"]))


def clean_up_invalid_polygons(postcode, polygons, indent="    "):
    """
    This function expects a list of lists of coordinates defined in degrees
    """
    for index, polygon in enumerate(polygons):
        shapely_polygon = Polygon(polygon)

        # Some of our data has points which are incredibly close
        # together. In some cases they are close enough to be duplicates
        # at a given precision, which makes an invalid topology. In
        # other cases they are close enough that, when converting from
        # one coordinate system to another, they shift about enough to
        # create self-intersection. The fix in both cases is to reduce
        # the precision of the coordinates and then apply simplification
        # with a tolerance of 0.
        simplified_polygon = wkt.loads(
            wkt.dumps(shapely_polygon, rounding_precision=Polygons.output_precision_in_decimal_places - 1)
        ).simplify(0)

        if simplified_polygon.is_valid:
            print(f"{indent}Polygon {index + 1}/{len(polygons)} is valid")
            yield simplified_polygon

        else:
            invalid_polygons.append(shapely_polygon)

            # We’ve found polygons where all the points line up, so they
            # don’t have an area. They wouldn’t contribute to a broadcast
            # so we can ignore them.
            if simplified_polygon.area == 0:
                print(f"{indent}Polygon {index + 1}/{len(polygons)} has 0 area, skipping")
                continue

            print(f"{indent}Polygon {index + 1}/{len(polygons)} needs fixing...")

            # Buffering with a size of 0 is a trick to make valid
            # geometries from polygons that self intersect
            buffered = shapely_polygon.buffer(0)

            # If the buffering has caused our polygon to split into
            # multiple polygons, we need to recursively check them
            # instead
            if isinstance(buffered, MultiPolygon):
                try:
                    for sub_polygon in clean_up_invalid_polygons(postcode, buffered, indent="        "):
                        yield sub_polygon
                    continue
                except TypeError:
                    for sub_polygon in clean_up_invalid_polygons(postcode, buffered.geoms, indent="        "):
                        yield sub_polygon
                    continue
            # We only care about the exterior of the polygon, not an
            # holes in it that may have been created by fixing self
            # intersection
            fixed_polygon = Polygon(buffered.exterior)

            print(f"{indent}Polygon {index + 1}/{len(polygons)} fixed!")

            yield fixed_polygon


def polygons_and_simplified_polygons(feature, name, postcode):
    raw_polygons = simplify_geometry(feature)
    clean_raw_polygons = [
        [[x, y] for x, y in polygon.exterior.coords] for polygon in clean_up_invalid_polygons(postcode, raw_polygons)
    ]
    polygons = Polygons(clean_raw_polygons)

    full_resolution = polygons
    smoothed = full_resolution.smooth
    simplified = smoothed.simplify

    if not (len(full_resolution) or len(simplified)):
        return None, None, None

    print(
        f"    Original:{full_resolution.point_count: >5} points"
        f"    Smoothed:{smoothed.point_count: >5} points"
        f"    Simplified:{simplified.point_count: >4} points"
    )

    point_counts.append(simplified.point_count)

    if simplified.point_count >= MAX_NUMBER_OF_POINTS_PER_POLYGON:
        raise RuntimeError(
            "Too many points "
            "(adjust Polygons.perimeter_to_simplification_ratio or "
            "Polygons.perimeter_to_buffer_ratio)"
        )

    output = [
        full_resolution.as_coordinate_pairs_long_lat,
        simplified.as_coordinate_pairs_long_lat,
    ]

    # Checking that the process hasn`t introduced bad data by
    # iterating through both the full resolution and simplified polygons.
    # Firstly checks validity, and if invalid checks whether polygon is Polygon or MultiPolygon
    # and fixes resulting polygons again by adding another buffer.
    # Following this another assertion is made that fixed polygons are valid.

    for dataset in output:
        for polygon in dataset:
            if not Polygon(polygon).is_valid:
                buffered = Polygon(polygon).buffer(0)
                if isinstance(buffered, MultiPolygon):
                    for polygon in list(buffered.geoms):
                        assert polygon.is_valid, f"Polygon in MultiPolygon for {name} is invalid"
                    multipolygons = [[[x, y] for x, y in polygon.exterior.coords] for polygon in list(buffered.geoms)]
                    polygons = Polygons(multipolygons)
                    full = polygons
                    simplified = polygons.smooth.simplify
                else:
                    fixed_polygon = Polygon(buffered.exterior)
                    assert fixed_polygon.is_valid, f"Polygon for {name} is invalid"
                    full = Polygons([[[x, y] for x, y in fixed_polygon.exterior.coords]])
                    simplified = Polygons([[[x, y] for x, y in fixed_polygon.exterior.coords]]).smooth.simplify
                output = [full.as_coordinate_pairs_long_lat, simplified.as_coordinate_pairs_long_lat]

    return output + [simplified.utm_crs]


def add_postcode_areas(postcode_filepath):
    dataset_id = "postcodes"
    dataset_geojson = geojson.loads(postcode_filepath.read_text())

    areas_to_add = []
    for feature in dataset_geojson["features"]:
        f_id = feature["properties"]["POSTCODE"]
        f_name = feature["properties"]["POSTCODE"]

        feature, _, utm_crs = polygons_and_simplified_polygons(feature["geometry"], dataset_id, f_name)

        if feature is not None:
            areas_to_add.append(
                [
                    f"{dataset_id}-{f_id}",
                    f_name,
                    dataset_id,
                    None,
                    feature,
                    feature,
                    utm_crs,
                    0,
                ]
            )

    repo.insert_broadcast_areas(areas_to_add, keep_old_polygons)


def check_postcode_library_exists():
    libraries = repo.get_libraries()
    if "postcodes" not in [tup[0] for tup in libraries]:
        repo.insert_broadcast_area_library(
            "postcodes",
            name="Postcode areas",
            name_singular="postcode area",
            is_group=False,
        )


keep_old_polygons = False

postcode_files = os.listdir(postcode_files_path)

check_postcode_library_exists()

for file in postcode_files:
    add_postcode_areas(postcode_files_path / file)
    os.remove(postcode_files_path / file)


most_detailed_polygons = formatted_list(
    sorted(point_counts, reverse=True)[:5],
    before_each="",
    after_each="",
)

print(
    "\n"
    "DONE\n"
    f"    Processed {len(point_counts):,} polygons.\n"
    f"    Cleaned up {len(invalid_polygons):,} polygons.\n"
    f"    Highest point counts once simplifed: {most_detailed_polygons}\n"
)
