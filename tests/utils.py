from unittest.mock import PropertyMock

from lxml import etree


class ComparablePropertyMock(PropertyMock):
    """A minimal extension of PropertyMock that allows it to be compared against another value"""

    def __lt__(self, other):
        return self() < other


# Differs to emergency_alerts_utils in that it takes strings
# (and we shouldn't import test code from the utils module)
def xml_path(alert_xml: str, path: str, format="cap"):
    root = etree.fromstring(alert_xml)

    if format == "cap":
        ns = {
            "cap": "urn:oasis:names:tc:emergency:cap:1.2",
            "ds": "http://www.w3.org/2000/09/xmldsig#",
        }
    else:
        ns = {
            "ibag": "ibag:1.0",
            "ds": "http://www.w3.org/2000/09/xmldsig#",
        }

    return root.xpath(path, namespaces=ns)
