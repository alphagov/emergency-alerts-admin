def features_nav():
    return [
        {
            "name": "Features",
            "link": "main.features",
            "sub_navigation_items": [
                {
                    "name": "Emails",
                    "link": "main.features_email",
                },
                {
                    "name": "Text messages",
                    "link": "main.features_sms",
                },
                {
                    "name": "Letters",
                    "link": "main.features_letters",
                },
            ],
        },
        {
            "name": "Roadmap",
            "link": "main.roadmap",
        },
        {
            "name": "Who can use Notify",
            "link": "main.who_can_use_notify",
        },
        {
            "name": "Security",
            "link": "main.security",
        },
        {
            "name": "Terms of use",
            "link": "main.terms",
        },
    ]


def using_notify_nav():
    return [
        {
            "name": "Get started",
            "link": "main.get_started",
        },
        {
            "name": "Trial mode",
            "link": "main.trial_mode_new",
        },
        {
            "name": "Delivery status",
            "link": "main.message_status",
        },
        {
            "name": "Guidance",
            "link": "main.guidance_index",
            "sub_navigation_items": [
                {
                    "name": "Formatting",
                    "link": "main.edit_and_format_messages",
                },
                {
                    "name": "Letter specification",
                    "link": "main.letter_specification",
                },
            ],
        },
        {
            "name": "API documentation",
            "link": "main.documentation",
        },
    ]
