# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class AccountJournal(models.Model):
    _inherit = "account.journal"

    credit_note_id = fields.Many2one(
        comodel_name="account.journal", string="Nota de credito", domain="[('type','in', ['sale', 'purchase'])]")
    dedit_note_id = fields.Many2one(
        comodel_name="account.journal", string="Nota de debito", domain="[('type','in', ['sale', 'purchase'])]")
    l10n_latam_document_type_id = fields.Many2one(
        comodel_name="l10n_latam.document.type",  string="Tipo de CPE")
