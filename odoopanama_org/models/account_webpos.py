# -*- coding: utf-8 -*-

from odoo import api, models, _
import logging

log = logging.getLogger(__name__)

payment_methods = [
            ('01', 'Efectivo'),
            ('02', 'Tarjeta crédito'),
            ('03', 'Tarjeta débito'),
            ('04', 'Cheque'),
            ('05', 'Otro'),
            ('06', 'Giftcard'),
            ('07', 'Nota de crédito'),
            ('08', 'Crédito'),
            ('09', 'Otro'),
        ]

class AccountMove(models.Model):
    _inherit = 'account.move'

    # ------------------------------------------------------------------
    # Lógica de retención / exención de ITBMS
    # ------------------------------------------------------------------

    def _apply_retention_taxes(self):
        """Agrega automáticamente el impuesto de retención o exención de ITBMS
        a todas las líneas de producto de la factura, según el tipo de retención
        configurado en el cliente (pa_retention_type).

        - '50'     → busca los impuestos marcados con pa_is_retention_tax
        - 'exento' → busca los impuestos marcados con pa_is_exemption_tax
        - 'normal' → no hace nada
        """
        self.ensure_one()

        if self.move_type not in ('out_invoice', 'out_refund'):
            return

        partner = self.partner_id
        if not partner:
            return

        retention_type = partner.pa_retention_type or 'normal'
        if retention_type == 'normal':
            return

        if retention_type == '50':
            retention_taxes = self.env['account.tax'].search([
                ('pa_is_retention_tax', '=', True),
                ('company_id', '=', self.company_id.id),
                ('type_tax_use', 'in', ('sale', 'all')),
            ])
            label = "retención 50%"
        elif retention_type == 'exento':
            retention_taxes = self.env['account.tax'].search([
                ('pa_is_exemption_tax', '=', True),
                ('company_id', '=', self.company_id.id),
                ('type_tax_use', 'in', ('sale', 'all')),
            ])
            label = "exención"
        else:
            return

        if not retention_taxes:
            log.warning(
                "[_apply_retention_taxes] No se encontró ningún impuesto de %s "
                "configurado para la empresa %s. Verifique la configuración de impuestos.",
                label, self.company_id.name
            )
            return

        product_lines = self.invoice_line_ids.filtered(
            lambda l: l.display_type == 'product'
        )
        for line in product_lines:
            new_taxes = retention_taxes.filtered(lambda t: t not in line.tax_ids)
            if new_taxes:
                line.tax_ids = line.tax_ids + new_taxes
                log.info(
                    "[_apply_retention_taxes] Impuesto(s) de %s agregado(s) "
                    "a la línea '%s' (factura: %s, cliente: %s).",
                    label, line.name or line.product_id.name,
                    self.name, partner.name
                )

    @api.model_create_multi
    def create(self, vals_list):
        """Aplica impuestos de retención al crear facturas desde pedidos de venta
        (o cualquier creación programática donde onchange no se dispara).
        """
        moves = super().create(vals_list)
        for move in moves:
            if move.move_type in ('out_invoice', 'out_refund') and move.state == 'draft':
                move._apply_retention_taxes()
        return moves

    @api.onchange('partner_id', 'company_id')
    def _onchange_partner_retention(self):
        """Aplica impuestos de retención al cambiar el cliente en la factura."""
        if self.move_type in ('out_invoice', 'out_refund'):
            self._apply_retention_taxes()

    def _post(self, soft=True):
        """Aplica impuestos de retención/exención antes de confirmar la factura
        (segunda garantía por si la factura fue modificada manualmente).
        """
        for invoice_id in self:
            if (invoice_id.move_type in ('out_invoice', 'out_refund')
                    and invoice_id.state == 'draft'):
                invoice_id._apply_retention_taxes()
        return super(AccountMove, self)._post(soft=soft)

    @api.model
    def _get_payment_methods(self):
        return payment_methods


class AccountJournal(models.Model):
    _inherit = "account.journal"

    def _get_payment_methods(self):
        return payment_methods


class PaPaymentDate(models.Model):
    _inherit = "pa.payment.date"

    def _get_payment_methods(self):
        return payment_methods

