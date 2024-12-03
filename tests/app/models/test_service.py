import pytest

from app.models.organisation import Organisation
from app.models.service import Service
from tests import organisation_json
from tests.conftest import ORGANISATION_ID, create_folder, create_template


def test_organisation_type_when_services_organisation_has_no_org_type(mocker, service_one):
    service = Service(service_one)
    service._dict["organisation_id"] = ORGANISATION_ID
    org = organisation_json(organisation_type=None)
    mocker.patch("app.organisations_client.get_organisation", return_value=org)

    assert not org["organisation_type"]
    assert service.organisation_type == "central"


def test_organisation_type_when_service_and_its_org_both_have_an_org_type(mocker, service_one):
    # service_one has an organisation_type of 'central'
    service = Service(service_one)
    service._dict["organisation"] = ORGANISATION_ID
    org = organisation_json(organisation_type="local")
    mocker.patch("app.organisations_client.get_organisation", return_value=org)

    assert service.organisation_type == "local"


def test_service_without_organisation_doesnt_need_org_api(mocker, service_one):
    mock_get_organisation = mocker.patch("app.organisations_client.get_organisation")
    service = Service(service_one)
    service._dict["organisation"] = None

    assert service.organisation_id is None
    assert service.organisation_name is None
    assert isinstance(service.organisation, Organisation)

    assert mock_get_organisation.called is False


def test_bad_permission_raises(service_one):
    with pytest.raises(KeyError) as e:
        Service(service_one).has_permission("foo")
    assert str(e.value) == "'foo is not a service permission'"


def test_has_templates_of_type_includes_folders(
    mocker,
    service_one,
    mock_get_template_folders,
):
    mocker.patch(
        "app.service_api_client.get_service_templates",
        return_value={"data": [create_template(folder="something", template_type="broadcast")]},
    )

    mocker.patch("app.template_folder_api_client.get_template_folders", return_value=[create_folder(id="something")])

    assert Service(service_one).has_templates_of_type("broadcast")
