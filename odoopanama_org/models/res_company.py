# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class ResCompany(models.Model):
    _inherit = 'res.company'
    _description = 'Panamanian Server'

    # ── Campos de odoopanama_org_vat ──────────────────────────────────────────
    pa_dv = fields.Char(
        string="Dígito Verificador",
        related='partner_id.pa_dv',
        readonly=False,
        store=True,
    )
    l10n_pa_corregimiento = fields.Char(
        string='Corregimiento (Texto)',
        compute='_compute_l10n_pa_corregimiento',
        store=True,
    )

    # ── Campos de odoopanama_org_server ───────────────────────────────────────
    type_env = fields.Boolean("Tipo de Ambiente", default=False)
    server_type = fields.Selection(
        [('ebi', 'EBI PAC'), ('webpos', 'WebPOS PAC')],
        string="Servidor",
        default="ebi",
    )
    url = fields.Char("Url Producción")
    url_dev = fields.Char("Url Desarrollo")
    user = fields.Char("User")
    password = fields.Char("Password")
    default_invoice_email = fields.Char(
        "Email por Defecto en Facturación",
        help="Se usará este correo cuando el cliente no tenga email registrado "
             "al momento de emitir una factura electrónica."
    )
    default_payment_method = fields.Selection(
        selection='_get_default_payment_methods',
        string="Método de Pago por Defecto",
        help="Se usará este método de pago cuando la factura no tenga ninguno "
             "seleccionado al momento de confirmar."
    )
    default_corregimiento_id = fields.Many2one(
        'l10n_pa.res.city.corregimiento',
        string="Corregimiento por Defecto",
        help="Se usará este corregimiento cuando el cliente no tenga corregimiento "
             "registrado al momento de emitir una factura electrónica."
    )
    description = fields.Text("Description")
    pe_is_sync = fields.Boolean("Es sincrono", default=True)
    l10n_pa_edi_address_type_code = fields.Char(
        string="Address Type Code",
        default="0000",
        help="Code of the establishment that PAC has registered.",
    )

    # ── Métodos de odoopanama_org_vat ─────────────────────────────────────────
    @api.depends('partner_id.l10n_pa_corregimiento')
    def _compute_l10n_pa_corregimiento(self):
        for company in self:
            company.l10n_pa_corregimiento = (
                company.partner_id.l10n_pa_corregimiento.name
                if company.partner_id.l10n_pa_corregimiento
                else ''
            )

    # ── Métodos de odoopanama_org_server ──────────────────────────────────────
    def _get_default_payment_methods(self):
        return self.env['account.move']._get_payment_methods()

    @api.onchange("type_env")
    def _onchange_type_evn(self):
        if self.type_env:
            if not self.user:
                self.type_env = False
                raise UserError(
                    'Debe configurar el usuario y contraseña para pasar a Producción.')

    # ── Métodos de odoopanama_org_cpe ─────────────────────────────────────────
    def get_pac_signature(self):
        return ""

    # ── Métodos de odoopanama_org_pos ─────────────────────────────────────────
    @api.model
    def _load_pos_data_fields(self, config_id):
        result_fields = super(ResCompany, self)._load_pos_data_fields(config_id)
        result_fields.append('l10n_pa_corregimiento')
        result_fields.append('pa_dv')
        return result_fields

    @api.model
    def _load_pos_data(self, data):
        result = super()._load_pos_data(data)
        if isinstance(result, dict) and 'data' in result:
            for company_data in result['data']:
                company = self.browse(company_data['id'])
                signature = company.get_pac_signature()
                company_data['pac_signature'] = signature
        return result
