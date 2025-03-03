import re
import unicodedata
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from functools import lru_cache
from math import floor, log10
from numbers import Number

import humanize
from emergency_alerts_utils.field import Field
from emergency_alerts_utils.formatters import make_quotes_smart
from emergency_alerts_utils.formatters import nl2br as utils_nl2br
from emergency_alerts_utils.take import Take
from emergency_alerts_utils.timezones import utc_string_to_aware_gmt_datetime
from emergency_alerts_utils.validation import InvalidPhoneError, validate_phone_number
from markupsafe import Markup


def convert_to_boolean(value):
    if isinstance(value, str):
        if value.lower() in ["t", "true", "on", "yes", "1"]:
            return True
        elif value.lower() in ["f", "false", "off", "no", "0"]:
            return False

    return value


def format_datetime(date):
    return "{} at {}".format(format_date(date), format_time(date))


def format_datetime_24h(date):
    return "{} at {}".format(
        format_date(date),
        format_time_24h(date),
    )


def format_datetime_normal(date):
    return "{} at {}".format(format_date_normal(date), format_time(date))


def format_datetime_short(date):
    return "{} at {}".format(format_date_short(date), format_time(date))


def format_datetime_relative(date):
    return "{} at {}".format(get_human_day(date), format_time(date))


def format_datetime_numeric(date):
    return "{} {}".format(
        format_date_numeric(date),
        format_time_24h(date),
    )


def format_date_numeric(date):
    return utc_string_to_aware_gmt_datetime(date).strftime("%Y-%m-%d")


def format_time_24h(date):
    return utc_string_to_aware_gmt_datetime(date).strftime("%H:%M")


def format_seconds_duration_as_time(seconds):
    seconds = int(seconds or 0)
    days = seconds // (24 * 3600)
    seconds %= 24 * 3600
    hours = seconds // 3600
    seconds %= 3600
    minutes = seconds // 60
    seconds %= 60

    time_parts = []
    if days > 0:
        time_parts.append(f"{days} {'day' if days == 1 else 'days'}")
    if hours > 0:
        time_parts.append(f"{hours} {'hour' if hours == 1 else 'hours'}")
    if minutes > 0:
        time_parts.append(f"{minutes} {'minute' if minutes == 1 else 'minutes'}")
    if seconds > 0:
        time_parts.append(f"{seconds} {'second' if seconds == 1 else 'seconds'}")

    if not time_parts:
        return "0 seconds"
    elif len(time_parts) == 1:
        return time_parts[0]
    else:
        return ", ".join(time_parts)


def parse_seconds_as_hours_and_minutes(seconds):
    seconds = int(seconds or 0)
    seconds %= 24 * 3600
    hours = seconds // 3600
    seconds %= 3600
    minutes = seconds // 60
    return (hours, minutes)


def get_human_day(time, date_prefix=""):
    #  Add 1 minute to transform 00:00 into ‘midnight today’ instead of ‘midnight tomorrow’
    date = (utc_string_to_aware_gmt_datetime(time) - timedelta(minutes=1)).date()
    now = datetime.utcnow()

    if date == (now + timedelta(days=1)).date():
        return "tomorrow"
    if date == now.date():
        return "today"
    if date == (now - timedelta(days=1)).date():
        return "yesterday"
    if date.strftime("%Y") != now.strftime("%Y"):
        return "{} {} {}".format(
            date_prefix,
            _format_datetime_short(date),
            date.strftime("%Y"),
        ).strip()
    return "{} {}".format(
        date_prefix,
        _format_datetime_short(date),
    ).strip()


def format_time(date):
    return (
        {"12:00AM": "Midnight", "12:00PM": "Midday"}
        .get(
            utc_string_to_aware_gmt_datetime(date).strftime("%-I:%M%p"),
            utc_string_to_aware_gmt_datetime(date).strftime("%-I:%M%p"),
        )
        .lower()
    )


def format_date(date):
    return utc_string_to_aware_gmt_datetime(date).strftime("%A %d %B %Y")


def format_date_normal(date):
    return utc_string_to_aware_gmt_datetime(date).strftime("%d %B %Y").lstrip("0")


def format_date_short(date):
    return _format_datetime_short(utc_string_to_aware_gmt_datetime(date))


def format_date_human(date):
    return get_human_day(date)


def format_datetime_human(date, date_prefix=""):
    return "{} at {}".format(
        get_human_day(date, date_prefix="on"),
        format_time(date),
    )


def format_day_of_week(date):
    return utc_string_to_aware_gmt_datetime(date).strftime("%A")


def _format_datetime_short(datetime):
    return datetime.strftime("%d %B").lstrip("0")


def naturaltime_without_indefinite_article(date):
    return re.sub(
        "an? (.*) ago",
        lambda match: "1 {} ago".format(match.group(1)),
        humanize.naturaltime(date),
    )


def format_delta(date):
    delta = (datetime.now(timezone.utc)) - (utc_string_to_aware_gmt_datetime(date))
    if delta < timedelta(seconds=30):
        return "just now"
    if delta < timedelta(seconds=60):
        return "in the last minute"
    return naturaltime_without_indefinite_article(delta)


def format_delta_days(date):
    now = datetime.now(timezone.utc)
    date = utc_string_to_aware_gmt_datetime(date)
    if date.strftime("%Y-%m-%d") == now.strftime("%Y-%m-%d"):
        return "today"
    if date.strftime("%Y-%m-%d") == (now - timedelta(days=1)).strftime("%Y-%m-%d"):
        return "yesterday"
    return naturaltime_without_indefinite_article(now - date)


def valid_phone_number(phone_number):
    try:
        validate_phone_number(phone_number)
        return True
    except InvalidPhoneError:
        return False


def nl2br(value):
    if value:
        return Markup(
            Take(
                Field(
                    value,
                    html="escape",
                )
            ).then(utils_nl2br)
        )
    return ""


def format_thousands(value):
    if isinstance(value, Number):
        return "{:,.0f}".format(value)
    if value is None:
        return ""
    return value


@lru_cache(maxsize=4)
def email_safe(string, whitespace="."):
    # strips accents, diacritics etc
    string = "".join(c for c in unicodedata.normalize("NFD", string) if unicodedata.category(c) != "Mn")
    string = "".join(
        word.lower() if word.isalnum() or word == whitespace else ""
        for word in re.sub(r"\s+", whitespace, string.strip())
    )
    string = re.sub(r"\.{2,}", ".", string)
    return string.strip(".")


def id_safe(string):
    return email_safe(string, whitespace="-")


def round_to_significant_figures(value, number_of_significant_figures):
    if value == 0:
        return value
    return int(round(value, number_of_significant_figures - int(floor(log10(abs(value)))) - 1))


def redact_mobile_number(mobile_number, spacing=""):
    indices = [-4, -5, -6, -7]
    redact_character = spacing + "•" + spacing
    mobile_number_list = list(mobile_number.replace(" ", ""))
    for i in indices:
        mobile_number_list[i] = redact_character
    return "".join(mobile_number_list)


def starts_with_initial(name):
    return bool(re.match(r"^.\.", name))


def remove_middle_initial(name):
    return re.sub(r"\s+.\s+", " ", name)


def remove_digits(name):
    return "".join(c for c in name if not c.isdigit())


def normalize_spaces(name):
    return " ".join(name.split())


def guess_name_from_email_address(email_address):
    possible_name = re.split(r"[\@\+]", email_address)[0]

    if "." not in possible_name or starts_with_initial(possible_name):
        return ""

    return (
        Take(possible_name)
        .then(str.replace, ".", " ")
        .then(remove_digits)
        .then(remove_middle_initial)
        .then(str.title)
        .then(make_quotes_smart)
        .then(normalize_spaces)
    )


def message_count_label(count, template_type, suffix="sent"):
    if suffix:
        return f"{message_count_noun(count, template_type)} {suffix}"
    return message_count_noun(count, template_type)


def message_count_noun(count, template_type):
    singular = count == 1

    if template_type == "broadcast":
        return "broadcast" if singular else "broadcasts"

    return "message" if singular else "messages"


def message_count(count, template_type):
    return f"{format_thousands(count)} {message_count_noun(count, template_type)}"


def iteration_count(count):
    if count == 1:
        return "once"
    if count == 2:
        return "twice"
    return f"{count} times"


def character_count(count):
    if count == 1:
        return "1 character"
    return f"{format_thousands(count)} characters"


def format_mobile_network(network):
    if network in ("three", "vodafone", "o2"):
        return network.capitalize()
    return "EE"


def format_yes_no(value, yes="Yes", no="No", none="No"):
    if value is None:
        return none
    return yes if value else no


def square_metres_to_square_miles(area):
    return area * 3.86e-7


def format_auth_type(auth_type, with_indefinite_article=False):
    indefinite_article, auth_type = {
        "email_auth": ("an", "Email link"),
        "sms_auth": ("a", "Text message code"),
        "webauthn_auth": ("a", "Security key"),
    }[auth_type]

    if with_indefinite_article:
        return f"{indefinite_article} {auth_type.lower()}"

    return auth_type


def format_number_no_scientific(num):
    """
    Returns a string of the number similar to ':g' formatting (e.g. no trailing zeroes), but this will *not* be in
    scientific notation after the number reaches a certain threshold.
    """
    dec = Decimal(str(num))
    # Ensure whole numbers with trailing zeroes are not normlaized to exponent format
    # See https://docs.python.org/3.9/library/decimal.html#decimal-faq
    normalised = dec.quantize(Decimal(1)) if dec == dec.to_integral() else dec.normalize()

    return str(normalised)
