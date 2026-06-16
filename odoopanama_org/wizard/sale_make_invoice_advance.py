# -*- coding: utf-8 -*-
from odoo import models, _


class SaleAdvancePaymentInv(models.TransientModel):
    _inherit = "sale.advance.payment.inv"

    def create_invoices(self):
        res = super(SaleAdvancePaymentInv, self).create_invoices()
        order = self.env['sale.order'].browse(
            self._context.get('active_ids', []))
        for invoice_id in order.invoice_ids:
            invoice_id.with_context(
                force_pe_journal=True)._onchange_partner_id()
            invoice_id.invoice_payment_term_id = order.payment_term_id.id

        return res
   