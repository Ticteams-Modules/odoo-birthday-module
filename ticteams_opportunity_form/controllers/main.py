# -*- coding: utf-8 -*-
import re

from odoo import fields, http
from odoo.http import request

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class OdooDiagnosisController(http.Controller):

    # ------------------------------------------------------------------
    # Standalone page
    # ------------------------------------------------------------------
    @http.route(
        ["/odoo-diagnosis"],
        type="http",
        auth="public",
        website=False,
        csrf=False,
        sitemap=False,
    )
    def odoo_diagnosis_page(self, **kw):
        """Render the standalone multi-step diagnosis form.

        Prospect data may be pre-filled through URL parameters carried from
        WhatsApp, e.g.::

            /odoo-diagnosis?name=John%20Doe&email=john@acme.com&phone=+507...
        """
        prefill = {
            "name": (kw.get("name") or "").strip(),
            "email": (kw.get("email") or "").strip(),
            "phone": (kw.get("phone") or "").strip(),
            "company": (kw.get("company") or "").strip(),
        }
        return request.render(
            "ticteams_opportunity_form.diagnosis_page",
            {"prefill": prefill},
        )

    # ------------------------------------------------------------------
    # Submission endpoint (called via fetch from the page)
    # ------------------------------------------------------------------
    @http.route(
        ["/odoo-diagnosis/submit"],
        type="json",
        auth="public",
        website=False,
        csrf=False,
    )
    def odoo_diagnosis_submit(self, contact=None, answers=None, hp_field=None, **kw):
        # For type="json" routes Odoo passes the JSON-RPC "params" dict directly
        # as keyword arguments to this method.
        contact = contact or {}
        answers = answers or {}

        # --- Basic anti-spam / validation ------------------------------
        # Honeypot: real users never fill this hidden field.
        if (hp_field or "").strip():
            return {"success": True}  # silently ignore bots

        name = (contact.get("name") or "").strip()
        email = (contact.get("email") or "").strip()
        phone = (contact.get("phone") or "").strip()
        company = (contact.get("company") or "").strip()

        if not name:
            return {"success": False, "error": "missing_name"}
        if not email or not EMAIL_RE.match(email):
            return {"success": False, "error": "invalid_email"}

        Lead = request.env["crm.lead"].sudo()

        vals = Lead._diag_sanitize_answers(answers)
        vals.update({
            "name": "Diagnóstico Odoo - %s%s" % (
                name, (" (%s)" % company) if company else ""
            ),
            "type": "opportunity",
            "contact_name": name,
            "email_from": email,
            "phone": phone,
            "partner_name": company or False,
            "x_diag_is_form": True,
            "x_diag_submitted_on": fields.Datetime.now(),
        })

        # Description: surface the main problem at the top of the lead.
        main_problem = vals.get("x_diag_main_problem")
        if main_problem:
            vals["description"] = main_problem

        # Contact handling:
        #   * If a contact with this email already exists, reuse it.
        #   * Otherwise always create a new res.partner and link it.
        Partner = request.env["res.partner"].sudo()
        partner = Partner.search([("email", "=ilike", email)], limit=1)
        if not partner:
            partner = Partner.create({
                "name": name,
                "email": email,
                "phone": phone or False,
                "company_name": company or False,
                "company_type": "person",
            })
        vals["partner_id"] = partner.id

        lead = Lead.create(vals)

        # Readable summary in the chatter for the sales team.
        summary = lead._diag_build_summary()
        if summary:
            lead.message_post(body=summary)

        return {"success": True, "lead_id": lead.id}
