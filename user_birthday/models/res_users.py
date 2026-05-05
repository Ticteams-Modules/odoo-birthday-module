# -*- coding: utf-8 -*-
from datetime import date

from dateutil.relativedelta import relativedelta

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class ResUsers(models.Model):
    _inherit = "res.users"

    birthday = fields.Date(
        string="Birthday",
        tracking=True,
        help="Birth date of the user. Used to compute upcoming birthday "
             "reminders and to send notifications on the celebration day.",
    )
    birthday_day = fields.Integer(
        string="Birth Day",
        compute="_compute_birthday_parts",
        store=True,
        help="Day of the month of the user's birthday (1-31).",
    )
    birthday_month = fields.Integer(
        string="Birth Month",
        compute="_compute_birthday_parts",
        store=True,
        help="Month of the user's birthday (1-12).",
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
        help="Current age of the user.",
    )
    is_birthday_today = fields.Boolean(
        string="Birthday Today",
        compute="_compute_birthday_parts",
        store=True,
        help="True when the user's birthday matches today.",
    )

    # ------------------------------------------------------------------
    # Make the new field available through web self-service / signup
    # ------------------------------------------------------------------
    @property
    def SELF_READABLE_FIELDS(self):
        return super().SELF_READABLE_FIELDS + ["birthday", "next_birthday",
                                               "days_to_birthday", "age",
                                               "is_birthday_today",
                                               "birthday_day",
                                               "birthday_month"]

    @property
    def SELF_WRITEABLE_FIELDS(self):
        return super().SELF_WRITEABLE_FIELDS + ["birthday"]

    # ------------------------------------------------------------------
    # Compute
    # ------------------------------------------------------------------
    @api.depends("birthday")
    def _compute_birthday_parts(self):
        today = fields.Date.context_today(self)
        for user in self:
            bday = user.birthday
            if not bday:
                user.birthday_day = 0
                user.birthday_month = 0
                user.next_birthday = False
                user.days_to_birthday = 0
                user.age = 0
                user.is_birthday_today = False
                continue

            user.birthday_day = bday.day
            user.birthday_month = bday.month

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

            user.next_birthday = next_bday
            user.days_to_birthday = (next_bday - today).days
            user.is_birthday_today = (
                bday.day == today.day and bday.month == today.month
            )
            user.age = relativedelta(today, bday).years

    # ------------------------------------------------------------------
    # Constraints
    # ------------------------------------------------------------------
    @api.constrains("birthday")
    def _check_birthday(self):
        today = fields.Date.context_today(self)
        for user in self:
            if user.birthday and user.birthday > today:
                raise ValidationError(
                    _("The birthday cannot be set in the future "
                      "(user: %s).") % user.name
                )

    # ------------------------------------------------------------------
    # Cron / notification logic
    # ------------------------------------------------------------------
    @api.model
    def _cron_send_birthday_notifications(self):
        """Scheduled action: detect users whose birthday is today and push a
        real-time popup notification (bus) to every active internal user.

        Also writes a chatter message on the celebrant's user record.
        """
        today = fields.Date.context_today(self)
        celebrants = self.search([
            ("birthday_day", "=", today.day),
            ("birthday_month", "=", today.month),
            ("active", "=", True),
            ("share", "=", False),
        ])

        if not celebrants:
            return True

        # Recipients: every active internal user
        recipients = self.search([
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
            for recipient in recipients:
                self.env["bus.bus"]._sendone(
                    recipient.partner_id,
                    "simple_notification",
                    payload,
                )
        return True

    # ------------------------------------------------------------------
    # Manual action (button on form)
    # ------------------------------------------------------------------
    def action_send_birthday_notification(self):
        """Manual trigger: send a popup birthday notification for the
        currently selected user(s), regardless of the date."""
        self.ensure_one()
        recipients = self.search([
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
        for recipient in recipients:
            self.env["bus.bus"]._sendone(
                recipient.partner_id,
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
