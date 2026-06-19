# -*- coding: utf-8 -*-
{
    "name": "Opportunity Diagnosis Form",
    "version": "18.0.1.0.0",
    "category": "Sales/CRM",
    "summary": "Standalone multi-step Odoo diagnosis form that creates a "
               "CRM opportunity with the prospect's answers.",
    "description": """
Opportunity Diagnosis Form
==========================

Public, standalone web form (typeform-style) that lets a prospect describe
the Odoo project they need. It is meant to be shared from WhatsApp through a
link that carries the prospect's name, email and phone as URL parameters::

    /odoo-diagnosis?name=John%20Doe&email=john@acme.com&phone=+50760000000

The visitor answers ~12 Odoo-focused steps (industry, company size, current
system, modules to configure, custom development, accounting / e-invoicing
status, POS, inventory, integrations, timeline, budget, main problem) and a
final contact step. On submit, a ``crm.lead`` opportunity is created with all
the answers stored in structured fields and shown on a dedicated
**Odoo Diagnosis** page of the opportunity form.

Branded with the TicTeams primary color rgb(12, 118, 121).
""",

    "author": "TICTeams",
    "maintainer": "TICTeams",
    "maintainers": ["ticteams"],
    "company": "TICTeams",
    "website": "https://www.ticteams.com",
    "support": "info@ticteams.com",
    "license": "LGPL-3",

    "depends": [
        "crm",
        "web",
    ],

    "data": [
        "views/diagnosis_report.xml",
        "views/crm_lead_views.xml",
        "views/diagnosis_templates.xml",
    ],

    # The standalone page is self-contained: it loads its own CSS/JS directly
    # (see views/diagnosis_templates.xml) so it stays fully branded and free of
    # Bootstrap/website conflicts. No asset bundle registration is required.

    "installable": True,
    "application": True,
    "auto_install": False,
}
