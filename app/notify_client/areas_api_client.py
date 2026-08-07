from app.notify_client import AdminAPIClient

class AreasAPIClient(AdminAPIClient):
    def get_libraries(self):
        return self.get(url="/areas/geography-types")["data"]

    def get_areas_for_library(self, type_name):
        return self.get(url=f"/areas/geography-types/{type_name}/areas")["data"]

    def get_areas_for_parent(self, parent_id):
        return self.get(url=f"/areas/{parent_id}/sub-areas")["data"]

    def check_grandparent(self, parent_id):
            return self.get(url=f"/areas/{parent_id}/is-grandparent")["data"]

    def get_areas():
        pass

    def get_area(self, id):
        return self.get(url=f"/areas/{id}")["data"]

    def get_areas_by_names(self, names, type_name):
        data = {"area_names": names}
        return self.post(url=f"/areas/get-{type_name}-by-names", data=data)["data"]

    def get_polygons(self, area_ids):
        data = {"areas": area_ids}
        return self.post(url="/areas/polygons", data=data)["data"]

    def add_areas(self, message_id, service_id, area_ids, type_name=None):
        data = {"area_ids": area_ids}
        if type_name:
            data["type_name"] = type_name
        return self.post(url=f"/areas/{service_id}/{message_id}/add-areas", data=data)

    def get_postcode_centroid(self, area_id):
        data = {"postcode": area_id}
        return self.post(url="/areas/postcodes/get-centroid", data=data)["data"]

    def create_postcode_area(self, area_id, radius):
        data = {"postcode": area_id, "radius": radius}
        return self.post(url="/areas/postcode-area", data=data)["data"]

    def add_postcode_area(self, message_id, service_id, postcode, radius):
        data = {"type_name": "postcodes", "postcode": postcode, "radius": radius}
        return self.post(url=f"/areas/{service_id}/{message_id}/add-postcodes-area", data=data)

    def get_coordinate_centroid(self, first_coordinate, second_coordinate, coordinate_type):
        data = {"first_coordinate": first_coordinate, "second_coordinate": second_coordinate, "coordinate_type": coordinate_type}
        return self.post(url="/areas/coordinates/get-centroid", data=data)["data"]

    def create_coordinate_area(self, first_coordinate, second_coordinate, radius, coordinate_type):
        data = {"first_coordinate": first_coordinate, "second_coordinate": second_coordinate, "radius": radius, "coordinate_type": coordinate_type}
        return self.post(url="/areas/coordinate-area", data=data)["data"]

    def add_coordinate_area(self, message_id, service_id, first_coordinate, second_coordinate, radius, coordinate_type):
        data = {"first_coordinate": first_coordinate, "second_coordinate": second_coordinate, "radius": radius, "coordinate_type": coordinate_type}
        return self.post(url=f"/areas/{service_id}/{message_id}/add-coordinates-area", data=data)

    def check_coordinates_valid(self, first_coordinate, second_coordinate, coordinate_type):
        data = {"first_coordinate": first_coordinate, "second_coordinate": second_coordinate, "coordinate_type": coordinate_type}
        return self.post(url="/areas/check-coordinates-valid", data=data)["data"]

    def remove_area(self, message_id, service_id, area_ids):
        data = {"area_ids": area_ids}
        return self.post(url=f"/areas/{service_id}/{message_id}/remove-areas", data=data)["data"]


areas_api_client = AreasAPIClient()
