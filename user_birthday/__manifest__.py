# -*- coding: utf-8 -*-
{
    # ------------------------------------------------------------------
    # Identification
    # ------------------------------------------------------------------
    "name": "User Birthday",
    "version": "18.0.1.0.0",
    "category": "Human Resources",
    "summary": "Track and celebrate internal users' birthdays with popup "
               "notifications.",
    "description": """
User Birthday
=============

Adds a Birthday date field on internal users (res.users) and provides:

* A dedicated *Birthdays* menu with list and kanban views ordered by
  upcoming birthday.
* Smart filters (today, this week, within 30 days, missing) and group
  by birthday month.
* Computed fields: next birthday, days remaining, current age,
  is_birthday_today.
* A daily scheduled action that detects users celebrating their
  birthday today and pushes a real-time popup notification (bus) to
  every internal user, plus a chatter message on the celebrant's
  record.
* A manual *Send birthday notification now* button on the user form.

Designed and ready to be published on the Odoo Apps Store for
Odoo 18.0.
""",

    # ------------------------------------------------------------------
    # Authoring & support
    # ------------------------------------------------------------------
    "author": "TICTeams",
    "maintainer": "TICTeams",
    "maintainers": ["ticteams"],
    "company": "TICTeams",
    "website": "https://www.ticteams.com",
    "support": "info@ticteams.com",
    "license": "LGPL-3",

    # ------------------------------------------------------------------
    # Apps Store metadata
    # ------------------------------------------------------------------
    "price": 2.99,
    "currency": "USD",
    "development_status": "Production/Stable",
    "live_test_url": "",  # leave empty unless you set up a runbot demo

    # ------------------------------------------------------------------
    # Dependencies
    # ------------------------------------------------------------------
    "depends": [
        "base",
        "mail",
        "bus",
    ],
    "external_dependencies": {
        "python": [
            "dateutil",
        ],
    },

    # ------------------------------------------------------------------
    # Data files
    # ------------------------------------------------------------------
    "data": [
        "security/ir.model.access.csv",
        "data/ir_cron_data.xml",
        "views/res_users_views.xml",
        "views/user_birthday_menu.xml",
    ],

    # ------------------------------------------------------------------
    # Frontend assets
    # ------------------------------------------------------------------
    "assets": {
        "web.assets_backend": [
            "user_birthday/static/src/scss/user_birthday.scss",
        ],
    },

    # ------------------------------------------------------------------
    # Apps Store images
    #   - First image is the cover thumbnail shown on the store listing.
    #   - Following images are the screenshots displayed on the page.
    # ------------------------------------------------------------------
    "images": [
        "static/description/cover.png",
        "static/description/banner.png",
        "static/description/screenshot_1_list.png",
        "static/description/screenshot_2_notification.png",
    ],

    # ------------------------------------------------------------------
    # Installation flags
    # ------------------------------------------------------------------
    "installable": True,
    "application": True,
    "auto_install": False,
}
