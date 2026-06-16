# -*- coding: utf-8 -*-
from importlib import import_module
import json

from odoo import models, fields, api, _, tools
from odoo.exceptions import UserError

import logging
log = logging.getLogger(__name__)


class PanamaDgiCpe(models.Model):
    _name = 'odoopanama.cpe'
    _description = 'Factura Electronica Panama'
    _order = 'date desc, name desc'
    
    name = fields.Char("Name", default="/")
    state = fields.Selection([
        ('draft', 'Draft'),
        ('generate', 'Generated'),
        ('send', 'Send'),
        ('verify', 'Waiting'),
        ('done', 'Done'),
        ('cancel', 'Cancelled'),
    ], string='Status', index=True, readonly=True, default='draft', copy=False)
    type = fields.Selection([
        ('sync', 'Envio online'),
        ('rc', 'Resumen diario'),
        ('ra', 'Comunicación de Baja'),
    ], string="Type", default='sync')
    date = fields.Datetime("Date", default=fields.Datetime.now)
    company_id = fields.Many2one('res.company', string='Company', change_default=True,
                                 required=True, readonly=True,
                                 default=lambda self: self.env['res.company']._company_default_get('pe.sunat.cpe'))
    pa_edocument = fields.Text("XML Document")

    note = fields.Text("Note", readonly=True)
    error_code = fields.Char(string="Error Code", readonly=True)
    digest = fields.Char("Digest", readonly=True)
    invoice_ids = fields.One2many(
        "account.move", 'pa_edocument_id', string="Invoices", readonly=True)
    ticket = fields.Char("Ticket", readonly=True)
    date_end = fields.Datetime("End Date")
    send_date = fields.Datetime("Send Date")
    voided_ids = fields.One2many(
        "account.move", "pa_voided_id", string="Voided Invoices")
    is_voided = fields.Boolean("Is Boided")

    response = fields.Char("Response", readonly=True)
    response_code = fields.Char("Response Code", readonly=True)

    authorization_protocol = fields.Char(
        "Nro Authorization Protocol", readonly=True)
    cufe = fields.Char("CUFE", readonly=True)
    dateReceptionDGI = fields.Char("Date Reception DGI", readonly=True)
    deadline = fields.Char("Deadline", readonly=True)
    qrcontent = fields.Text("Qr Content",)
    
    @api.model
    def _import_pac_module(self, pac_type):
        log.error(f"[CPE:_import_pac_module] Importando módulo PAC: {pac_type}")
        try:
            module = import_module(f'.cpe_core_{pac_type}', package=__package__)
            log.error(f"[CPE:_import_pac_module] Módulo importado OK: {module.__name__}")
            return module
        except ImportError as e:
            log.error(f"[CPE:_import_pac_module] ERROR al importar PAC '{pac_type}': {e}", exc_info=True)
            raise UserError(f"No se pudo importar el módulo para el PAC '{pac_type}'. Error: {str(e)}")
        
        
    @api.model
    @tools.ormcache('pac_type')
    def _get_pac_module(self, pac_type):
        return self._import_pac_module(pac_type)
    
    def _get_current_pac_module(self):
        pac_type = self.company_id.server_type
        return self._get_pac_module(pac_type)
    
    def unlink(self):
        for batch in self:
            if batch.name != "/" and batch.state != "draft":
                raise UserError(_('You can only delete sent documents.'))
        return super(PanamaDgiCpe, self).unlink()

    def action_draft(self):
        if not self.pa_edocument and self.type == "sync":
            self._prepare_cpe()
        self.state = 'draft'

    def action_generate(self):
        if self.type in ['rc', 'ra']:
            if self.response:
                self.response = ''
            if not self.send_date:                
                self.send_date = fields.Datetime.now()
            if self.type == "sync" and self.name == "/":
                self.name = self.invoice_ids[0].number

        if not self.pa_edocument:
            self._prepare_cpe()
            self.name =  self.get_document_name()
        elif self.name != "/" and self.type in ["rc", "ra"]:
            if self.get_document_name() != self.name:
                self._prepare_cpe()
        self.state = 'generate'

    def action_send(self):
        state = self.send_cpe()
        if state:
            self.state = state

    def action_verify(self):
        self.state = 'verify'

    def action_cancel(self):
        self.state = 'cancel'

    @api.model
    def create_from_invoice(self, invoice_id):
        vals = {}
        vals['invoice_ids'] = [(4, invoice_id.id)]
        vals['type'] = 'sync'
        vals['company_id'] = invoice_id.company_id.id
        res = self.create(vals)
        return res

    @api.model
    def get_cpe_async(self, type, invoice_id, is_voided=False):
        res = None
        company_id = invoice_id.company_id.id
        date_invoice = invoice_id.invoice_date
        if not res:
            vals = {}
            vals['type'] = type
            vals['date'] = date_invoice
            vals['company_id'] = company_id
            vals['is_voided'] = is_voided
            res = self.create(vals)
        return res

    def get_document_name(self):
        self.ensure_one()
        name = False
        if self.type == "sync":
            name = self.invoice_ids[0].name
        elif self.type == "ra":
            name = self.voided_ids[0].name + " [Anulación]"
        return name

    def get_document_name_manual(self):
        self.ensure_one()
        ruc = self.company_id.partner_id.vat
        if self.type == "sync":
            number = self.name
            doc_code = "-%s" % (self.l10n_latam_document_type_id.code or '01')
        else:
            doc_code = ""
            number = self.name or ""
        return "%s%s-%s" % (ruc, doc_code, number)

    def prepare_pac_auth(self):
        self.ensure_one()
        urls = {
            'ebi': {
                'test': "https://demointegracion.ebi-pac.com/ws/obj/v1.0/Service.svc?singleWsdl",
                'prod': "https://emision.ebi-pac.com/ws/obj/v1.0/Service.svc?singleWsdl"
            },
            'thefactoryhka': {
                'test': "https://demoemision.thefactoryhka.com.pa/ws/obj/v1.0/Service.svc?singleWsdl",
                'prod': "https://emision.thefactoryhka.com.pa/ws/obj/v1.0/Service.svc?singleWsdl"
            },
        }
        company = self.company_id
        env_type = 'prod' if company.type_env else 'test'
        server_type = company.server_type

        if server_type == 'webpos':
            # Lee la URL desde la configuración de la compañía
            raw_url = company.url if company.type_env else company.url_dev
            # HTTPSConnection solo acepta hostname, sin esquema ni slash final
            url = raw_url.replace('https://', '').replace('http://', '').strip('/') if raw_url else ''
        else:
            url = urls[server_type][env_type]

        res = {
            'ruc': company.partner_id.vat,
            'username': company.user,
            'password': company.password,
            'url': url,
            'env_type': env_type,
            'server': server_type
        }

        return res

    def _prepare_cpe(self):
        log.error(f"[CPE:_prepare_cpe] CPE id={self.id} | name={self.name} | pa_edocument={'OK' if self.pa_edocument else 'VACÍO'}")
        if not self.pa_edocument:
            try:
                self.name = self.get_document_name()
                log.error(f"[CPE:_prepare_cpe] document_name={self.name}")
                pac_module = self._get_current_pac_module()
                log.error(f"[CPE:_prepare_cpe] PAC module={pac_module.__name__}")
                pa_edocument = pac_module.get_document(self)
                log.error(f"[CPE:_prepare_cpe] Documento generado OK (len={len(pa_edocument) if pa_edocument else 0})")
                self.pa_edocument = pa_edocument
            except Exception as e:
                log.error(f"[CPE:_prepare_cpe] ERROR: {e}", exc_info=True)
                raise

    def send_cpe(self):
        self.ensure_one()
        log.error(f"[CPE:send_cpe] Iniciando envío | CPE id={self.id} | name={self.name} | type={self.type}")

        if not self.send_date:
            self.send_date = fields.Datetime.now()

        local_date = self.send_date.date().strftime("%Y-%m-%d")

        if self.type == "sync" and self.name == "/":
            self.name = self.invoice_ids[0].number
        elif self.type == "ra" and self.name == "/":
            self.name = self.voided_ids[0].name + " [Anulación]"

        file_name = self.get_document_name()
        client = self.prepare_pac_auth()
        document = {
            'document_name': file_name,
            'type': self.type,
            'xml': self.pa_edocument
        }
        pac_module = self._get_current_pac_module()
        try:
            response = pac_module.send_dgi_cpe(client, document)
        except Exception as e:
            log.error(f"[CPE:send_cpe] ERROR en send_dgi_cpe: {e}", exc_info=True)
            raise

        log.error(f"[CPE:send_cpe] Respuesta DGI raw: {response}")

        if response:
            try:
                response_dict = json.loads(response)
            except Exception as e:
                log.error(f"[CPE:send_cpe] ERROR al parsear respuesta JSON: {e} | raw={response}")
                raise
            self.error_code = response_dict.get("error_code")
            self.response = f"{response_dict.get('msg')}"
            self.qrcontent = response_dict.get("qrContent")
            self.response_code = response_dict.get("resultado")
            self.authorization_protocol = response_dict.get("authNumber")
            self.cufe = response_dict.get("cufe")
            self.deadline = response_dict.get("authDate")
            self.dateReceptionDGI = response_dict.get("authDate")
            log.error(f"[CPE:send_cpe] resultado={self.response_code} | cufe={self.cufe} | msg={self.response} | error_code={self.error_code}")

            new_state = self.get_response_details()
            return new_state or "send"

        log.error(f"[CPE:send_cpe] Respuesta vacía o None del PAC")
        return None   



    @api.depends('response_code')
    def get_response_details(self):
        self.ensure_one()
        state = self.state
        if self.response_code:
            if self.response_code == "procesado":
                state = "done"
        return state

    def generate_cpe(self):
        log.error(f"[CPE:generate_cpe] Generando CPE id={self.id}")
        try:
            self._prepare_cpe()
            self.state = "generate"
            log.error(f"[CPE:generate_cpe] CPE generado OK | state={self.state}")
        except Exception as e:
            log.error(f"[CPE:generate_cpe] ERROR: {e}", exc_info=True)
            raise

    def action_document_status(self):
        client = self.prepare_pac_auth()
        pac_module = self._get_current_pac_module()
        response = pac_module.get_status_pac(client, self)
        res = self.state
        if response:
            response_dict = json.loads(response)
            self.response = f"{response_dict.get('msg')}"
            self.qrcontent = response_dict.get("qrContent")
            self.response_code = response_dict.get("resultado")
            self.authorization_protocol = response_dict.get("authNumber")
            self.cufe = response_dict.get("cufe")
            self.deadline = response_dict.get("authDate")
            self.dateReceptionDGI = response_dict.get("authDate")
            self.error_code = False

            new_state = self.get_response_details()
            return new_state or "send"
        return res

    def send_async_cpe(self):
        cpe_ids = self.search(
            [('state', 'in', ['generate', 'send']), ('type', 'in', ['sync'])])
        for cpe_id in cpe_ids:
            if cpe_id.invoice_ids:
                if cpe_id.invoice_ids[0].l10n_latam_document_type_id.code not in ["03", "07"]:
                    try:
                        cpe_id.action_document_status()
                    except Exception:
                        pass
                if cpe_id.state != 'done':
                    if cpe_id.invoice_ids[0].l10n_latam_document_type_id.code not in ["03", "07"]:
                        try:
                            cpe_id.action_generate()
                            cpe_id.action_send()
                        except Exception:
                            pass
