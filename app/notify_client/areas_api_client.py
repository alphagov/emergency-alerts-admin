from app.notify_client import AdminAPIClient


class AreasAPIClient(AdminAPIClient):

    def get_libraries(self):
        return self.get(url="/areas/geography-types")["data"]

    def get_library_example(self, type_name):
        return self.get(url=f"/areas/geography-types/{type_name}/examples")["data"]

    def get_areas_for_library(self, version_id):
        return self.get(url=f"/areas/geography-types/{version_id}/areas")["data"]

    def get_areas_for_parent(self, version_id, parent_id):
        return self.get(url=f"/areas/geography-types/{version_id}/{parent_id}/areas")["data"]

    def get_all_areas(self):
        pass

    def get_areas_by_ids(self, area_ids):
        data = {"area_ids": area_ids}
        return self.post(url="/areas/get-areas", data=data)["data"]

    def get_area(self, id):
        return self.get(url=f"/areas/{id}")["data"]

    def get_local_authorities_by_names(self, names):
        data = {"area_names": names}
        return self.post(url="/areas/get-local-authorities-by-names", data=data)["data"]

    def get_flood_warning_areas_by_ta_codes(self, names):
        data = {"ta_codes": names}
        return self.post(url="/areas/get-flood-warning-areas-by-geographic-ids", data=data)["data"]

    def get_area_dict(self, area_ids):
        data = {"area_ids": area_ids}
        return self.post(url="/areas/get-area-dict", data=data)

    def add_areas(self, message_id, service_id, area_ids, message_type="broadcast", version_id=None):
        data = {"area_ids": area_ids}
        if version_id:
            data["version_id"] = version_id
        return self.post(url=f"/areas/{service_id}/{message_id}/{message_type}/add-areas", data=data)

    def get_postcode_centroid(self, area_id):
        data = {"postcode": area_id}
        return self.post(url="/areas/postcodes/get-centroid", data=data)["data"]

    def create_postcode_area(self, area_id, radius):
        data = {"postcode": area_id, "radius": radius}
        return self.post(url="/areas/postcode-area", data=data)

    def add_postcode_area(self, message_id, service_id, postcode, radius, message_type):
        data = {"type_name": "postcodes", "postcode": postcode, "radius": radius}
        return self.post(url=f"/areas/{service_id}/{message_id}/{message_type}/add-postcodes-area", data=data)

    def get_coordinate_centroid(self, first_coordinate, second_coordinate, coordinate_type):
        data = {
            "first_coordinate": first_coordinate,
            "second_coordinate": second_coordinate,
            "coordinate_type": coordinate_type,
        }
        return self.post(url="/areas/coordinates/get-centroid", data=data)["data"]

    def create_coordinate_area(self, first_coordinate, second_coordinate, radius, coordinate_type):
        data = {
            "first_coordinate": first_coordinate,
            "second_coordinate": second_coordinate,
            "radius": radius,
            "coordinate_type": coordinate_type,
        }
        return self.post(url="/areas/coordinate-area", data=data)["data"]

    def add_coordinate_area(
        self, message_id, service_id, first_coordinate, second_coordinate, radius, coordinate_type, message_type
    ):
        data = {
            "first_coordinate": first_coordinate,
            "second_coordinate": second_coordinate,
            "radius": radius,
            "coordinate_type": coordinate_type,
        }
        return self.post(url=f"/areas/{service_id}/{message_id}/{message_type}/add-coordinates-area", data=data)

    def check_coordinates_valid(self, first_coordinate, second_coordinate, coordinate_type):
        data = {
            "first_coordinate": first_coordinate,
            "second_coordinate": second_coordinate,
            "coordinate_type": coordinate_type,
        }
        return self.post(url="/areas/check-coordinates-valid", data=data)["data"]

    def remove_area(self, message_id, service_id, area_id, message_type):
        data = {"area_id": area_id}
        return self.post(url=f"/areas/{service_id}/{message_id}/{message_type}/remove-area", data=data)


areas_api_client = AreasAPIClient()
