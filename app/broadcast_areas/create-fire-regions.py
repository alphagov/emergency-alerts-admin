#!/usr/bin/env python

import sys
from math import isclose
from pathlib import Path

import geojson
from emergency_alerts_utils.formatters import formatted_list
from emergency_alerts_utils.polygons import Polygons
from repo import BroadcastAreasRepository
from rtreelib import RTree
from shapely import make_valid, wkt
from shapely.geometry import MultiPolygon, Polygon, mapping, shape
from shapely.ops import unary_union

source_files_path = Path(__file__).resolve().parent / "source_files"
point_counts = []
invalid_polygons = []
rtree_index = RTree()

# The hard limit in the CBCs is 6,000 points per polygon. But we also
# care about optimising how quickly we can process and display polygons
# so we aim for something lower, i.e. enough to give us a good amount of
# precision relative to the accuracy of a cell broadcast
MAX_NUMBER_OF_POINTS_PER_POLYGON = 250


def simplify_geometry(feature):
    if feature["type"] == "Polygon":
        return [feature["coordinates"][0]]
    elif feature["type"] == "MultiPolygon":
        return [polygon for polygon, *_holes in feature["coordinates"]]
    elif feature["type"] == "GeometryCollection":
        polygons = []

        for geom in feature["geometries"]:
            if geom["type"] == "Polygon":
                polygons.append(geom["coordinates"][0])

            elif geom["type"] == "MultiPolygon":
                polygons.extend(polygon for polygon, *_holes in geom["coordinates"])

        return polygons
    else:
        raise Exception("Unknown type: {}".format(feature["type"]))


def clean_up_invalid_polygons(polygons, indent="    "):
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
                for sub_polygon in clean_up_invalid_polygons(buffered, indent="        "):
                    yield sub_polygon
                continue

            # We only care about the exterior of the polygon, not an
            # holes in it that may have been created by fixing self
            # intersection
            fixed_polygon = Polygon(buffered.exterior)

            # Make sure the polygon is now valid, and that we haven’t
            # drastically transformed the polygon by ‘fixing’ it
            assert fixed_polygon.is_valid
            assert isclose(fixed_polygon.area, shapely_polygon.area, rel_tol=0.001)

            print(f"{indent}Polygon {index + 1}/{len(polygons)} fixed!")

            yield fixed_polygon


def polygons_and_simplified_polygons(feature):
    if keep_old_polygons:
        # cheat and shortcut out
        return [], []

    raw_polygons = simplify_geometry(feature)

    clean_raw_polygons = [
        [[x, y] for x, y in polygon.exterior.coords] for polygon in clean_up_invalid_polygons(raw_polygons)
    ]
    polygons = Polygons(clean_raw_polygons)

    full_resolution = polygons.remove_too_small
    smoothed = full_resolution.smooth
    simplified = smoothed.simplify

    if not (len(full_resolution) or len(simplified)):
        raise RuntimeError("Polygon of 0 size found")

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

    # Check that the simplification process hasn’t introduced bad data
    for dataset in output:
        for polygon in dataset:
            assert Polygon(polygon).is_valid

    return output + [simplified.utm_crs]


# https://geoportal.statistics.gov.uk/datasets/99b65a0790a64a36bfcb0581e8d760f1_0
fire_ew_filepath = source_files_path / "Fire_and_Rescue_Authorities_December_(2024)_Boundaries_EW_BGC.geojson"

# https://hub.arcgis.com/maps/govscot::fire-and-rescue-service-areas-scotland
fire_s_filepath = source_files_path / "ScottishFireRescue.geojson"

# https://www.nisra.gov.uk/publications/data-zone-boundaries-gis-format
fire_ni_filepath = source_files_path / "NIFRS.geojson"


def add_fire_areas():
    dataset_name = "Fire Regions"
    dataset_name_singular = "fire region"
    dataset_id = "fire"

    repo.insert_broadcast_area_library(
        dataset_id,
        name=dataset_name,
        name_singular=dataset_name_singular,
        is_group=True,
    )

    england_wales_features = geojson.loads(fire_ew_filepath.read_text())["features"]

    scotland_features = geojson.loads(fire_s_filepath.read_text())["features"]

    northern_ireland_features = geojson.loads(fire_ni_filepath.read_text())["features"]

    _add_top_level_fire_regions(
        dataset_id,
        england_wales_features,
        scotland_features,
        northern_ireland_features,
    )

    _add_fire_areas_england_wales(
        dataset_id,
        england_wales_features,
    )

    _add_fire_areas_scotland(
        dataset_id,
        scotland_features,
    )

    _add_fire_areas_northern_ireland(
        dataset_id,
        northern_ireland_features,
    )


def _merge_geometries(geometries):
    merged = unary_union(geometries)

    if merged.geom_type == "GeometryCollection":
        merged = unary_union([geom for geom in merged.geoms if geom.geom_type in ("Polygon", "MultiPolygon")])

    return merged


def _create_top_level_area(
    area_id,
    area_name,
    dataset_id,
    features,
):
    geometries = [make_valid(shape(feature["geometry"])) for feature in features]

    merged_geometry = _merge_geometries(geometries)

    feature, simple_feature, utm_crs = polygons_and_simplified_polygons(mapping(merged_geometry))

    return [
        area_id,
        area_name,
        dataset_id,
        None,
        feature,
        simple_feature,
        utm_crs,
        0,
    ]


def _add_top_level_fire_regions(
    dataset_id,
    england_wales_features,
    scotland_features,
    northern_ireland_features,
):
    areas_to_add = [
        _create_top_level_area(
            "fire-ew",
            "England and Wales FRAs",
            dataset_id,
            england_wales_features,
        ),
        _create_top_level_area(
            "fire-s",
            "Scotland SFRS Local Areas",
            dataset_id,
            scotland_features,
        ),
        _create_top_level_area(
            "fire-ni",
            "Northern Ireland NIFRS Commands",
            dataset_id,
            northern_ireland_features,
        ),
    ]

    repo.insert_broadcast_areas(
        areas_to_add,
        keep_old_polygons,
    )


def _add_fire_areas_england_wales(
    dataset_id,
    features,
):
    areas_to_add = []

    for feature in features:
        f_code = feature["properties"]["FRA24CD"]
        f_name = feature["properties"]["FRA24NM"]

        print()
        print(f_name)

        feature, simple_feature, utm_crs = polygons_and_simplified_polygons(feature["geometry"])

        areas_to_add.append(
            [
                f"{dataset_id}-ew-{f_code}",
                f_name,
                dataset_id,
                f"{dataset_id}-ew",
                feature,
                simple_feature,
                utm_crs,
                0,
            ]
        )

    repo.insert_broadcast_areas(
        areas_to_add,
        keep_old_polygons,
    )


def _add_fire_areas_scotland(
    dataset_id,
    features,
):
    grouped = {}

    for feature in features:
        code = feature["properties"]["sfrsdacode"]

        grouped.setdefault(
            code,
            {
                "name": (feature["properties"]["sfrsdaname"] + " Service Delivery Area"),
                "geometries": [],
            },
        )

        grouped[code]["geometries"].append(make_valid(shape(feature["geometry"])))

    areas_to_add = []

    for code, group in grouped.items():
        merged_geometry = _merge_geometries(group["geometries"])

        feature, simple_feature, utm_crs = polygons_and_simplified_polygons(mapping(merged_geometry))

        areas_to_add.append(
            [
                f"{dataset_id}-s-{code}",
                group["name"],
                dataset_id,
                f"{dataset_id}-s",
                feature,
                simple_feature,
                utm_crs,
                0,
            ]
        )

    repo.insert_broadcast_areas(
        areas_to_add,
        keep_old_polygons,
    )


def _add_fire_areas_northern_ireland(
    dataset_id,
    features,
):
    grouped = {}

    for feature in features:
        area = feature["properties"]["command_area"]

        grouped.setdefault(
            area,
            {
                "name": area,
                "geometries": [],
            },
        )

        grouped[area]["geometries"].append(make_valid(shape(feature["geometry"])))

    areas_to_add = []

    for area, group in grouped.items():
        merged_geometry = _merge_geometries(group["geometries"])

        feature, simple_feature, utm_crs = polygons_and_simplified_polygons(mapping(merged_geometry))

        areas_to_add.append(
            [
                f"{dataset_id}-ni-{area}",
                group["name"],
                dataset_id,
                f"{dataset_id}-ni",
                feature,
                simple_feature,
                utm_crs,
                0,
            ]
        )

    repo.insert_broadcast_areas(
        areas_to_add,
        keep_old_polygons,
    )


# cheeky global variable
keep_old_polygons = sys.argv[1:] == ["--keep-old-polygons"]

repo = BroadcastAreasRepository()

add_fire_areas()

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
