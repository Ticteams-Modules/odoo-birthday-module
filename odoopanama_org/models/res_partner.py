# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError
from .library.cedula import validate as CDL
import requests
import logging

_logger = logging.getLogger(__name__)


class ResPartner(models.Model):
    _inherit = 'res.partner'

    # ── Campos de odoopanama_org_vat ──────────────────────────────────────────
    commercial_name = fields.Char("Nombre commercial", default="-")
    is_validate = fields.Boolean("Es Validado")
    l10n_pa_corregimiento = fields.Many2one(
        'l10n_pa.res.city.corregimiento', string='Corregimiento')
    pa_dv = fields.Char("Digito Verificador")
    pa_type_client = fields.Selection(
        selection=[
            ('taxpayer', 'Empresa contribuyente'),
            ('consumer', 'Consumidor Final'),
            ('foreign', 'Extranjero'),
        ],
        string="Tipo de Cliente para FE",
        store=False,
        compute='_compute_customer_type',
    )

    # ── Campos de odoopanama_org_base ─────────────────────────────────────────
    is_retainer = fields.Boolean(
        string="Is Retainer",
        help="Indicates if the partner is a retainer.",
    )
    retention_code = fields.Selection(
        [
            ('1', 'Pago por servicio profesional al estado 100%'),
            ('2', 'Pago por venta de bienes/servicios al estado 50%'),
            ('3', 'Pago o acreditación a no domiciliado o empresa constituida en el exterior 100%'),
            ('4', 'Pago o acreditación por compra de bienes/servicios 50%'),
            ('7', 'Pago a comercio afiliado a sistema de TC/TD 50%'),
            ('8', 'Otros (disminución de la retención)'),
        ],
        string="Retention Code",
        help="Specifies the type of retention for the partner.",
    )

    # ── Campos de odoopanama_org_webpos ───────────────────────────────────────
    pa_retention_type = fields.Selection(
        selection=[
            ('normal', 'Normal'),
            ('50', 'Retenedor 50%'),
            ('exento', 'Exento'),
        ],
        string="Tipo de Retención ITBMS",
        default='normal',
        help="Define si este cliente aplica retención de ITBMS:\n"
             "- Normal: paga el 7% completo de ITBMS.\n"
             "- Retenedor 50%: retiene el 50% del ITBMS (paga 3.5%) y "
             "lo declara directamente a la DGI.\n"
             "- Exento: está exento del pago de ITBMS.",
    )

    # ── Métodos de odoopanama_org_webpos (doc_codes) ──────────────────────────
    @api.model
    def get_doc_codes(self):
        return {
            'taxpayer': ['04'],
            'government': ['03'],
            'cdl': ['05'],
            'consumer': ['07'],
            'foreign': ['06'],
            'other': ['99'],
        }

    # ── Métodos de odoopanama_org_vat ─────────────────────────────────────────
    @api.depends("l10n_latam_identification_type_id")
    def _compute_customer_type(self):
        for partner in self:
            doc_type = partner.l10n_latam_identification_type_id.l10n_pa_vat_code
            doc_codes = self.get_doc_codes()
            taxpayer = doc_codes.get('taxpayer', []) + doc_codes.get('government', [])
            consumer = doc_codes.get('consumer', []) + doc_codes.get('cdl', [])
            if doc_type:
                if doc_type in taxpayer:
                    partner.pa_type_client = "taxpayer"
                elif doc_type in consumer:
                    partner.pa_type_client = "consumer"
                else:
                    partner.pa_type_client = "foreign"
            else:
                partner.pa_type_client = "consumer"

    @api.onchange('l10n_pa_corregimiento')
    def _onchange_l10n_pa_corregimiento(self):
        if self.l10n_pa_corregimiento:
            self.city_id = self.l10n_pa_corregimiento.city_id

    @api.onchange('city_id')
    def _onchange_l10n_pa_city_id(self):
        if (self.city_id and self.l10n_pa_corregimiento.city_id
                and self.l10n_pa_corregimiento.city_id != self.city_id):
            self.l10n_pa_corregimiento = False

    @api.constrains("vat")
    def check_vat(self):
        if not self.parent_id:
            for partner in self:
                doc_type = partner.l10n_latam_identification_type_id.l10n_pa_vat_code
                doc_codes = self.get_doc_codes()
                consumer = doc_codes.get('consumer', []) + doc_codes.get('other', [])
                if not doc_type and not partner.vat or doc_type in consumer:
                    continue
                elif doc_type and not partner.vat:
                    raise UserError("Enter the document number")
                if self.search_count([
                    ('company_id', '=', partner.company_id.id),
                    ('l10n_latam_identification_type_id.l10n_pa_vat_code', '=', doc_type),
                    ('vat', '=', partner.vat),
                ]) > 1:
                    raise UserError(
                        'The document number already exists and violates the unique field restriction')

    @api.model
    def get_document_types(self):
        return []

    @api.onchange("vat", "l10n_latam_identification_type_id")
    @api.depends("l10n_latam_identification_type_id", "vat")
    def _vat_change(self):
        _logger.info("Entering _vat_change method")
        if self.vat:
            vat = self.vat
            _logger.info(f"VAT present: {vat}")
            if vat and self.l10n_latam_identification_type_id:
                doc_type = self.l10n_latam_identification_type_id.l10n_pa_vat_code
                _logger.info(f"Doc Type: {doc_type}")
                doc_codes = self.get_doc_codes()
                taxpayer = doc_codes.get('taxpayer', []) + doc_codes.get('government', [])
                cdl = doc_codes.get('cdl', [])
                query_doc_codes = taxpayer + cdl

                if doc_type in query_doc_codes:
                    _logger.info(f"Doc Type {doc_type} needs validation/lookup")
                    if doc_type == cdl:
                        response = CDL(self.vat)
                        if not response['is_valid']:
                            _logger.warning(f"Invalid CDL: {self.vat}")
                            raise UserError(_('The identification number (Cédula) is incorrect.'))

                    company = self.env.company
                    api_key = company.password
                    if api_key:
                        environment = "prod" if company.type_env else "test"
                        base_url = "https://fepa-api18.webposonline.com/api/fepa/ak/v1"
                        request_url = f"{base_url}/{environment}/checkRuc/{api_key}/{vat.strip()}/0"

                        _logger.info(f"Requesting WebPOS URL: {request_url}")
                        try:
                            response_api = requests.get(request_url)
                            _logger.info(f"Response Status Code: {response_api.status_code}")
                            _logger.info(f"Response Content: {response_api.text}")

                            if response_api.status_code == 200:
                                data = response_api.json()
                                if data.get('valido'):
                                    _logger.info("API Success. Updating partner data.")
                                    self.name = data.get('razonSocial', '').strip()
                                    self.pa_dv = data.get('dv', '').strip()
                                else:
                                    _logger.warning(f"API returned valido=False: {data}")
                        except Exception as e:
                            _logger.error(f"Exception during API request: {str(e)}")

    @api.onchange("l10n_latam_identification_type_id")
    def _onchange_identification_type(self):
        for res in self:
            if res.l10n_latam_identification_type_id:
                doc_type = res.l10n_latam_identification_type_id.l10n_pa_vat_code
                doc_codes = self.get_doc_codes()
                taxpayer = doc_codes.get('taxpayer', [])
                government = doc_codes.get('government', [])
                relevant_codes = taxpayer + government

                if doc_type in relevant_codes:
                    res.company_type = 'company'
                else:
                    res.company_type = 'person'

            res.country_id = self.env.ref("base.pa").id

    def AppLink(self, doc_type):
        doc_codes = self.get_doc_codes()
        Applink = False
        LinkSudo = self.env['ir.config_parameter'].sudo()
        consulta = LinkSudo.get_param('token') or "public"
        ruc = LinkSudo.get_param('web.base.url').replace(
            'http://', '').replace('https://', '').replace('wwww', '').replace('.', '_')
        apiserver = ruc.split(':')[0]
        company = self.env.company

        env_value = "1" if company.type_env else "0"
        source_value = company.server_type
        user_value = company.user or ""
        key_value = company.password or ""

        url = 'https://api.odoopanama.org/apiv2'
        Applink = "{}?url={}&token={}&type={}&env={}&source={}&user={}&key={}&ruc=".format(
            url, apiserver, consulta, doc_type, env_value, source_value, user_value, key_value)
        return Applink

    # ── Métodos de odoopanama_org_pos ─────────────────────────────────────────
    @api.model
    def create_from_ui(self, partner):
        if partner.get('l10n_latam_identification_type_id', False):
            partner.update({
                'l10n_latam_identification_type_id': int(
                    partner.get('l10n_latam_identification_type_id'))
            })
        res = super(ResPartner, self).create_from_ui(partner)
        return res
