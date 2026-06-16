# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from collections import defaultdict
from odoo.exceptions import ValidationError, UserError


class PosOrder(models.Model):
    _inherit = "pos.order"

    invoice_journal_id = fields.Many2one(
        'account.journal', 
        string='Journal account', 
        readonly=True,
        domain="[('type', 'in', ['sale'])]", 
        copy=True
    )
    refund_order_id = fields.Many2one('pos.order', string="POS for which this invoice is the credit")
    pa_invoice_type = fields.Selection(
        [("annul", "Annul"), ("refund", "Credit Note")], 
        "Invoice Type"
    )
    pa_motive = fields.Char("Credit Note Reference")
    pa_invoice_date = fields.Datetime("Invoice Date Time", copy=False)
    date_invoice = fields.Date("Invoice Date")
    refund_invoice_id = fields.Many2one('account.move', string="Invoice for which this invoice is the credit")

    l10n_pa_edi_refund_reason = fields.Selection(
        selection=[
            ('01', 'Anulación de la operación'),
            ('02', 'Anulación por error en el RUC'),
            ('03', 'Corrección por error en la descripción'),
            ('04', 'Descuento global'),
            ('05', 'Descuento por ítem'),
            ('06', 'Devolución total'),
            ('07', 'Devolución por ítem'),
            ('08', 'Bonificación'),
            ('09', 'Disminución en el valor'),
            ('10', 'Otros Conceptos'),
            ('11', 'Ajustes de operaciones de exportación'),
            ('12', 'Ajustes afectos al IVAP'),
            ('13', 'Ajustes – montos y/o fechas de pago'),
        ],
        string="Credit Note Code",
        help='Contains all possible values for the credit note reason Catalog No. 09'
    )

    number = fields.Char(string='Number', compute='_compute_number', store=True)

    @api.depends('account_move', 'refund_invoice_id')
    def _compute_number(self):
        for order in self:
            order.number = order.account_move.name or order.refund_invoice_id.name or False

    def refund(self):
        res = super().refund()
        order_id = res.get("res_id")
        if not order_id:
            return res

        order = self.env['pos.order'].browse(order_id)
        if not self.account_move:
            raise ValidationError(_("The current order does not have an associated accounting move."))

        pa_invoice_type = self.env.context.get("default_pa_invoice_type", False)
        
        values_to_write = {
            'refund_order_id': self.id,
            'refund_invoice_id': self.account_move.id,
            'pa_invoice_type': pa_invoice_type,
            'invoice_journal_id': self._get_invoice_journal_id(order, pa_invoice_type),
        }
        order.write(values_to_write)
        return res

    def _get_invoice_journal_id(self, order, pa_invoice_type):
        if pa_invoice_type == 'annul':
            return self.account_move.journal_id.id or False
        return self.invoice_journal_id.credit_note_id.id if self.invoice_journal_id.credit_note_id else self.invoice_journal_id.id

    def _prepare_invoice_vals(self):
        values = super()._prepare_invoice_vals()
        if self.config_id.l10n_pa_edi_send_invoice and self.invoice_journal_id:
            values['journal_id'] = self.invoice_journal_id.id

        origin_move_id = self.refund_invoice_id
        if origin_move_id and origin_move_id.l10n_latam_document_type_id:
            values.update({
                'reversed_entry_id': origin_move_id.id,
                'origin_l10n_latam_document_type_id': origin_move_id.l10n_latam_document_type_id.id,
                'origin_number': origin_move_id.name.replace(' ', '') if origin_move_id.name else False,
                'origin_invoice_date': origin_move_id.invoice_date,
            })

        return values

    @api.model
    def _order_fields(self, ui_order):
        order_fields = super()._order_fields(ui_order)
        if ui_order.get('invoice_journal_id'):
            order_fields['invoice_journal_id'] = ui_order['invoice_journal_id']
        return order_fields

    @api.model
    def _process_order(self, order, existing_order):
        """Configura campos de reembolso cuando se recibe original_move_id del frontend."""
        original_move_id = order.pop("original_move_id", None)

        if original_move_id:
            original_move = self.env["account.move"].browse(original_move_id)
            if original_move.exists():
                order["refund_invoice_id"] = original_move_id
                order["pa_invoice_type"] = 'annul'

                journal = original_move.journal_id
                if journal.credit_note_id:
                    order["invoice_journal_id"] = journal.credit_note_id.id
                else:
                    order["invoice_journal_id"] = journal.id

        return super()._process_order(order, existing_order)

    @api.model
    def invoice_data(self, order):
        """
        Obtiene los datos de facturación electrónica para mostrar en el POS

        Args:
            order (str): Referencia de la orden POS (pos_reference)

        Returns:
            dict: Datos de la factura electrónica o False si no existe
        """
        pos_order = self.env['pos.order'].sudo().search([('pos_reference', '=', order)], limit=1)
        if not pos_order or not pos_order.account_move:
            return False

        account_move = pos_order.account_move
        company = pos_order.company_id

        data = {
            'invoice_number': (account_move.name).split("-")[-1] if account_move.name else '',
            'billing_point': (account_move.name).split("-")[0][1:] if account_move.name else '',
            'type_of_invoice_document': account_move.l10n_latam_document_type_id.report_name.upper() if account_move.l10n_latam_document_type_id else '',
            'is_cpe': account_move.journal_id.is_cpe if account_move.journal_id else False,
            'amount_in_words': account_move.currency_id.amount_to_text(account_move.amount_total) if account_move.currency_id else '',
            'currency_name': account_move.currency_id.currency_unit_label or account_move.currency_id.name if account_move.currency_id else '',
            'control_url': company.website or 'http://odoopanama.org',
            'date_invoice': account_move.invoice_date,
            'invoice_date_due': account_move.invoice_date_due,
            'cufe': account_move.pa_edocument_id.cufe if account_move.pa_edocument_id else '',
            'qrcontent': account_move.pa_edocument_id.qrcontent if account_move.pa_edocument_id and account_move.pa_edocument_id.qrcontent else '',
            'authorization_protocol': account_move.pa_edocument_id.authorization_protocol if account_move.pa_edocument_id else '',
            'env': company.type_env if hasattr(company, 'type_env') else False,
        }

        return data


    def _create_invoice(self, move_vals):
        invoice = super()._create_invoice(move_vals)

        for order in self:
            payments = order.payment_ids

            if not payments and order.amount_total == 0:
                cash_method = order.session_id.config_id.payment_method_ids.filtered(
                    lambda pm: pm.type == 'cash'
                )
                if not cash_method:
                    cash_method = order.session_id.config_id.payment_method_ids[:1]

                if cash_method:
                    payment_vals = {
                        'pos_order_id': order.id,
                        'payment_method_id': cash_method.id,
                        'amount': 0.0,
                        'session_id': order.session_id.id,
                    }
                    self.env['pos.payment'].create(payment_vals)
                    payments = order.payment_ids
                else:
                    continue

            if not payments:
                continue

            payment_date_model = self.env['pa.payment.date']
            payment_records = []

            payments_by_method = defaultdict(float)
            for payment in payments:
                journal = payment.payment_method_id.journal_id
                payment_method_code = journal.pa_payment_method if journal else False

                if payment_method_code:
                    payments_by_method[payment_method_code] += payment.amount

            remaining_amount = order.amount_total
            for method, total_payment in payments_by_method.items():
                if remaining_amount >= 0:
                    amount_to_register = min(remaining_amount, total_payment)
                else:
                    amount_to_register = max(remaining_amount, total_payment)

                payment_data = {
                    'amount': amount_to_register,
                    'date': order.date_order.date(),
                    'move_id': invoice.id,
                    'pa_payment_method': method,
                }
                payment_records.append(payment_data)
                remaining_amount -= amount_to_register

            if payment_records:
                payment_date_model.create(payment_records)

        return invoice

    
    def _generate_pos_order_invoice(self):
        moves = self.env['account.move']

        for order in self:
            if order.account_move:
                moves += order.account_move
                continue

            if not order.partner_id:
                raise UserError(_('Please provide a partner for the sale.'))

            move_vals = order._prepare_invoice_vals()
            new_move = order._create_invoice(move_vals)

            order.write({'account_move': new_move.id, 'state': 'invoiced'})
            new_move.sudo().with_company(order.company_id).with_context(skip_invoice_sync=True)._post()

            moves += new_move
            payment_moves = order._apply_invoice_payments(order.session_id.state == 'closed')

            if order.session_id.state == 'closed':
                order._create_misc_reversal_move(payment_moves)

        if not moves:
            return {}

        return {
            'name': _('Customer Invoice'),
            'view_mode': 'form',
            'view_id': self.env.ref('account.view_move_form').id,
            'res_model': 'account.move',
            'context': "{'move_type':'out_invoice'}",
            'type': 'ir.actions.act_window',
            'nodestroy': True,
            'target': 'current',
            'res_id': moves and moves.ids[0] or False,
        }
