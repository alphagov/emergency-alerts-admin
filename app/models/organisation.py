from collections import OrderedDict

from flask import abort
from werkzeug.utils import cached_property

from app.models import JSONModel, ModelList, SerialisedModelCollection
from app.notify_client.organisations_api_client import organisations_client


class Organisation(JSONModel):
    TYPE_CENTRAL = "central"
    TYPE_LOCAL = "local"
    TYPE_NHS_CENTRAL = "nhs_central"
    TYPE_NHS_LOCAL = "nhs_local"
    TYPE_NHS_GP = "nhs_gp"
    TYPE_EMERGENCY_SERVICE = "emergency_service"
    TYPE_SCHOOL_OR_COLLEGE = "school_or_college"
    TYPE_OTHER = "other"

    NHS_TYPES = (
        TYPE_NHS_CENTRAL,
        TYPE_NHS_LOCAL,
        TYPE_NHS_GP,
    )

    TYPE_LABELS = OrderedDict(
        [
            (TYPE_CENTRAL, "Central government"),
            (TYPE_LOCAL, "Local government"),
            (TYPE_NHS_CENTRAL, "NHS – central government agency or public body"),
            (TYPE_NHS_LOCAL, "NHS Trust or Clinical Commissioning Group"),
            (TYPE_NHS_GP, "GP practice"),
            (TYPE_EMERGENCY_SERVICE, "Emergency service"),
            (TYPE_SCHOOL_OR_COLLEGE, "School or college"),
            (TYPE_OTHER, "Other"),
        ]
    )

    ALLOWED_PROPERTIES = {
        "id",
        "name",
        "active",
        "crown",
        "organisation_type",
        "domains",
        "count_of_live_services",
        "notes",
    }

    __sort_attribute__ = "name"

    @classmethod
    def from_id(cls, org_id):
        if not org_id:
            return cls({})
        return cls(organisations_client.get_organisation(org_id))

    @classmethod
    def from_domain(cls, domain):
        return cls(organisations_client.get_organisation_by_domain(domain))

    @classmethod
    def from_service(cls, service_id):
        return cls(organisations_client.get_service_organisation(service_id))

    @classmethod
    def create_from_form(cls, form):
        return cls.create(
            name=form.name.data,
            crown={
                "crown": True,
                "non-crown": False,
                "unknown": None,
            }.get(form.crown_status.data),
            organisation_type=form.organisation_type.data,
        )

    @classmethod
    def create(cls, name, crown, organisation_type, agreement_signed=False):
        return cls(
            organisations_client.create_organisation(
                name=name,
                crown=crown,
                organisation_type=organisation_type,
                agreement_signed=agreement_signed,
            )
        )

    def __init__(self, _dict):
        super().__init__(_dict)

        if self._dict == {}:
            self.id = None
            self.name = None
            self.crown = None
            self.agreement_signed = None
            self.domains = []
            self.organisation_type = None

    @property
    def organisation_type_label(self):
        return self.TYPE_LABELS.get(self.organisation_type)

    @property
    def crown_status_or_404(self):
        if self.crown is None:
            abort(404)
        return self.crown

    @cached_property
    def services(self):
        from app.models.service import Services

        return Services(organisations_client.get_organisation_services(self.id))

    @cached_property
    def service_ids(self):
        return [s.id for s in self.services]

    @property
    def live_services(self):
        return [s for s in self.services if s.active and s.live]

    @property
    def trial_services(self):
        return [s for s in self.services if not s.active or s.trial_mode]

    @cached_property
    def invited_users(self):
        from app.models.user import OrganisationInvitedUsers

        return OrganisationInvitedUsers(self.id)

    @cached_property
    def active_users(self):
        from app.models.user import OrganisationUsers

        return OrganisationUsers(self.id)

    @cached_property
    def team_members(self):
        return self.invited_users + self.active_users

    @cached_property
    def agreement_signed_by(self):
        if self.agreement_signed_by_id:
            from app.models.user import User

            return User.from_id(self.agreement_signed_by_id)

    def update(self, delete_services_cache=False, **kwargs):
        organisations_client.update_organisation(
            self.id, cached_service_ids=self.service_ids if delete_services_cache else None, **kwargs
        )

    def associate_service(self, service_id):
        organisations_client.update_service_organisation(service_id, self.id)

    def services_and_usage(self, financial_year):
        return organisations_client.get_services_and_usage(self.id, financial_year)


class Organisations(SerialisedModelCollection):
    model = Organisation


class AllOrganisations(ModelList, Organisations):
    client_method = organisations_client.get_organisations
