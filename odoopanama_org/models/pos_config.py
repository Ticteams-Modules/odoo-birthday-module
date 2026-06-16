# -*- coding: utf-8 -*-

from odoo import fields, models


class PosConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    l10n_pa_edi_send_invoice = fields.Boolean(
        string='Electronic Invoicing',
        related='pos_config_id.l10n_pa_edi_send_invoice',
        readonly=False
    )
    invoice_journal_ids = fields.Many2many(
        'account.journal',
        string='Accounting Invoice Journal',
        related='pos_config_id.invoice_journal_ids',
        readonly=False
    )
    auto_select_journal = fields.Boolean(
        string="Auto-select Journal",
        related='pos_config_id.auto_select_journal',
        readonly=False
    )
    auto_go_to_payment_on_refund = fields.Boolean(
        string='Ir directamente a pago en reembolsos',
        related='pos_config_id.auto_go_to_payment_on_refund',
        readonly=False
    )



class PosConfig(models.Model):
    _inherit = "pos.config"

    l10n_pa_edi_send_invoice = fields.Boolean(string='Electronic Invoicing')
    invoice_journal_ids = fields.Many2many(
        'account.journal',
        'pos_config_invoice_journal_rel',
        'config_id',
        'journal_id',
        string='Accounting Invoice Journal',
        help="Invoice journals for Electronic invoices."
    )
    default_partner_id = fields.Many2one(
        "res.partner",
        string="Client by default",
        help="This client will be set by default in the order"
    )
    auto_select_journal = fields.Boolean(
        string="Auto-select Journal",
        default=False,
        help="Selecciona automáticamente el primer diario disponible."
    )
    auto_go_to_payment_on_refund = fields.Boolean(
        string="Ir directamente a pago en reembolsos",
        default=False,
        help="Si está marcado, los reembolsos irán directamente a la pantalla de pago."
    )
