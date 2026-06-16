# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class AccountJournal(models.Model):
    _inherit = "account.journal"

    is_cpe = fields.Boolean("Es un CPE")
    is_synchronous = fields.Boolean("Es sincrono")
    pa_payment_method = fields.Selection(
        selection='_get_payment_methods',
        string='Método de pago para DGI',
        help='Método de pago para envio de FE-DGI')
    
    def _get_payment_methods(self):
        return []
