# -*- coding: utf-8 -*-
from odoo import models, api
import logging

log = logging.getLogger(__name__)

class PanamaDgiCpe(models.Model):
    _inherit = 'odoopanama.cpe'

    def send_cpe(self):
        log.error(f"[WebPOS Debug] send_cpe called for {self.name}")
        res = super(PanamaDgiCpe, self).send_cpe()
        
        log.error(f"[WebPOS Debug] send_cpe finished. server_type: {self.company_id.server_type}, response_code: {self.response_code}")

        # Check if the company uses WebPOS and if the response was successful
        if self.company_id.server_type == 'webpos' and self.response_code == 'procesado':
            log.error("[WebPOS Debug] Conditions met. Attempting to get PDF.")
            try:
                self._get_webpos_pdf()
            except Exception as e:
                log.error(f"[WebPOS Debug] Failed to retrieve PDF from WebPOS: {str(e)}")
        else:
            log.error("[WebPOS Debug] Conditions NOT met for PDF retrieval.")
        
        return res

    def _get_webpos_pdf(self):
        self.ensure_one()
        log.error(f"[WebPOS Debug] _get_webpos_pdf entered for CUFE: {self.cufe}")
        client_params = self.prepare_pac_auth()
        pac_module = self._get_current_pac_module()
        
        if hasattr(pac_module, 'get_pdf_from_webpos'):
            log.error("[WebPOS Debug] Calling get_pdf_from_webpos in core module...")
            pdf_content = pac_module.get_pdf_from_webpos(client_params, self.cufe)
            
            if pdf_content:
                log.error(f"[WebPOS Debug] PDF content received (len: {len(pdf_content)}). Creating attachment.")
                # Assuming pdf_content is base64 string from the response
                att = self.env['ir.attachment'].create({
                    'name': f"{self.get_document_name()}.pdf",
                    'type': 'binary',
                    'datas': pdf_content,
                    'res_model': 'account.move',
                    'res_id': self.invoice_ids[0].id if self.invoice_ids else False,
                    'mimetype': 'application/pdf',
                })
                log.error(f"[WebPOS Debug] PDF Attachment created: {att.id}")
            else:
                log.error(f"[WebPOS Debug] No PDF content returned for CUFE: {self.cufe}")
        else:
            log.error("[WebPOS Debug] WebPOS module does not have get_pdf_from_webpos function.")
