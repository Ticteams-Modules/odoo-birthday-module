# -*- coding: utf-8 -*-

from odoo import _
from datetime import datetime
import http.client
import json
import xml.etree.ElementTree as ET
import logging
log = logging.getLogger(__name__)


class CPE:    
    
    def _format_phone(self, phone):
        res = ''
        if not phone:
            res = ''
        else:
            phone = phone.replace(" ", "").replace("-", "")
            if len(phone) >= 8:
                res = phone[-8:][:4] + '-' + phone[-8:][-4:]
            elif len(phone) == 7:
                res = phone[-8:][:3] + '-' + phone[-8:][-4:]
        return res

    def _set_tax(self, val):
        tax_rates = {0: '0', 7.0: '1', 10.0: '2', 15.0: '3'}
        return tax_rates.get(val, '0')
    
    def getCreditNote(self, invoice):
        fiscal_doc = self._buildFiscalDoc(invoice, invoice_number="credit")

        data = {
            "fiscalDoc": fiscal_doc
        }

        return json.dumps(data)
    
    def getDebitNote(self, invoice):
        fiscal_doc = self._buildFiscalDoc(invoice, invoice_number="debit")

        data = {
            "fiscalDoc": fiscal_doc
        }

        return json.dumps(data)


    def _getLinesInvoice(self, invoice_id):
        list_item = []
        invoices_line_ids = invoice_id.invoice_line_ids.filtered(lambda line: line.display_type == "product")
        line=1
        for item in invoices_line_ids:
            unspsc_code = item.product_id.pa_unspsc_code_id.code[:2] if item.product_id.pa_unspsc_code_id else ""
            precio_unitario = format((item.price_subtotal / item.quantity), '.5f')

            list_item.append({
                "id":line,
                "qty": format(item.quantity, '.2f'),
                "code": item.product_id.default_code or "",
                "desc": item.name,
                "price": precio_unitario,
                "tax": self._set_tax(item.tax_ids.amount) or "",
                "comments": "",
                "dperc": 0,
                "cat1Code": unspsc_code or ""
            })
            line+=1
            
        return list_item

    def _getPaymentList(self, invoice_id):
        formaPagoList = []
        id_num = 1
        if len(invoice_id.pa_payment_lines) != 0:
            for line in invoice_id.pa_payment_lines:
                formaPagoList.append({
                    "id":id_num,
                    'type': line.pa_payment_method,
                    "amt": format(line.amount, '.2f')}
                )
                id_num+=1
        else:
            formaPagoList.append({
                "id":id_num,
                'type': invoice_id.pa_payment_method,
                "amt": format(invoice_id.amount_total, '.2f')
            }
            )
        return formaPagoList

    def _getTotal(self, invoice_id):
        tax_totals_json = invoice_id.tax_totals
        group_taxs = []
        
        for tax_totals in tax_totals_json.get("groups_by_subtotal", {}):
            group_taxs += tax_totals_json["groups_by_subtotal"][tax_totals]

        amount_untaxed = sum(group_tax['tax_group_base_amount'] for group_tax in group_taxs)
        totalITBMS = sum(group_tax["tax_group_amount"] for group_tax in group_taxs)
        totalDescuento = invoice_id.pa_amount_discount or ''
        amount_total = invoice_id.amount_total
        nroItems = len(invoice_id.invoice_line_ids.filtered(lambda line: line.display_type == "product"))

        data = {
            "totalPrecioNeto": format(amount_untaxed, '.2f'),
            "totalITBMS": format(totalITBMS, '.2f'),
            "totalMontoGravado": format(totalITBMS, '.2f'),
            "totalDescuento": totalDescuento,
            "totalAcarreoCobrado": "",
            "valorSeguroCobrado": "",
            "totalFactura": format(amount_total, '.2f'),
            "totalValorRecibido": format(amount_total, '.2f'),
            "vuelto": "0.00",
            "tiempoPago": "1",
            "nroItems": nroItems,
            "totalTodosItems": format(amount_total, '.2f')
        }

        return data

    def _extractVoidedDocumentData(self, document):
        return {
            "cufe": document.pa_edocument_id.cufe,
            "motivo": document.cancellation_reason or "Anulacion de la Operacion",
            "is_annulment": True
        }
        
    def getVoidedDocuments(self, batch):
        if not batch:
            return {}

        document = batch[0]
        voided_document_data = self._extractVoidedDocumentData(document)

        return json.dumps(voided_document_data)

    def getDocumentStatus(self, invoice_id):
        datas = self._getDocumentData(invoice_id)
        datas.pop('posCod', None)
        return datas

    def _getCompanyData(self, invoice):
        return {
            "companyLicCod": invoice.company_id.user,
            "branchCod": invoice.company_id.l10n_pa_edi_address_type_code or "0000"
        }

    def _getCustomerData(self, invoice):
        partner = invoice.partner_id
        tipoClienteFE = partner.l10n_latam_identification_type_id.l10n_pa_vat_code
        numeroRUC = '0-000-0000' if not partner.vat and tipoClienteFE in ('99', '02') else partner.vat

        # Email: usar el del cliente; si no tiene, usar el de la compañía
        email = partner.email or ''
        if not email and invoice.company_id.default_invoice_email:
            email = invoice.company_id.default_invoice_email

        # Corregimiento: usar el del cliente; si no tiene, usar el de la compañía
        corregimiento_code = partner.l10n_pa_corregimiento.code or ''
        if not corregimiento_code and invoice.company_id.default_corregimiento_id:
            corregimiento_code = invoice.company_id.default_corregimiento_id.code

        return {
            "customerName": partner.name,
            "customerRUC": numeroRUC,
            "customerType": tipoClienteFE or "",
            "email": email,
            "customerLocationCod": corregimiento_code,
            "customerAddress": partner.street
        }

    def _getDocumentData(self, invoice, invoice_number=False):
        doc_parts = invoice.name.split('-')
        doc_data = {
            "posCod": doc_parts[0][-3:], 
            "docType": doc_parts[0][:1],
            "docNumber": doc_parts[1] 
        }
        if invoice_number == "credit":
            reversed_entry = invoice.reversed_entry_id
            doc_data["invoiceNumber"] = reversed_entry.name.split("-")[1]
        elif invoice_number == "debit":
            reversed_entry = invoice.debit_origin_id
            doc_data["invoiceNumber"] = reversed_entry.name.split("-")[1]
        
        return doc_data

    def _buildFiscalDoc(self, invoice, invoice_number=False):
        fiscal_doc = {
            **self._getCompanyData(invoice),
            **self._getDocumentData(invoice, invoice_number),
            **self._getCustomerData(invoice),
            "addInfo": [{"id": 1, "value": ""}],
            "items": self._getLinesInvoice(invoice),
            "discount": {"perc": "0%", "amt": 0},
            "payments": self._getPaymentList(invoice),
            "trailer": [{"id": 1, "value": "Información de Pago: Realizar Pagos a la cuenta de  Ahorros de Banco General  04-38-00-000859-4 a nombre de  TICTEAMS SOFTWARE, S. EP. "}],
        }

        if invoice.is_subject_to_retention:
            fiscal_doc["fepa"] = {
               "withHolding": {
                "code": 7,
                "value": round(invoice.retention_amount, 2)
               }
            }
        
        return fiscal_doc

    def getInvoice(self, invoice):
        payload = {
            "fiscalDoc": self._buildFiscalDoc(invoice)
        }
        return json.dumps(payload)


class Document(object):

    def __init__(self):
        self._xml = None
        self._type = None
        self._document_name = None
        self._client = None
        self._response = None
        self._response_status = None
        self._response_data = None

    def send(self):
        if self._type in ('sync', 'ra'):
            self._response = self._client.send_bill(self._xml)
        else:
            if self._type == 'status':
                self._response = self._client.get_status_pac(self._xml)

    def process_response(self):
        if self._response is not None:
            if self._type == 'sync':
                self._response_data = self._response
                return

    def process(self, document_name, type, xml, client):
        self._xml = xml
        self._type = type
        self._document_name = document_name
        self._client = client
        self.send()
        self.process_response()
        return (self._response)

    def get_status_pac(self, type, xml, client):
        self._type = 'status'
        self._xml = xml
        self._client = client
        self.send()
        self.process_response()
        return (self._response)


class Client(object):

    def __init__(self, ruc, username, password, url, debug=False, type=None, server=None, env_type=None):
        self._type = type
        self._username = username
        self._password = password
        self._debug = debug
        self._url = url
        self._server = server
        self._env_type = env_type
        self._method = 'getstatusPac'
        level = logging.DEBUG
        logging.basicConfig(level=level)
        log.setLevel(level)
        self._connect()

    def _connect(self):
        self._client = http.client.HTTPSConnection(self._url)

    def _call_ws(self, content_file):
        log.info(f"[_call_ws] Input content_file: {content_file}")
        if isinstance(content_file, str):
            data_dict = json.loads(content_file)
        else:
            data_dict = content_file

        datos = {}

        if self._type == 'status':
            try:
                env = "1" if self._env_type != "test" else "2"
                doc_type = data_dict.get("docType")
                doc_number = data_dict.get("docNumber")

                url = f"/api/fepa/ak/v1/getCufeBySystemRef/{self._username}/{self._password}/{env}/{doc_type}/{doc_number}"
                headers = {
                    "accept": "application/json"
                }
                
                self._client.request("GET", url, headers=headers)
                
                response = self._client.getresponse()
                data = response.read()
                datos_response = data.decode("utf-8")

                datos_response_dict = json.loads(datos_response)
                
                processed_response =  {
                    "cufe": datos_response_dict.get("cufe"),
                    "msg": "Autorizado" if datos_response_dict.get("authorized") else "",
                    "authDate": datos_response_dict.get("authDate"),
                    "authNumber": datos_response_dict.get("authNumber"),
                    "dateSentToDgi": datos_response_dict.get("dateSentToDgi"),
                    "resultado": "procesado" if datos_response_dict.get("authorized") else ""
                }
                
                return json.dumps(processed_response)

            except Exception as e:
                log.error(f"Error durante la solicitud HTTP de 'status': {str(e)}")
                raise RuntimeError(f"Error al realizar la solicitud HTTP de 'status': {str(e)}")

            
        elif data_dict.get('is_annulment'):            

            data_dict.pop('is_annulment', None)
            
            content_file = json.dumps(data_dict)
            url = f"/api/fepa/ak/v1/{self._env_type}/cancelFe/{self._username}/{self._password}"
            
            headers = {
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            }
            self._client.request("POST", url, content_file, headers)
            res = self._client.getresponse()
            data = res.read()
            datos_response = data.decode("utf-8")
            
            datos_response_dict = json.loads(datos_response)

            canceled = datos_response_dict.get("canceled")
            cufe = datos_response_dict.get("cufe")
            date = datos_response_dict.get("date")
            
            processed_response = {
                "canceled": canceled,
                "cufe": cufe,
                "date": date,
                "resultado": "procesado" if canceled else ""
            }
            
            if "resp" in datos_response_dict:
                root = ET.fromstring(datos_response_dict["resp"])
                namespace = {'ns': 'http://dgi-fep.mef.gob.pa/wsdl/FeRecepFE'}
                element = root.find(".//ns:dMsgRes", namespaces=namespace)
                response_message = element.text if element is not None else "Mensaje no encontrado"
                processed_response["msg"] = response_message
                
            
        else:
            fiscal_doc = data_dict.get("fiscalDoc", {})
            fiscal_doc["apiKey"] = self._password
            content_file = json.dumps(fiscal_doc)
            
            url = f"/api/fepa/ak/v1/{self._env_type}/sendFileToProcess/{self._username}/{self._password}"
            
            headers = {
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            }
            log.info(f"[_call_ws] Sending POST to URL: {url}")
            log.info(f"[_call_ws] Payload: {content_file}")

            self._client.request("POST", url, content_file, headers)
            res = self._client.getresponse()
            data = res.read()
            datos_response = data.decode("utf-8")
            log.info(f"[_call_ws] Response RAW: {datos_response}")

            data_dict = json.loads(data)
            
            processed_response =  {
                "qrContent": data_dict.get("qrContent"),
                "cufe": data_dict.get("cufe"),
                "msg": data_dict.get("msg"),
                "authDate": data_dict.get("authDate"),
                "authNumber": data_dict.get("authNumber"),
                "dateSentToDgi": data_dict.get("dateSentToDgi"),
                "resultado": "procesado" if data_dict.get("accepted") else ""
            }
            

        return json.dumps(processed_response)

        
    def _call_service(self, content_file):
        try:
            return self._call_ws(content_file)
        except Exception as e:
            return (False, {})

    def send_bill(self, content_file):
        return self._call_service(content_file)

    def get_pdf(self, cufe):
        try:
            url = f"/api/fepa/ak/v1/GetPdf/{self._username}/{self._password}/{cufe}"
            headers = {
                "accept": "application/json"
            }
            log.info(f"[get_pdf] Fetching PDF from: {url}")
            
            self._client.request("GET", url, headers=headers)
            response = self._client.getresponse()
            data = response.read()
            datos_response = data.decode("utf-8")
            
            # log.debug(f"[get_pdf] Response: {datos_response}")
            log.info(f"[get_pdf] Response RAW: {datos_response}")
            
            response_dict = json.loads(datos_response)
            
            if isinstance(response_dict, str):
                log.warning("[get_pdf] Response seems to be a double-encoded JSON string or just a string. Attempting to parse or return.")
                try:
                    # Try parsing again in case it's double encoded JSON
                    potential_dict = json.loads(response_dict)
                    if isinstance(potential_dict, dict):
                        response_dict = potential_dict
                except ValueError:
                    # Not a valid JSON string, maybe it's just the PDF content itself?
                    pass
            
            if isinstance(response_dict, dict):
                return response_dict.get('pdf')
            else:
                log.error(f"[get_pdf] Unexpected response format (not a dict): {type(response_dict)} - {response_dict}")
                return None
        except Exception as e:
            log.error(f"Error getting PDF from WebPOS: {str(e)}")
            return None


def get_document(self):
    xml = None
    if self.type == 'sync':
        if self.invoice_ids[0].l10n_latam_document_type_id.code == '04' and self.invoice_ids[0].reversed_entry_id:
            xml = CPE().getCreditNote(self.invoice_ids[0])
        elif self.invoice_ids[0].l10n_latam_document_type_id.code == '05' and self.invoice_ids[0].debit_origin_id:
            xml = CPE().getDebitNote(self.invoice_ids[0])
        else:
            xml = CPE().getInvoice(self.invoice_ids[0])
    else:
        if self.type == 'ra':
            xml = CPE().getVoidedDocuments(self.voided_ids[0])
    return xml


def get_status_pac(client, invoice_id):
    xml = None
    if invoice_id.type == 'sync':
        xml = CPE().getDocumentStatus(invoice_id.invoice_ids[0])
    else:
        if invoice_id.type == 'rc':
            xml = CPE().getDocumentStatus(invoice_id.voided_ids[0])
    document = {}
    document['type'] = 'statusPac'
    document['xml'] = xml
    client = Client(**client)
    document['client'] = client
    return Document().get_status_pac(**document)


def get_response(data):
    return (Document().get_response)(**data)


def send_dgi_cpe(client, document):
    client['type'] = 'send'
    client = Client(**client)
    document['client'] = client
    return (Document().process)(**document)


def get_pdf_from_webpos(client, cufe):
    client = Client(**client)
    return client.get_pdf(cufe)
