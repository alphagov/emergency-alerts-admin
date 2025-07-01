import math
import weakref
from datetime import datetime, timedelta, timezone
from itertools import chain
from numbers import Number

import pytz
from emergency_alerts_utils.admin_action import ADMIN_SENSITIVE_PERMISSIONS
from emergency_alerts_utils.formatters import strip_all_whitespace
from emergency_alerts_utils.insensitive_dict import InsensitiveDict
from emergency_alerts_utils.validation import InvalidPhoneError, validate_phone_number
from flask import request
from flask_login import current_user
from flask_wtf import FlaskForm as Form
from markupsafe import Markup
from werkzeug.utils import cached_property
from wtforms import (
    BooleanField,
    DateField,
    DecimalField,
    EmailField,
    Field,
    FieldList,
    HiddenField,
    IntegerField,
    PasswordField,
)
from wtforms import RadioField as WTFormsRadioField
from wtforms import (
    SearchField,
    SelectMultipleField,
    StringField,
    TelField,
    TextAreaField,
    ValidationError,
    validators,
)
from wtforms.validators import (
    UUID,
    DataRequired,
    InputRequired,
    Length,
    NumberRange,
    Optional,
    Regexp,
)

from app.config import BroadcastProvider
from app.formatters import (
    format_auth_type,
    guess_name_from_email_address,
    parse_seconds_as_hours_and_minutes,
)
from app.main.validators import (
    BroadcastLength,
    CharactersNotAllowed,
    CommonlyUsedPassword,
    IsPostcode,
    LowEntropyPassword,
    MobileNumberMustBeDifferent,
    MustContainAlphanumericCharacters,
    NameMustBeDifferent,
    NoCommasInPlaceHolders,
    NoPlaceholders,
    Only2DecimalPlaces,
    Only6DecimalPlaces,
    OnlySMSCharacters,
    StringsNotAllowed,
    ValidEmail,
    ValidGovEmail,
)
from app.models.feedback import PROBLEM_TICKET_TYPE, QUESTION_TICKET_TYPE
from app.models.organisation import Organisation
from app.utils.govuk_frontend_field import (
    GovukFrontendWidgetMixin,
    render_govuk_frontend_macro,
)
from app.utils.user import distinct_email_addresses
from app.utils.user_permissions import (
    all_ui_permissions,
    broadcast_permission_options,
    permission_options,
)


def get_time_value_and_label(future_time):
    return (
        future_time.replace(tzinfo=None).isoformat(),
        "{} at {}".format(
            get_human_day(future_time.astimezone(pytz.timezone("Europe/London"))),
            get_human_time(future_time.astimezone(pytz.timezone("Europe/London"))),
        ),
    )


def get_human_time(time):
    return {"0": "midnight", "12": "midday"}.get(time.strftime("%-H"), time.strftime("%-I%p").lower())


def get_human_day(time, prefix_today_with="T"):
    #  Add 1 hour to get ‘midnight today’ instead of ‘midnight tomorrow’
    time = (time - timedelta(hours=1)).strftime("%A")
    if time == datetime.now(timezone.utc).strftime("%A"):
        return "{}oday".format(prefix_today_with)
    if time == (datetime.now(timezone.utc) + timedelta(days=1)).strftime("%A"):
        return "Tomorrow"
    return time


def get_furthest_possible_scheduled_time():
    return (datetime.now(timezone.utc) + timedelta(days=4)).replace(hour=0)


def get_next_hours_until(until):
    now = datetime.now(timezone.utc)
    hours = int((until - now).total_seconds() / (60 * 60))
    return [
        (now + timedelta(hours=i)).replace(minute=0, second=0, microsecond=0).replace(tzinfo=pytz.utc)
        for i in range(1, hours + 1)
    ]


def get_next_days_until(until):
    now = datetime.now(timezone.utc)
    days = int((until - now).total_seconds() / (60 * 60 * 24))
    return [
        get_human_day((now + timedelta(days=i)).replace(tzinfo=pytz.utc), prefix_today_with="Later t")
        for i in range(0, days + 1)
    ]


class RadioField(WTFormsRadioField):
    def __init__(self, *args, thing="an option", **kwargs):
        super().__init__(*args, **kwargs)
        self.thing = thing
        self.validate_choice = False

    def pre_validate(self, form):
        super().pre_validate(form)
        if self.data not in dict(self.choices).keys():
            raise ValidationError(f"Select {self.thing}")


def email_address(label="Email address", gov_user=True, required=True):
    validators = [
        ValidEmail(),
    ]

    if gov_user:
        validators.append(ValidGovEmail())

    if required:
        validators.append(DataRequired(message="Enter a valid email address"))

    return GovukEmailField(label, validators)


class RequiredValidatorsMixin(Field):
    """
    A mixin for use if there are ever required validators you want to always apply, regardless of what a subclass does
    or how the field is invoked.

    Normally if you pass `validators` in a Field.__init__, that list overrides any base class validators entirely.
    This isn't always desirable, for example, we might want to ensure that all our files are virus scanned regardless
    of whether they pass other validators (filesize, is the file openable, etc)

    To set these, use this mixin then specify `required_validators` as a class variable.
    Note that these validators will be run before any other validators passed in through the field constructor.

    This inherits from Field to ensure that it gets invoked before the `Field` constructor
    (which actually takes the validators and saves them)
    """

    required_validators = []

    def __init__(self, *args, validators=None, **kwargs):
        if validators is None:
            validators = []
        # make a copy of `self.required_validators` to ensure it's not shared with other instances of this field
        super().__init__(*args, validators=(self.required_validators[:] + validators), **kwargs)


class GovukTextInputFieldMixin(GovukFrontendWidgetMixin):
    input_type = "text"
    govuk_frontend_component_name = "text-input"

    def prepare_params(self, **kwargs):
        value = kwargs["value"] if "value" in kwargs else self._value()
        value = str(value) if isinstance(value, Number) else value

        error_message_format = "html" if kwargs.get("error_message_with_html") else "text"

        # convert to parameters that govuk understands
        params = {
            "classes": "govuk-!-width-two-thirds",
            "errorMessage": self.get_error_message(error_message_format),
            "id": self.id,
            "label": {"text": self.label.text},
            "name": self.name,
            "value": value,
            "type": self.input_type,
        }

        return params


class UKMobileNumber(GovukTextInputFieldMixin, TelField):
    input_type = "tel"

    def pre_validate(self, form):
        try:
            validate_phone_number(self.data)
        except InvalidPhoneError as e:
            raise ValidationError(str(e))


class InternationalPhoneNumber(UKMobileNumber, GovukTextInputFieldMixin, TelField):
    def pre_validate(self, form):
        try:
            if self.data:
                validate_phone_number(self.data, international=True)
        except InvalidPhoneError as e:
            raise ValidationError(str(e))


def uk_mobile_number(label="Mobile number"):
    return UKMobileNumber(label, validators=[DataRequired(message="Cannot be empty")])


def international_phone_number(label="Mobile number"):
    return InternationalPhoneNumber(label, validators=[DataRequired(message="Enter a valid mobile number")])


def mobile_number(label="Mobile number"):
    return InternationalPhoneNumber(
        label, validators=[DataRequired(message="Enter a valid mobile number"), MobileNumberMustBeDifferent()]
    )


def password():
    return GovukPasswordField(
        label="New password",
        validators=[
            DataRequired(message="Cannot be empty"),
            Length(8, 255, message="Must be at least 8 characters"),
            CommonlyUsedPassword(message="Choose a password that’s harder to guess"),
            LowEntropyPassword(),
        ],
    )


def existing_password(label="Password"):
    return GovukPasswordField(
        label,
        validators=[DataRequired(message="Cannot be empty"), Length(8, 255, message="Must be at least 8 characters")],
    )


class GovukTextInputField(GovukTextInputFieldMixin, StringField):
    pass


class GovukPasswordField(GovukTextInputFieldMixin, PasswordField):
    input_type = "password"


class GovukEmailField(GovukTextInputFieldMixin, EmailField):
    input_type = "email"
    param_extensions = {"spellcheck": False}  # email addresses don't need to be spellchecked


class GovukSearchField(GovukTextInputFieldMixin, SearchField):
    input_type = "search"
    param_extensions = {"classes": "govuk-!-width-full"}  # email addresses don't need to be spellchecked


class GovukDateField(GovukTextInputFieldMixin, DateField):
    pass


class GovukIntegerField(GovukTextInputFieldMixin, IntegerField):
    pass


class GovukDecimalField(GovukTextInputFieldMixin, DecimalField):
    pass


class PostcodeSearchField(GovukTextInputFieldMixin, SearchField):
    input_type = "Search"
    param_extensions = {"classes": "govuk-input--width-10"}
    validators = [DataRequired(message="Enter a postcode within the UK"), IsPostcode()]


class SMSCode(GovukTextInputField):
    # the design system recommends against ever using `type="number"`. "tel" makes mobile browsers
    # show a phone keypad input rather than a full qwerty keyboard.
    input_type = "tel"
    param_extensions = {"attributes": {"pattern": "[0-9]*"}}
    validators = [
        DataRequired(message="Cannot be empty"),
        Regexp(regex=r"^\d+$", message="Numbers only"),
        Length(min=7, message="Not enough numbers"),
        Length(max=7, message="Too many numbers"),
    ]

    def process_formdata(self, valuelist):
        if valuelist:
            self.data = InsensitiveDict.make_key(valuelist[0])


class FieldWithNoneOption:
    # This is a special value that is specific to our forms. This is
    # more expicit than casting `None` to a string `'None'` which can
    # have unexpected edge cases
    NONE_OPTION_VALUE = "__NONE__"

    # When receiving Python data, eg when instantiating the form object
    # we want to convert that data to our special value, so that it gets
    # recognised as being one of the valid choices
    def process_data(self, value):
        self.data = self.NONE_OPTION_VALUE if value is None else value

    # After validation we want to convert it back to a Python `None` for
    # use elsewhere, eg posting to the API
    def post_validate(self, form, validation_stopped):
        if self.data == self.NONE_OPTION_VALUE and not validation_stopped:
            self.data = None


class RadioFieldWithNoneOption(FieldWithNoneOption, RadioField):
    pass


class NestedFieldMixin:
    def children(self):
        # start map with root option as a single child entry
        child_map = {None: [option for option in self if option.data == self.NONE_OPTION_VALUE]}

        # add entries for all other children
        for option in self:
            # assign all options with a NONE_OPTION_VALUE (not always None) to the None key
            if option.data == self.NONE_OPTION_VALUE:
                child_ids = [folder["id"] for folder in self.all_template_folders if folder["parent_id"] is None]
                key = self.NONE_OPTION_VALUE
            else:
                child_ids = [folder["id"] for folder in self.all_template_folders if folder["parent_id"] == option.data]
                key = option.data

            child_map[key] = [option for option in self if option.data in child_ids]

        return child_map

    # to be used as the only version of .children once radios are converted
    @cached_property
    def _children(self):
        return self.children()

    def get_items_from_options(self, field):
        items = []

        for option in self._children[None]:
            item = self.get_item_from_option(option)
            if option.data in self._children:
                item["children"] = self.render_children(field.name, option.label.text, self._children[option.data])
            items.append(item)

        return items

    def render_children(self, name, label, options):
        params = {
            "name": name,
            "fieldset": {"legend": {"text": label, "classes": "govuk-visually-hidden"}},
            "formGroup": {"classes": "govuk-form-group--nested"},
            "asList": True,
            "items": [],
        }
        for option in options:
            item = self.get_item_from_option(option)

            if len(self._children[option.data]):
                item["children"] = self.render_children(name, option.label.text, self._children[option.data])

            params["items"].append(item)

        return render_govuk_frontend_macro(self.govuk_frontend_component_name, params=params)


class NestedRadioField(RadioFieldWithNoneOption, NestedFieldMixin):
    pass


class NestedCheckboxesField(SelectMultipleField, NestedFieldMixin):
    NONE_OPTION_VALUE = None


class HiddenFieldWithNoneOption(FieldWithNoneOption, HiddenField):
    pass


class RadioFieldWithRequiredMessage(RadioField):
    def __init__(self, *args, required_message="Not a valid choice", **kwargs):
        self.required_message = required_message
        super().__init__(*args, **kwargs)

    def pre_validate(self, form):
        try:
            return super().pre_validate(form)
        except ValueError:
            raise ValidationError(self.required_message)


class StripWhitespaceForm(Form):
    class Meta:
        def bind_field(self, form, unbound_field, options):
            # FieldList simply doesn't support filters.
            # @see: https://github.com/wtforms/wtforms/issues/148
            no_filter_fields = (FieldList, PasswordField, GovukPasswordField)
            filters = [strip_all_whitespace] if not issubclass(unbound_field.field_class, no_filter_fields) else []
            filters += unbound_field.kwargs.get("filters", [])
            bound = unbound_field.bind(form=form, filters=filters, **options)
            bound.get_form = weakref.ref(form)  # GC won't collect the form if we don't use a weakref
            return bound

        def render_field(self, field, render_kw):
            render_kw.setdefault("required", False)
            return super().render_field(field, render_kw)


class StripWhitespaceStringField(GovukTextInputField):
    def __init__(self, label=None, **kwargs):
        kwargs["filters"] = tuple(
            chain(
                kwargs.get("filters", ()),
                (strip_all_whitespace,),
            )
        )
        super(GovukTextInputField, self).__init__(label, **kwargs)


class LoginForm(StripWhitespaceForm):
    email_address = GovukEmailField(
        "Email address", validators=[Length(min=5, max=255), DataRequired(message="Cannot be empty"), ValidEmail()]
    )
    password = GovukPasswordField("Password", validators=[DataRequired(message="Enter your password")])


class RegisterUserForm(StripWhitespaceForm):
    name = GovukTextInputField("Full name", validators=[DataRequired(message="Cannot be empty")])
    email_address = email_address()
    mobile_number = international_phone_number()
    password = password()
    # always register as sms type
    auth_type = HiddenField("auth_type", default="sms_auth")


class RegisterUserFromInviteForm(RegisterUserForm):
    def __init__(self, invited_user):
        super().__init__(
            service=invited_user.service,
            email_address=invited_user.email_address,
            auth_type=invited_user.auth_type,
            name=guess_name_from_email_address(invited_user.email_address),
        )

    mobile_number = InternationalPhoneNumber("Mobile number", validators=[])
    service = HiddenField("service")
    email_address = HiddenField("email_address")
    auth_type = HiddenField("auth_type", validators=[DataRequired()])

    def validate_mobile_number(self, field):
        if self.auth_type.data == "sms_auth" and not field.data:
            raise ValidationError("Cannot be empty")


class RegisterUserFromOrgInviteForm(StripWhitespaceForm):
    def __init__(self, invited_org_user):
        super().__init__(
            organisation=invited_org_user.organisation,
            email_address=invited_org_user.email_address,
        )

    name = GovukTextInputField("Full name", validators=[DataRequired(message="Cannot be empty")])

    mobile_number = InternationalPhoneNumber("Mobile number", validators=[DataRequired(message="Cannot be empty")])
    password = password()
    organisation = HiddenField("organisation")
    email_address = HiddenField("email_address")
    auth_type = HiddenField("auth_type", validators=[DataRequired()])


class GovukCheckboxField(GovukFrontendWidgetMixin, BooleanField):
    govuk_frontend_component_name = "checkbox"

    def prepare_params(self, **kwargs):
        params = {
            "name": self.name,
            "errorMessage": self.get_error_message(),
            "items": [
                {
                    "name": self.name,
                    "id": self.id,
                    "text": self.label.text,
                    "value": self._value(),
                    "checked": self.data,
                }
            ],
        }
        return params


class GovukTextareaField(GovukFrontendWidgetMixin, TextAreaField):
    govuk_frontend_component_name = "textarea"

    def prepare_params(self, **kwargs):
        # error messages
        error_message = None
        if self.errors:
            error_message = {"text": self.errors[0]}

        params = {
            "name": self.name,
            "id": self.id,
            "rows": 8,
            "label": {"text": self.label.text, "classes": None, "isPageHeading": False},
            "hint": {"text": None},
            "errorMessage": error_message,
        }

        return params


# based on work done by @richardjpope: https://github.com/richardjpope/recourse/blob/master/recourse/forms.py#L6
class GovukCheckboxesField(GovukFrontendWidgetMixin, SelectMultipleField):
    govuk_frontend_component_name = "checkbox"
    render_as_list = False

    def get_item_from_option(self, option):
        return {
            "name": option.name,
            "id": option.id,
            "text": option.label.text,
            "value": option._value(),
            "checked": option.checked,
        }

    def get_items_from_options(self, field):
        return [self.get_item_from_option(option) for option in field]

    def prepare_params(self, **kwargs):
        # returns either a list or a hierarchy of lists
        # depending on how get_items_from_options is implemented
        items = self.get_items_from_options(self)

        params = {
            "name": self.name,
            "fieldset": {
                "attributes": {"id": self.name},
                "legend": {"text": self.label.text, "classes": "govuk-fieldset__legend--s"},
            },
            "asList": self.render_as_list,
            "errorMessage": self.get_error_message(),
            "items": items,
            "hint": {"text": "Select all that apply."},
        }

        return params


class GovukCheckboxesFieldWithNetworkRequired(GovukCheckboxesField):
    validators = [DataRequired("Select a mobile network")]


class GovukCheckboxesFieldWithSensitivePermissionAttribute(GovukCheckboxesField):
    def get_item_from_option(self, option):
        item = super().get_item_from_option(option)
        item["attributes"] = (
            {"data-permission-sensitive": "true"} if item["value"] in ADMIN_SENSITIVE_PERMISSIONS else {}
        )
        return item


# Wraps checkboxes rendering in HTML needed by the collapsible JS
class GovukCollapsibleCheckboxesField(GovukCheckboxesField):
    param_extensions = {"hint": {"html": '<div class="selection-summary" role="region" aria-live="polite"></div>'}}

    def __init__(self, *args, field_label="", **kwargs):
        self.field_label = field_label
        super().__init__(*args, **kwargs)

    def widget(self, *args, **kwargs):
        checkboxes_string = super().widget(*args, **kwargs)

        # wrap the checkboxes HTML in the HTML needed by the collapsible JS
        result = Markup(
            f'<div class="selection-wrapper"'
            f'     data-notify-module="collapsible-checkboxes"'
            f'     data-field-label="{self.field_label}">'
            f"  {checkboxes_string}"
            f"</div>"
        )

        return result


# GovukCollapsibleCheckboxesField adds an ARIA live-region to the hint and wraps the render in HTML needed by the
# collapsible JS
# NestedFieldMixin puts the items into a tree hierarchy, pre-rendering the sub-trees of the top-level items
class GovukCollapsibleNestedCheckboxesField(NestedFieldMixin, GovukCollapsibleCheckboxesField):
    NONE_OPTION_VALUE = None
    render_as_list = True


class GovukRadiosField(GovukFrontendWidgetMixin, RadioField):
    govuk_frontend_component_name = "radios"

    class Divider(str):
        """
        Behaves like a normal string but can be used instead of a `(value, label)`
        pair as one of the items in `GovukRadiosField.choices`, for example:

            numbers = GovukRadiosField(choices=(
                (1, "One"),
                (2, "Two"),
                GovukRadiosField.Divider("or")
                (3, "Three"),
            ))

        When rendered it won’t appear as a choice the user can click, but instead
        as text in between the choices, as per:
        https://design-system.service.gov.uk/components/radios/#radio-items-with-a-text-divider
        """

        def __iter__(self):
            # This is what WTForms will use as the value of the choice. We will
            # throw this away, but needs to be unique, unguessable and impossible
            # to confuse with a real choice
            yield object()
            # This is what WTForms will use as the label, which we can later
            # use to see if the choice is actually a divider
            yield self

    def get_item_from_option(self, option):
        if isinstance(option.label.text, self.Divider):
            return {
                "divider": option.label.text,
            }
        return {
            "name": option.name,
            "id": option.id,
            "text": option.label.text,
            "value": option._value(),
            "checked": option.checked,
        }

    def get_items_from_options(self, field):
        return [self.get_item_from_option(option) for option in field]

    def prepare_params(self, **kwargs):
        # returns either a list or a hierarchy of lists
        # depending on how get_items_from_options is implemented
        items = self.get_items_from_options(self)

        return {
            "name": self.name,
            "fieldset": {
                "attributes": {"id": self.name},
                "legend": {"text": self.label.text, "classes": "govuk-fieldset__legend--s"},
            },
            "errorMessage": self.get_error_message(),
            "items": items,
        }


class OptionalGovukRadiosField(GovukRadiosField):
    def pre_validate(self, form):
        if self.data is None:
            return
        super().pre_validate(form)


class OnOffField(GovukRadiosField):
    def __init__(self, label, choices=None, *args, **kwargs):
        choices = choices or [
            (True, "On"),
            (False, "Off"),
        ]
        super().__init__(
            label,
            choices=choices,
            thing=f"{choices[0][1].lower()} or {choices[1][1].lower()}",
            *args,
            **kwargs,
        )

    def process_formdata(self, valuelist):
        if valuelist:
            value = valuelist[0]
            self.data = (value == "True") if value in ["True", "False"] else value

    def iter_choices(self):
        for value, label in self.choices:
            # This overrides WTForms default behaviour which is to check
            # self.coerce(value) == self.data
            # where self.coerce returns a string for a boolean input
            yield (value, label, (self.data in {value, self.coerce(value)}))


class OrganisationTypeField(GovukRadiosField):
    def __init__(self, *args, include_only=None, validators=None, **kwargs):
        super().__init__(
            *args,
            choices=[
                (value, label)
                for value, label in Organisation.TYPE_LABELS.items()
                if not include_only or value in include_only
            ],
            thing="the type of organisation",
            validators=validators or [],
            **kwargs,
        )


class GovukRadiosFieldWithNoneOption(FieldWithNoneOption, GovukRadiosField):
    pass


class GovukRadiosWithImagesField(GovukRadiosField):
    govuk_frontend_component_name = "radios-with-images"

    param_extensions = {
        "classes": "govuk-radios--inline",
        "fieldset": {"legend": {"classes": "govuk-fieldset__legend--l", "isPageHeading": True}},
    }

    def __init__(self, label="", *, image_data, **kwargs):
        super(GovukRadiosField, self).__init__(label, **kwargs)

        self.image_data = image_data

    def get_item_from_option(self, option):
        return {
            "name": option.name,
            "id": option.id,
            "text": option.label.text,
            "value": str(option.data),  # to protect against non-string types like uuids
            "checked": option.checked,
            "image": self.image_data[option.data],
        }


# guard against data entries that aren't a known permission
def filter_by_permissions(valuelist):
    if valuelist is None:
        return None
    else:
        return [entry for entry in valuelist if any(entry in option for option in permission_options)]


# guard against data entries that aren't a known broadcast permission
def filter_by_broadcast_permissions(valuelist):
    if valuelist is None:
        return None
    else:
        return [entry for entry in valuelist if any(entry in option for option in broadcast_permission_options)]


class AuthTypeForm(StripWhitespaceForm):
    auth_type = GovukRadiosField(
        "Sign in using",
        choices=[
            ("sms_auth", format_auth_type("sms_auth")),
            ("email_auth", format_auth_type("email_auth")),
        ],
    )


class BasePermissionsForm(StripWhitespaceForm):
    def __init__(self, all_template_folders=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.folder_permissions.choices = []
        if all_template_folders is not None:
            self.folder_permissions.all_template_folders = all_template_folders
            self.folder_permissions.choices = [
                (item["id"], item["name"]) for item in ([{"name": "Templates", "id": None}] + all_template_folders)
            ]

    folder_permissions = GovukCollapsibleNestedCheckboxesField("Folders this team member can see", field_label="folder")

    login_authentication = GovukRadiosField(
        "Sign in using",
        choices=[
            ("sms_auth", "Text message code"),
            ("email_auth", "Email link"),
            ("webauthn_auth", "WebAuthn verification"),
        ],
        thing="how this team member should sign in",
        validators=[DataRequired()],
    )

    permissions_field = GovukCheckboxesField(
        "Permissions",
        filters=[filter_by_permissions],
        choices=[(value, label) for value, label in permission_options],
        param_extensions={"hint": {"text": "All team members can see sent messages."}},
    )

    @property
    def permissions(self):
        return set(self.permissions_field.data)

    @classmethod
    def from_user(cls, user, service_id, **kwargs):
        form = cls(
            **kwargs,
            **{"permissions_field": (user.permissions_for_service(service_id) & all_ui_permissions)},
            login_authentication=user.auth_type,
        )

        # If a user logs in with a security key, we generally don't want a service admin to be able to change this.
        # As well as enforcing this in the backend, we need to delete the auth radios to prevent validation errors.
        if user.webauthn_auth:
            del form.login_authentication
        return form


class PermissionsForm(BasePermissionsForm):
    pass


class BroadcastPermissionsForm(BasePermissionsForm):
    permissions_field = GovukCheckboxesFieldWithSensitivePermissionAttribute(
        "Permissions",
        choices=[(value, label) for value, label in broadcast_permission_options],
        filters=[filter_by_broadcast_permissions],
        param_extensions={
            "hint": {
                "text": "Team members who can create or approve alerts can also reject them."
                + " Platform admin approval is required to enable creating or approving alerts."
            },
        },
    )

    @property
    def permissions(self):
        return {"view_activity"} | super().permissions


class BaseInviteUserForm:
    email_address = email_address(gov_user=False)

    def __init__(self, inviter_email_address, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.inviter_email_address = inviter_email_address

    def validate_email_address(self, field):
        if current_user.platform_admin:
            return
        if field.data.lower() == self.inviter_email_address.lower():
            raise ValidationError("You cannot send an invitation to yourself")


class InviteUserForm(BaseInviteUserForm, PermissionsForm):
    pass


class BroadcastInviteUserForm(BaseInviteUserForm, BroadcastPermissionsForm):
    email_address = email_address(gov_user=True)

    def validate_email_address(self, field):
        if not distinct_email_addresses(field.data, self.inviter_email_address):
            raise ValidationError("You cannot send an invitation to yourself")


class InviteOrgUserForm(BaseInviteUserForm, StripWhitespaceForm):
    pass


class TwoFactorForm(StripWhitespaceForm):
    def __init__(self, validate_code_func, *args, **kwargs):
        """
        Keyword arguments:
        validate_code_func -- Validates the code with the API.
        """
        self.validate_code_func = validate_code_func
        super(TwoFactorForm, self).__init__(*args, **kwargs)

    sms_code = SMSCode("Text message code")

    def validate(self, extra_validators=None):
        if not self.sms_code.validate(self):
            return False

        is_valid, reason = self.validate_code_func(self.sms_code.data)

        if not is_valid:
            self.sms_code.errors.append(reason)
            return False

        return True


class TextNotReceivedForm(StripWhitespaceForm):
    mobile_number = international_phone_number()


class RenameServiceForm(StripWhitespaceForm):
    name = GovukTextInputField(
        "Service name",
        validators=[
            DataRequired(message="Cannot be empty"),
            MustContainAlphanumericCharacters(),
            Length(max=255, message="Service name must be 255 characters or fewer"),
        ],
    )


class RenameOrganisationForm(StripWhitespaceForm):
    name = GovukTextInputField(
        "Organisation name",
        validators=[
            DataRequired(message="Cannot be empty"),
            MustContainAlphanumericCharacters(),
            Length(max=255, message="Organisation name must be 255 characters or fewer"),
        ],
    )


class OrganisationOrganisationTypeForm(StripWhitespaceForm):
    organisation_type = OrganisationTypeField("What type of organisation is this?")


class OrganisationCrownStatusForm(StripWhitespaceForm):
    crown_status = GovukRadiosField(
        "Is this organisation a crown body?",
        choices=[
            ("crown", "Yes"),
            ("non-crown", "No"),
            ("unknown", "Not sure"),
        ],
        thing="whether this organisation is a crown body",
    )


class AdminOrganisationDomainsForm(StripWhitespaceForm):
    def populate(self, domains_list):
        for index, value in enumerate(domains_list):
            self.domains[index].data = value

    domains = FieldList(
        StripWhitespaceStringField(
            "",
            validators=[
                CharactersNotAllowed("@"),
                StringsNotAllowed("nhs.uk", "nhs.net"),
                Optional(),
            ],
            default="",
        ),
        min_entries=20,
        max_entries=20,
        label="Domain names",
    )


class CreateServiceForm(StripWhitespaceForm):
    name = GovukTextInputField(
        "What’s your service called?",
        validators=[
            DataRequired(message="Cannot be empty"),
            MustContainAlphanumericCharacters(),
            Length(max=255, message="Service name must be 255 characters or fewer"),
        ],
    )
    organisation_type = OrganisationTypeField("Who runs this service?")


class AdminNewOrganisationForm(
    RenameOrganisationForm,
    OrganisationOrganisationTypeForm,
    OrganisationCrownStatusForm,
):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Don’t offer the ‘not sure’ choice
        self.crown_status.choices = self.crown_status.choices[:-1]


class ConfirmPasswordForm(StripWhitespaceForm):
    def __init__(self, validate_password_func, *args, **kwargs):
        self.validate_password_func = validate_password_func
        super(ConfirmPasswordForm, self).__init__(*args, **kwargs)

    password = GovukPasswordField("Enter password")

    def validate_password(self, field):
        if not self.validate_password_func(field.data):
            raise ValidationError("Invalid password")


class NewBroadcastForm(StripWhitespaceForm):
    content = GovukRadiosField(
        "Create new alert",
        choices=[
            ("freeform", "Write your own message"),
            ("template", "Use a template"),
        ],
        param_extensions={
            "fieldset": {"legend": {"classes": "govuk-visually-hidden"}},
            "hint": {"text": "Select one option"},
        },
        validators=[DataRequired(message="Select if you want to write your own message or use a template")],
    )

    @property
    def use_template(self):
        return self.content.data == "template"


class ChooseExtraContentForm(StripWhitespaceForm):
    content = GovukRadiosField(
        "Would you like to add extra content to the alert?",
        choices=[
            ("yes", "Yes"),
            ("no", "No"),
        ],
        param_extensions={
            "fieldset": {"legend": {"classes": "govuk-visually-hidden"}},
            "hint": {
                "html": """<p>This won't be sent to those receiving the alert, but will be displayed as part
                     of the alert on <a href='https://www.gov.uk/alerts'>gov.uk/alerts</a>. </p>
                     <p>Select one option.</p>"""
            },
        },
        validators=[DataRequired(message="Select whether or not to add additional text to alert")],
    )


class ConfirmBroadcastForm(StripWhitespaceForm):
    def __init__(self, *args, service_is_live, channel, max_phones, **kwargs):
        super().__init__(*args, **kwargs)

        self.confirm.label.text = self.generate_label(channel, max_phones)

        if service_is_live:
            self.confirm.validators += (DataRequired("You need to confirm that you understand"),)

    confirm = GovukCheckboxField("Confirm")

    @staticmethod
    def generate_label(channel, max_phones):
        if channel in {"test", "operator"}:
            return f"I understand this will alert anyone who has switched on the {channel} channel"
        if channel == "severe":
            return f"I understand this will alert {ConfirmBroadcastForm.format_number_generic(max_phones)} of people"
        if channel == "government":
            return (
                f"I understand this will alert {ConfirmBroadcastForm.format_number_generic(max_phones)} "
                "of people, even if they’ve opted out"
            )

    @staticmethod
    def format_number_generic(count):
        for threshold, message in (
            (1_000_000, "millions"),
            (100_000, "hundreds of thousands"),
            (10_000, "tens of thousands"),
            (1_000, "thousands"),
            (100, "hundreds"),
            (-math.inf, "an unknown number"),
        ):
            if count >= threshold:
                return message


class BaseTemplateForm(StripWhitespaceForm):
    name = GovukTextInputField("Template name", validators=[DataRequired(message="Template name cannot be empty")])

    template_content = TextAreaField(
        "Alert message", validators=[DataRequired(message="Alert message cannot be empty"), NoCommasInPlaceHolders()]
    )


class ChooseDurationForm(StripWhitespaceForm):
    def __init__(self, channel, duration, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.channel = channel
        if duration is None:
            if self.hours.data is None and self.minutes.data is None:
                if channel in ["test", "operator"]:
                    self.hours.data = 4
                    self.minutes.data = 0
                else:
                    self.hours.data = 22
                    self.minutes.data = 30
        elif self.hours.data is None and self.minutes.data is None:
            (hours, minutes) = parse_seconds_as_hours_and_minutes(duration)
            self.hours.data = hours
            self.minutes.data = minutes

    hours = GovukIntegerField(
        validators=[
            InputRequired("Hours required"),
            NumberRange(min=0, max=22, message="Hours must be between 0 and 22"),
        ],
        param_extensions={
            "hint": {"text": "Hours"},
        },
    )
    minutes = GovukIntegerField(
        validators=[
            InputRequired("Minutes required"),
            NumberRange(min=0, max=59, message="Minutes must be between 0 and 59"),
        ],
        param_extensions={
            "hint": {"text": "Minutes"},
        },
    )

    def validate(self, **kwargs):
        if not super().validate(**kwargs):
            return False

        channel = self.channel
        hours = self.hours.data
        minutes = self.minutes.data

        duration = timedelta(hours=hours, minutes=minutes)

        if duration < timedelta(minutes=30):
            self.minutes.errors.append("Duration must be at least 30 minutes")

        if channel in ["test", "operator"]:
            if duration > timedelta(hours=4):
                if hours > 4:
                    self.hours.errors.append("Duration must not be greater than 4 hours")
                if hours == 4:
                    self.minutes.errors.append("Duration must not be greater than 4 hours")
                return False
        elif channel in ["government", "severe"]:
            if duration > timedelta(hours=22, minutes=30):
                if hours > 22:
                    self.hours.errors.append("Maximum duration is 22 hours, 30 minutes")
                if hours == 22:
                    self.minutes.errors.append("Maximum duration is 22 hours, 30 minutes")
                return False
        return True


class SMSTemplateForm(BaseTemplateForm):
    def validate_template_content(self, field):
        OnlySMSCharacters(template_type="sms")(None, field)


class BroadcastTemplateForm(SMSTemplateForm):
    name = GovukTextInputField("Reference", validators=[DataRequired(message="Enter a reference")])
    template_content = TextAreaField(
        "Alert message", validators=[DataRequired(message="Enter an alert message"), NoCommasInPlaceHolders()]
    )
    # Hidden fields to store initial data and data on page when specific actions taken by user
    initial_name = HiddenField("initial_name")
    initial_content = HiddenField("initial_content")
    overwrite_name = BooleanField("overwrite_name", render_kw={"hidden": True})
    overwrite_content = BooleanField("overwrite_content", render_kw={"hidden": True})

    def validate_template_content(self, field):
        OnlySMSCharacters(template_type="broadcast")(None, field)
        NoPlaceholders()(None, field)
        BroadcastLength()(None, field)


class AddExtraContentForm(StripWhitespaceForm):
    extra_content = TextAreaField(
        "Extra content",
        validators=[DataRequired(message="Enter extra content"), NoCommasInPlaceHolders()],
    )


class ForgotPasswordForm(StripWhitespaceForm):
    email_address = email_address(gov_user=False)


class NewPasswordForm(StripWhitespaceForm):
    password = password()


class ChangePasswordForm(StripWhitespaceForm):
    def __init__(self, validate_password_func, *args, **kwargs):
        self.validate_password_func = validate_password_func
        super(ChangePasswordForm, self).__init__(*args, **kwargs)

    old_password = existing_password("Current password")
    new_password = password()

    def validate_old_password(self, field):
        if not self.validate_password_func(field.data):
            raise ValidationError("Invalid password")


class ChangeNameForm(StripWhitespaceForm):
    def __init__(self, validate_password_func, *args, **kwargs):
        self.validate_password_func = validate_password_func
        super(ChangeNameForm, self).__init__(*args, **kwargs)

    new_name = GovukTextInputField(
        "Your name",
        validators=[
            DataRequired(message="Enter a name"),
            NameMustBeDifferent("Name must be different to current name"),
        ],
    )

    password = GovukPasswordField("Enter password")

    def validate_password(self, field):
        if not self.validate_password_func(field.data):
            raise ValidationError("Invalid password")


class ChangeEmailForm(StripWhitespaceForm):
    def __init__(self, validate_email_func, validate_password_func, *args, **kwargs):
        self.validate_email_func = validate_email_func
        self.validate_password_func = validate_password_func
        super(ChangeEmailForm, self).__init__(*args, **kwargs)

    email_address = email_address()
    password = GovukPasswordField("Enter password")

    def validate_email_address(self, field):
        # The validate_email_func can be used to call API to check if the email address is already in
        # use. We don't want to run that check for invalid email addresses, since that will cause an error.
        # If there are any other validation errors on the email_address, we should skip this check.
        if self.email_address.errors:
            return

        is_valid = self.validate_email_func(field.data)
        if is_valid:
            raise ValidationError("The email address is already in use")

    def validate_password(self, field):
        if not self.validate_password_func(field.data):
            raise ValidationError("Invalid password")


class ChangeTeamMemberEmailForm(StripWhitespaceForm):
    def __init__(self, validate_email_func, *args, **kwargs):
        self.validate_email_func = validate_email_func
        super(ChangeTeamMemberEmailForm, self).__init__(*args, **kwargs)

    email_address = email_address()

    def validate_email_address(self, field):
        # The validate_email_func can be used to call API to check if the email address is already in
        # use. We don't want to run that check for invalid email addresses, since that will cause an error.
        # If there are any other validation errors on the email_address, we should skip this check.
        if self.email_address.errors:
            return

        is_valid = self.validate_email_func(field.data)
        if is_valid:
            raise ValidationError("The email address is already in use")


class ChangeNonGovEmailForm(ChangeTeamMemberEmailForm):
    email_address = email_address(gov_user=False)


class ChangeMobileNumberForm(StripWhitespaceForm):
    def __init__(self, validate_password_func, *args, **kwargs):
        self.validate_password_func = validate_password_func
        super(ChangeMobileNumberForm, self).__init__(*args, **kwargs)

    mobile_number = mobile_number()

    password = GovukPasswordField("Enter password")

    def validate_password(self, field):
        if not self.validate_password_func(field.data):
            raise ValidationError("Invalid password")


class ChangeTeamMemberMobileNumberForm(StripWhitespaceForm):
    mobile_number = international_phone_number()


class ChooseTimeForm(StripWhitespaceForm):
    def __init__(self, *args, **kwargs):
        super(ChooseTimeForm, self).__init__(*args, **kwargs)
        self.scheduled_for.choices = [("", "Now")] + [
            get_time_value_and_label(hour) for hour in get_next_hours_until(get_furthest_possible_scheduled_time())
        ]
        self.scheduled_for.categories = get_next_days_until(get_furthest_possible_scheduled_time())

    scheduled_for = GovukRadiosField(
        "When should Notify send these messages?",
        default="",
    )


class CreateKeyForm(StripWhitespaceForm):
    def __init__(self, existing_keys, *args, **kwargs):
        self.existing_key_names = [key["name"].lower() for key in existing_keys if not key["expiry_date"]]
        super().__init__(*args, **kwargs)

    key_type = GovukRadiosField(
        "Type of key",
        thing="the type of key",
    )

    key_name = GovukTextInputField(
        "Name for this key", validators=[DataRequired(message="You need to give the key a name")]
    )

    def validate_key_name(self, key_name):
        if key_name.data.lower() in self.existing_key_names:
            raise ValidationError("A key with this name already exists")


class SupportType(StripWhitespaceForm):
    support_type = GovukRadiosField(
        "How can we help you?",
        choices=[
            (PROBLEM_TICKET_TYPE, "Report a problem"),
            (QUESTION_TICKET_TYPE, "Ask a question or give feedback"),
        ],
    )


class SupportRedirect(StripWhitespaceForm):
    who = GovukRadiosField(
        "What do you need help with?",
        choices=[
            ("public-sector", "I work in the public sector and need support with the Emergency Alerts service"),
            ("public", "I’m a member of the public with a question for the government"),
        ],
    )


class FeedbackOrProblem(StripWhitespaceForm):
    name = GovukTextInputField("Name (optional)")
    email_address = email_address(label="Email address", gov_user=False, required=True)
    feedback = TextAreaField("Your message", validators=[DataRequired(message="Cannot be empty")])


class Triage(StripWhitespaceForm):
    severe = GovukRadiosField(
        "Is it an emergency?",
        choices=[
            ("yes", "Yes"),
            ("no", "No"),
        ],
        thing="yes or no",
    )


class AdminNotesForm(StripWhitespaceForm):
    notes = TextAreaField(validators=[])


class ServiceOnOffSettingForm(StripWhitespaceForm):
    def __init__(self, name, *args, truthy="On", falsey="Off", **kwargs):
        super().__init__(*args, **kwargs)
        self.enabled.label.text = name
        self.enabled.choices = [
            (True, truthy),
            (False, falsey),
        ]

    enabled = OnOffField("Choices")


class DateFilterForm(StripWhitespaceForm):
    start_date = GovukDateField("Start Date", [validators.optional()])
    end_date = GovukDateField("End Date", [validators.optional()])
    include_from_test_key = GovukCheckboxField("Include test keys")


class RequiredDateFilterForm(StripWhitespaceForm):
    start_date = GovukDateField("Start Date")
    end_date = GovukDateField("End Date")


class SearchByNameForm(StripWhitespaceForm):
    search = GovukSearchField(
        "Search by name",
        validators=[DataRequired("You need to enter full or partial name to search by.")],
    )


class AdminSearchUsersByEmailForm(StripWhitespaceForm):
    search = GovukSearchField(
        "Search and filter by name or email address",
        validators=[DataRequired("You need to enter full or partial email address to search by.")],
    )


class SearchUsersForm(StripWhitespaceForm):
    search = GovukSearchField("Search and filter by name or email address")


class SearchNotificationsForm(StripWhitespaceForm):
    to = GovukSearchField()

    labels = {
        "email": "Search by email address",
        "sms": "Search by phone number",
    }

    def __init__(self, message_type, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.to.label.text = self.labels.get(
            message_type,
            "Search by phone number or email address",
        )


class SearchTemplatesForm(StripWhitespaceForm):
    search = GovukSearchField()

    def __init__(self, api_keys, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.search.label.text = "Search and filter by name or ID" if api_keys else "Search and filter by name"


class PlaceholderForm(StripWhitespaceForm):
    pass


class SMSPrefixForm(StripWhitespaceForm):
    enabled = OnOffField("")  # label is assigned on instantiation


class SetTemplateSenderForm(StripWhitespaceForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.sender.choices = kwargs["sender_choices"]
        self.sender.label.text = "Select your sender"

    sender = GovukRadiosField()


class AdminSetOrganisationForm(StripWhitespaceForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.organisations.choices = kwargs["choices"]

    organisations = GovukRadiosField("Select an organisation", validators=[DataRequired()])


class TemplateFolderForm(StripWhitespaceForm):
    def __init__(self, all_service_users=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if all_service_users is not None:
            self.users_with_permission.all_service_users = all_service_users
            self.users_with_permission.choices = [(item.id, item.name) for item in all_service_users]

    users_with_permission = GovukCollapsibleCheckboxesField(
        "Team members who can see this folder", field_label="team member"
    )
    name = GovukTextInputField("Folder name", validators=[DataRequired(message="Cannot be empty")])


def required_for_ops(*operations):
    operations = set(operations)

    def validate(form, field):
        if form.op not in operations and any(field.raw_data):
            # super weird
            raise validators.StopValidation("Must be empty")
        if form.op in operations and not any(field.raw_data):
            raise validators.StopValidation("Cannot be empty")

    return validate


class TemplateAndFoldersSelectionForm(Form):
    """
    This form expects the form data to include an operation, based on which submit button is clicked.
    If enter is pressed, unknown will be sent by a hidden submit button at the top of the form.
    The value of this operation affects which fields are required, expected to be empty, or optional.

    * unknown
        currently not implemented, but in the future will try and work out if there are any obvious commands that can be
        assumed based on which fields are empty vs populated.
    * move-to-existing-folder
        must have data for templates_and_folders checkboxes, and move_to radios
    * move-to-new-folder
        must have data for move_to_new_folder_name, cannot have data for move_to_existing_folder_name
    * add-new-folder
        must have data for move_to_existing_folder_name, cannot have data for move_to_new_folder_name
    """

    ALL_TEMPLATES_FOLDER = {
        "name": "Templates",
        "id": RadioFieldWithNoneOption.NONE_OPTION_VALUE,
    }

    def __init__(
        self,
        all_template_folders,
        template_list,
        available_template_types,
        allow_adding_copy_of_template,
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)

        self.available_template_types = available_template_types

        self.templates_and_folders.choices = [(item.id, item.name) for item in template_list]

        self.op = None
        self.is_move_op = self.is_add_folder_op = self.is_add_template_op = False

        self.move_to.all_template_folders = all_template_folders
        self.move_to.choices = [
            (item["id"], item["name"]) for item in ([self.ALL_TEMPLATES_FOLDER] + all_template_folders)
        ]

        self.add_template_by_template_type.choices = list(
            filter(
                None,
                [
                    ("broadcast", "Broadcast") if "broadcast" in available_template_types else None,
                    ("copy-existing", "Copy an existing template") if allow_adding_copy_of_template else None,
                ],
            )
        )

    @property
    def trying_to_add_unavailable_template_type(self):
        return all(
            (
                self.is_add_template_op,
                self.add_template_by_template_type.data,
                self.add_template_by_template_type.data not in self.available_template_types,
            )
        )

    def is_selected(self, template_folder_id):
        return template_folder_id in (self.templates_and_folders.data or [])

    def validate(self, extra_validators=None):
        self.op = request.form.get("operation")

        self.is_move_op = self.op in {"move-to-existing-folder", "move-to-new-folder"}
        self.is_add_folder_op = self.op in {"add-new-folder", "move-to-new-folder"}
        self.is_add_template_op = self.op in {"add-new-template"}

        if not (self.is_add_folder_op or self.is_move_op or self.is_add_template_op):
            return False

        return super().validate(extra_validators)

    def get_folder_name(self):
        if self.op == "add-new-folder":
            return self.add_new_folder_name.data
        elif self.op == "move-to-new-folder":
            return self.move_to_new_folder_name.data
        return None

    templates_and_folders = GovukCheckboxesField(
        "Choose templates or folders",
        validators=[required_for_ops("move-to-new-folder", "move-to-existing-folder")],
        choices=[],  # added to keep order of arguments, added properly in __init__
        param_extensions={"fieldset": {"legend": {"classes": "govuk-visually-hidden"}}},
    )
    # if no default set, it is set to None, which process_data transforms to '__NONE__'
    # this means '__NONE__' (self.ALL_TEMPLATES option) is selected when no form data has been submitted
    # set default to empty string so process_data method doesn't perform any transformation
    move_to = NestedRadioField(
        "Choose a folder", default="", validators=[required_for_ops("move-to-existing-folder"), Optional()]
    )
    add_new_folder_name = GovukTextInputField("Folder name", validators=[required_for_ops("add-new-folder")])
    move_to_new_folder_name = GovukTextInputField("Folder name", validators=[required_for_ops("move-to-new-folder")])

    add_template_by_template_type = RadioFieldWithRequiredMessage(
        "New template",
        validators=[
            required_for_ops("add-new-template"),
            Optional(),
        ],
        required_message="Select the type of template you want to add",
    )


class ServiceBroadcastChannelForm(StripWhitespaceForm):
    channel = GovukRadiosField(
        "Emergency alerts settings",
        thing="mode or channel",
        choices=[
            ("training", "Training mode"),
            ("operator", "Operator channel"),
            ("test", "Test channel"),
            ("severe", "Live channel"),
            ("government", "Government channel"),
        ],
    )


class ServiceBroadcastNetworkForm(StripWhitespaceForm):
    def __init__(self, broadcast_channel, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.broadcast_channel = broadcast_channel

    networks = GovukCheckboxesFieldWithNetworkRequired(
        None,
        choices=[
            ("all", "All mobile networks"),
            ("ee", "EE"),
            ("o2", "O2"),
            ("three", "Three"),
            ("vodafone", "Vodafone"),
        ],
        param_extensions={"hint": None, "fieldset": {"legend": {"classes": "govuk-visually-hidden"}}},
    )

    @property
    def account_type(self):
        if "all" in self.networks.data:
            providers = "-".join(BroadcastProvider.PROVIDERS)
        else:
            providers = "-".join(self.networks.data)

        return f"live-{self.broadcast_channel}-{providers}"


class ServiceBroadcastAccountForm(Form):
    account_type = StringField("Account type specifier")
    service_mode = ""
    broadcast_channel = ""
    provider_restriction = []

    def validate_account_type(self, field):
        if not field.data:
            raise ValidationError("Account type specifier cannot be empty")

        split_values = field.data.split("-")
        service_mode = split_values[0]
        channel = split_values[1]
        providers = split_values[2:]

        if service_mode not in ["live", "training"]:
            raise ValidationError("Invalid service mode")

        if channel not in ["test", "operator", "severe", "government"]:
            raise ValidationError("Invalid channel")

        for p in providers:
            if p not in ["all", "ee", "o2", "three", "vodafone"]:
                raise ValidationError("Invalid provider")

        if providers == ["all"]:
            providers = ["ee", "o2", "three", "vodafone"]

        self.service_mode = service_mode
        self.broadcast_channel = channel
        self.provider_restriction = providers


class BroadcastAreaForm(StripWhitespaceForm):
    areas = GovukCheckboxesField("Choose areas to broadcast to")

    def __init__(self, choices, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.areas.choices = choices
        self.areas.render_as_list = True
        self.areas.param_extensions = {"fieldset": {"legend": {"classes": "govuk-visually-hidden"}}}

    @classmethod
    def from_library(cls, library):
        return cls(choices=[(area.id, area.name) for area in sorted(library)])


class BroadcastAreaFormWithSelectAll(BroadcastAreaForm):
    select_all = GovukCheckboxField("Select all")

    @classmethod
    def from_library(cls, library, select_all_choice):
        instance = super().from_library(library)
        (
            instance.select_all.area_slug,
            instance.select_all.label.text,
        ) = select_all_choice
        return instance

    @property
    def selected_areas(self):
        if self.select_all.data:
            return [self.select_all.area_slug]
        return self.areas.data


class ChangeSecurityKeyNameForm(StripWhitespaceForm):
    security_key_name = GovukTextInputField(
        "Name of key",
        validators=[
            DataRequired(message="Cannot be empty"),
            MustContainAlphanumericCharacters(),
            Length(max=255, message="Name of key must be 255 characters or fewer"),
        ],
    )


class FindByUuidForm(StripWhitespaceForm):
    search = GovukSearchField(
        "Find anything by UUID",
        validators=[UUID("Enter a valid UUID")],
    )


class PlatformAdminSearch(StripWhitespaceForm):
    search = GovukSearchField(
        "Search",
        param_extensions={"hint": {"text": ("Search for users, services, and organisations by name or partial name.")}},
        validators=[DataRequired()],
    )


class PostcodeForm(StripWhitespaceForm):
    postcode = PostcodeSearchField("Postcode")
    """
    Reasoning for radius field validation limits:
    The minimum value of 100m / 0.1km was driven by MNO requirements for the most
    effective transmission to get full penetration without risk of over subscription of
    cell towers. Too small an area might be difficult for their (MNO) systems to calculate
    which cell sites and towers to use, and 38km was driven by COBR as bigger
    than a city and the max side of alerting for non country size areas.
    """
    radius = GovukDecimalField(
        "Radius",
        param_extensions={
            "classes": "govuk-input govuk-input--width-5",
            "suffix": {"text": "km"},
            "attributes": {"pattern": "^-?\\d+(\\.\\d+)?$"},
        },
        validators=[
            NumberRange(min=0.099, max=38.001, message="Enter a radius between 0.1km and 38.0km"),
            DataRequired(message="Enter a radius between 0.1km and 38.0km"),
            Only2DecimalPlaces(),
        ],
    )

    def pre_validate(self, form):
        return self.postcode.validate(form)


class LatitudeLongitudeCoordinatesForm(StripWhitespaceForm):
    """
    This form contains the input fields for creation of areas using Latitude & longitude coordinates.
    There is additional validation post-submission of the form that checks whether the coordinate lies within
    either the UK or the test polygons in Finland, and if both are false then an error is appended to the form.
    """

    first_coordinate = GovukDecimalField(
        "Latitude",
        validators=[
            InputRequired("The latitude and longitude must be within the UK"),
            Only6DecimalPlaces(),
        ],
        param_extensions={
            "classes": "govuk-input govuk-input--width-6",
            "attributes": {"pattern": "^-?\\d+(\\.\\d+)?$"},
        },
    )
    second_coordinate = GovukDecimalField(
        "Longitude",
        validators=[
            InputRequired("The latitude and longitude must be within the UK"),
            Only6DecimalPlaces(),
        ],
        param_extensions={
            "classes": "govuk-input govuk-input--width-6",
            "attributes": {"pattern": "^-?\\d+(\\.\\d+)?$"},
        },
    )
    radius = GovukDecimalField(
        "Radius",
        param_extensions={
            "classes": "govuk-input govuk-input--width-5",
            "suffix": {"text": "km"},
            "attributes": {"pattern": "^-?\\d+(\\.\\d+)?$"},
        },
        validators=[
            NumberRange(min=0.099, max=38.001, message="Enter a radius between 0.1km and 38.0km"),
            DataRequired(message="Enter a radius between 0.1km and 38.0km"),
            Only2DecimalPlaces(),
        ],
    )

    def pre_validate(self, form):
        self.first_coordinate.validate(form)
        self.second_coordinate.validate(form)
        return self.first_coordinate.validate(form) and self.second_coordinate.validate(form)


class EastingNorthingCoordinatesForm(StripWhitespaceForm):
    """
    This form contains the input fields for creation of areas using Eastings & northings.
    There is additional validation post-submission of the form that checks whether the coordinate lies within
    either the UK or the test polygons in Finland, and if both are false then an error is appended to the form.
    """

    first_coordinate = GovukDecimalField(
        "Eastings",
        param_extensions={
            "classes": "govuk-input govuk-input--width-6",
            "attributes": {"pattern": "^-?\\d+(\\.\\d+)?$"},
        },
        validators=[InputRequired("The easting and northing must be within the UK"), Only6DecimalPlaces()],
    )
    second_coordinate = GovukDecimalField(
        "Northings",
        param_extensions={
            "classes": "govuk-input govuk-input--width-6",
            "attributes": {"pattern": "^-?\\d+(\\.\\d+)?$"},
        },
        validators=[InputRequired("The easting and northing must be within the UK"), Only6DecimalPlaces()],
    )
    radius = GovukDecimalField(
        "Radius",
        param_extensions={
            "classes": "govuk-input govuk-input--width-5",
            "suffix": {"text": "km"},
            "attributes": {"pattern": "^-?\\d+(\\.\\d+)?$"},
        },
        validators=[
            NumberRange(min=0.099, max=38.001, message="Enter a radius between 0.1km and 38.0km"),
            DataRequired(message="Enter a radius between 0.1km and 38.0km"),
            Only2DecimalPlaces(),
        ],
    )

    def pre_validate(self, form):
        self.first_coordinate.validate(form)
        self.second_coordinate.validate(form)
        return self.first_coordinate.validate(form) and self.second_coordinate.validate(form)


class ChooseCoordinateTypeForm(StripWhitespaceForm):
    content = GovukRadiosField(
        "Choose coordinate type",
        choices=[
            ("latitude_longitude", "Latitude and longitude"),
            ("easting_northing", "Eastings and northings"),
        ],
        param_extensions={
            "fieldset": {
                "legend": {
                    "text": "Choose coordinate type",
                    "isPageHeading": True,
                    "classes": "govuk-fieldset__legend--l",
                }
            },
            "hint": {"text": "Select one option"},
            "items": [
                {"hint": {"text": "For example, 51.503630, -0.126770"}},
                {"hint": {"text": "For example, 530111, 179963"}},
            ],
        },
        validators=[DataRequired(message="Select which type of coordinates you'd like to use")],
    )


class RejectionReasonForm(StripWhitespaceForm):
    hint = """ Provide details of why you are rejecting the alert.
        For example, "The emergency has passed"."""

    rejection_reason = GovukTextareaField(
        validators=[DataRequired(message="Enter the reason for rejecting the alert")],
        param_extensions={"hint": {"text": hint}, "rows": 3},
    )


class ReturnForEditForm(StripWhitespaceForm):
    hint = """Provide details of why you're returning the alert to draft, including how it can be improved.
    For example, "The alert message has spelling mistakes"."""

    return_for_edit_reason = GovukTextareaField(
        validators=[DataRequired(message="Enter the reason for returning the alert for edit")],
        param_extensions={"hint": {"text": hint}, "rows": 3},
    )
