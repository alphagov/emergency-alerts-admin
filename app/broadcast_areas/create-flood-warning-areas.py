#!/usr/bin/env python

import sys
from pathlib import Path

import geojson
from emergency_alerts_utils.formatters import formatted_list
from emergency_alerts_utils.polygons import Polygons
from repo import BroadcastAreasRepository
from rtreelib import RTree

source_files_path = Path(__file__).resolve().parent / "source_files"
point_counts = []
rtree_index = RTree()


def simplify_geometry(feature):
    if feature["type"] == "Polygon":
        return [feature["coordinates"][0]]
    elif feature["type"] == "MultiPolygon":
        return [polygon for polygon, *_holes in feature["coordinates"]]
    else:
        raise Exception("Unknown type: {}".format(feature["type"]))


def polygons_and_simplified_polygons(feature, id):

    raw_polygons = simplify_geometry(feature)

    polygons = Polygons(raw_polygons)

    simplified = polygons.simplify

    output = [
        polygons.as_coordinate_pairs_long_lat,
        polygons.as_coordinate_pairs_long_lat,
    ]

    return output + [simplified.utm_crs]


flood_warning_filepath = source_files_path / "FWS_flood_warning_polygons.geojson"


def add_test_areas():
    dataset_id = "Flood_Warning_Target_Areas"
    dataset_geojson = geojson.loads(flood_warning_filepath.read_text())
    repo.insert_broadcast_area_library(
        dataset_id,
        name="Flood Warning Target Areas",
        name_singular="Flood Warning Target Area",
        is_group=False,
    )

    areas_to_add = []
    for feature in dataset_geojson["features"]:
        f_id = feature["properties"]["tacode"]
        f_name = feature["properties"]["name"].replace("_", " ")

        feature, _, utm_crs = polygons_and_simplified_polygons(feature["geometry"], f_id)
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


# cheeky global variable
keep_old_polygons = sys.argv[1:] == ["--keep-old-polygons"]

repo = BroadcastAreasRepository()

add_test_areas()

most_detailed_polygons = formatted_list(
    sorted(point_counts, reverse=True)[:5],
    before_each="",
    after_each="",
)
