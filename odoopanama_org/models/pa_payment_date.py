# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from datetime import timedelta


class PaPaymentDate(models.Model):
    _name = "pa.payment.date"
    _description = "Panama Payment Date"

    amount = fields.Float("Monto", required=True, digits=[12,3])
    date = fields.Date("Fecha", required=True)
    order_id = fields.Many2one("sale.order", "Order")
    move_id = fields.Many2one("account.move", "Invoice", required=True)
    number_quot = fields.Char(string="Line Nº", compute='_compute_number')
    pa_payment_method = fields.Selection(
        selection='_get_payment_methods',
        string='Método de pago para DGI',
        help='Método de pago para envio de FE-DGI')

    def _get_payment_methods(self):
        return []

    def _compute_number(self):
        number_quot = 1
        for move in self:
            move.number_quot = ("Pago-{}".format(str(number_quot)))
            number_quot += 1

    def get_payment_values(self):
        res = []
        for line in self:
            res.append((0, 0, {'amount': line.amount, 'date': line.date}))
        return res

    @api.model
    def get_payment_by_qty_date(self):
        date_start = self.env.context.get(
            'pa_payment_date_start') or fields.Date.context_today(self)
        date_end = self.env.context.get(
            'pa_payment_date_end') or fields.Date.context_today(self)
        qty = self.env.context.get('pa_payment_qty') or 1
        amount = self.env.context.get('pa_payment_amount') or 0
        pa_payment_method = self.env.context.get('pa_payment_method')
        amount_part = round(amount/qty, 3)
        date_vals = {}
        odate_start = fields.Date.from_string(date_start)
        odate_end = fields.Date.from_string(date_end)
        days = (odate_end - odate_start).days
        quote_part = int(round(days / qty, 0))
        for i in range(qty):
            if i != qty-1:
                odate_start = odate_start+timedelta(quote_part)
            else:
                odate_start = odate_end
            date_vals[i] = fields.Date.to_string(odate_start)
        res = []
        for i in range(qty):
            res.append((0, 0, {'pa_payment_method': pa_payment_method,
                       'amount': amount_part, 'date': date_vals[i]}))
            amount -= amount_part
            if i == qty-1:
                amount_part = amount

        return res
