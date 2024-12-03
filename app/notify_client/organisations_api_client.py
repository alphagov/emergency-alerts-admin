from itertools import chain

from notifications_python_client.errors import HTTPError

from app.notify_client import AdminAPIClient


class OrganisationsClient(AdminAPIClient):
    def get_organisations(self):
        return self.get(url="/organisations")

    def get_domains(self):
        return list(chain.from_iterable(organisation["domains"] for organisation in self.get_organisations()))

    def get_organisation(self, org_id):
        return self.get(url="/organisations/{}".format(org_id))

    def get_organisation_name(self, org_id):
        return self.get_organisation(org_id)["name"]

    def get_organisation_by_domain(self, domain):
        try:
            return self.get(
                url="/organisations/by-domain?domain={}".format(domain),
            )
        except HTTPError as error:
            if error.status_code == 404:
                return None
            raise error

    def create_organisation(self, name, crown, organisation_type, agreement_signed):
        return self.post(
            url="/organisations",
            data={
                "name": name,
                "crown": crown,
                "organisation_type": organisation_type,
                "agreement_signed": agreement_signed,
            },
        )

    def update_organisation(self, org_id, **kwargs):
        api_response = self.post(url="/organisations/{}".format(org_id), data=kwargs)
        return api_response

    def update_service_organisation(self, service_id, org_id):
        data = {"service_id": service_id}
        return self.post(url="/organisations/{}/service".format(org_id), data=data)

    def get_organisation_services(self, org_id):
        return self.get(url="/organisations/{}/services".format(org_id))

    def remove_user_from_organisation(self, org_id, user_id):
        return self.delete(f"/organisations/{org_id}/users/{user_id}")

    def get_services_and_usage(self, org_id, year):
        return self.get(url=f"/organisations/{org_id}/services-with-usage", params={"year": str(year)})

    def archive_organisation(self, org_id):
        return self.post(
            url=f"/organisations/{org_id}/archive",
            data=None,
        )


organisations_client = OrganisationsClient()
