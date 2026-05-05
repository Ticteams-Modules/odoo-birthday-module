# -*- coding: utf-8 -*-
from datetime import date

from dateutil.relativedelta import relativedelta

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class ResPartner(models.Model):
    _inherit = "res.partner"

    birthday = fields.Date(
        string="Birthday",
        tracking=True,
        help="Birth date of the contact. Used to compute upcoming birthday "
             "reminders and to send notifications on the celebration day.",
    )
    birthday_day = fields.Integer(
        string="Birth Day",
        compute="_compute_birthday_parts",
        store=True,
        help="Day of the month of the contact's birthday (1-31).",
    )
    birthday_month = fields.Integer(
        string="Birth Month",
        compute="_compute_birthday_parts",
        store=True,
        help="Month of the contact's birthday (1-12).",
    )
    next_birthday = fields.Date(
        string="Next Birthday",
        compute="_compute_birthday_parts",
        store=True,
        help="Next upcoming birthday date (automatically rolled to next year "
             "after the birthday has passed).",
    )
    days_to_birthday = fields.Integer(
        string="Days Until Birthday",
        compute="_compute_birthday_parts",
        store=True,
        help="Number of days remaining until the next birthday.",
    )
    age = fields.Integer(
        string="Age",
        compute="_compute_birthday_parts",
        store=True,
        help="Current age of the contact.",
    )
    is_birthday_today = fields.Boolean(
        string="Birthday Today",
        compute="_compute_birthday_parts",
        store=True,
        help="True when the contact's birthday matches today.",
    )

    # ------------------------------------------------------------------
    # Compute
    # ------------------------------------------------------------------
    @api.depends("birthday")
    def _compute_birthday_parts(self):
        today = fields.Date.context_today(self)
        for partner in self:
            bday = partner.birthday
            if not bday:
                partner.birthday_day = 0
                partner.birthday_month = 0
                partner.next_birthday = False
                partner.days_to_birthday = 0
                partner.age = 0
                partner.is_birthday_today = False
                continue

            partner.birthday_day = bday.day
            partner.birthday_month = bday.month

            try:
                this_year_bday = bday.replace(year=today.year)
            except ValueError:
                # Feb 29 on a non-leap year -> celebrate on Feb 28
                this_year_bday = date(today.year, 2, 28)

            if this_year_bday < today:
                try:
                    next_bday = bday.replace(year=today.year + 1)
                except ValueError:
                    next_bday = date(today.year + 1, 2, 28)
            else:
                next_bday = this_year_bday

            partner.next_birthday = next_bday
            partner.days_to_birthday = (next_bday - today).days
            partner.is_birthday_today = (
                bday.day == today.day and bday.month == today.month
            )
            partner.age = relativedelta(today, bday).years

    # ------------------------------------------------------------------
    # Constraints
    # ------------------------------------------------------------------
    @api.constrains("birthday")
    def _check_birthday(self):
        today = fields.Date.context_today(self)
        for partner in self:
            if partner.birthday and partner.birthday > today:
                raise ValidationError(
                    _("The birthday cannot be set in the future "
                      "(contact: %s).") % partner.name
                )

    # ------------------------------------------------------------------
    # Cron / notification logic
    # ------------------------------------------------------------------
    @api.model
    def _cron_send_birthday_notifications(self):
        """Scheduled action: detect contacts whose birthday is today and push
        a real-time popup notification (bus) to every active internal user.

        Also writes a chatter message on the celebrant's partner record.
        """
        today = fields.Date.context_today(self)
        celebrants = self.search([
            ("birthday_day", "=", today.day),
            ("birthday_month", "=", today.month),
            ("active", "=", True),
            ("is_company", "=", False),
        ])

        if not celebrants:
            return True

        # Recipients: every active internal user
        internal_users = self.env["res.users"].search([
            ("active", "=", True),
            ("share", "=", False),
        ])

        for celebrant in celebrants:
            age_text = ""
            if celebrant.age:
                age_text = _(" turning %s today") % celebrant.age

            title = _("🎂 Happy Birthday!")
            message = _(
                "%(name)s is celebrating their birthday%(age)s. "
                "Don't forget to wish them well!"
            ) % {"name": celebrant.name, "age": age_text}

            # Log on the celebrant's record (chatter)
            celebrant.message_post(
                body=_("%(name)s is celebrating their birthday today%(age)s. 🎉")
                % {"name": celebrant.name, "age": age_text},
                subject=_("Happy Birthday!"),
                message_type="notification",
            )

            # Real-time popup (bus) to every internal user
            payload = {
                "type": "success",
                "title": title,
                "message": message,
                "sticky": True,
            }
            for user in internal_users:
                self.env["bus.bus"]._sendone(
                    user.partner_id,
                    "simple_notification",
                    payload,
                )
        return True

    # ------------------------------------------------------------------
    # Manual action (button on form)
    # ------------------------------------------------------------------
    def action_send_birthday_notification(self):
        """Manual trigger: send a popup birthday notification for the
        currently selected contact, regardless of the date."""
        self.ensure_one()
        internal_users = self.env["res.users"].search([
            ("active", "=", True),
            ("share", "=", False),
        ])
        payload = {
            "type": "success",
            "title": _("🎂 Happy Birthday!"),
            "message": _(
                "%s is celebrating their birthday. Don't forget to wish "
                "them well!"
            ) % self.name,
            "sticky": True,
        }
        for user in internal_users:
            self.env["bus.bus"]._sendone(
                user.partner_id,
                "simple_notification",
                payload,
            )
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Notification sent"),
                "message": _("Birthday notification pushed to all internal "
                             "users."),
                "type": "success",
                "sticky": False,
            },
        }
