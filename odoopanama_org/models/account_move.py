# -*- coding: utf-8 -*-
from ast import literal_eval
from odoo import api, fields, tools, models, _
from odoo.exceptions import UserError
import tempfile
from base64 import encodebytes
import re
from datetime import datetime, date, timedelta
from io import BytesIO
from importlib import reload
import sys
from num2words import num2words
import logging

_logging = logging.getLogger(__name__)

try:
    import qrcode
    qr_mod = True
except Exception:
    qr_mod = False

TYPE2JOURNAL = {
    'out_invoice': 'sale',
    'in_invoice': 'purchase',
    'out_refund': 'sale',
    'in_refund': 'purchase',
}


class AccountMove(models.Model):
    _inherit = 'account.move'

    # ── Campos de odoopanama_org_origin ───────────────────────────────────────
    origin_move_id = fields.Many2one(
        comodel_name='account.move',
        string='Documento Rectificado',
        domain="[('id', '!=', id)]",
    )
    origin_number = fields.Char(string='Referencia Documento Rectificado')
    origin_l10n_latam_document_type_id = fields.Many2one(
        comodel_name='l10n_latam.document.type',
        string='Tipo Documento Rectificado',
    )
    origin_invoice_date = fields.Date(string='Fecha Rectificado')

    # ── Campos de odoopanama_org_base ─────────────────────────────────────────
    amount_text = fields.Char("Monto en letras", compute="_get_amount_text")
    pa_related_ids = fields.Many2many(
        "account.move", string="Facturas relacionadas", compute="_get_related_ids")
    annul = fields.Boolean('Anulado', readonly=True)
    state = fields.Selection(
        selection_add=[('annul', 'Anulado')], ondelete={'annul': 'cascade'})
    is_subject_to_retention = fields.Boolean(
        string="Is Subject to Retention",
        compute="_compute_is_subject_to_retention",
        store=True,
        help="Indicates if this invoice is subject to retention based on the partner's retention status.",
    )
    retention_amount = fields.Monetary(
        string="Retention Amount",
        compute="_compute_retention_amount",
        store=True,
        help="The amount of retention applied based on the ITBMS rate and total ITBMS.",
    )

    # ── Campos de odoopanama_org_cpe ──────────────────────────────────────────
    pa_dgi_type_emission = fields.Selection(
        selection=[
            ('01', '[01] Autorización de Uso Previa, operación normal'),
            ('02', '[02] Autorización de Uso Previa, operación en contingencia'),
            ('03', '[03] Autorización de Uso Posterior, operación normal.'),
            ('04', '[04] Autorización de Uso posterior, operación en contingencia.'),
        ],
        string="Tipo de Emisión",
        store=True, readonly=False,
        compute='_compute_l10n_pa_edi_emission_type',
    )
    pa_dgi_date_contingency = fields.Datetime(
        'Fecha/Hora de Contingencia', copy=False,
        help="Obligatorio si, tipoEmision = 02 / 04",
    )
    pa_dgi_reason_contingency = fields.Char(
        'Motivo de Contingencia', copy=False,
        help="Obligatorio si tipoEmision=02 / 04 Si la contingencia dura más de 72 horas también debe explicar las razones para no haber regresado a la operación normal.",
    )
    pa_dgi_nature_operation = fields.Selection(
        selection=[
            ('01', 'Venta'),
            ('02', 'Exportación'),
            ('10', 'Transferencia'),
            ('11', 'Devolución'),
            ('12', 'Consignación'),
            ('13', 'Remesa'),
            ('14', 'Entrega gratuita'),
            ('20', 'Compra'),
            ('21', 'Importación'),
        ],
        string='Naturaleza de la Operacion',
        default='01',
    )
    pa_dgi_type_operation = fields.Selection(
        selection=[
            ('1', 'Salida o venta'),
            ('2', 'Entrada o compra (factura de compra- para comercio informal. Ej.: taxista, trabajadores manuales)'),
        ],
        string='Tipo de Operación',
        default='1',
    )
    pa_dgi_destiny_operation = fields.Selection(
        selection=[
            ('1', 'Panamá'),
            ('2', 'Extranjero'),
        ],
        string='Destino de la Operación',
        default='1',
    )
    pa_dgi_type_sale = fields.Selection(
        selection=[
            ('1', 'Venta de Giro del negocio'),
            ('2', 'Venta Activo Fijo'),
            ('3', 'Venta de Bienes Raíces.'),
            ('4', 'Prestación de Servicio'),
        ],
        string='Tipo de Venta',
        help='Tipo de Venta para el vendedor. Si no es venta, no informar este campo',
        default='1',
    )
    cancellation_reason = fields.Char('Motivo de Anulación', readonly=True, copy=False)
    pa_edocument_id = fields.Many2one('odoopanama.cpe', 'PAC CPE', copy=False)
    pa_response = fields.Char('Respuesta', related='pa_edocument_id.response')
    is_cpe = fields.Boolean('Es CPE', related='journal_id.is_cpe')
    pa_voided_id = fields.Many2one('odoopanama.cpe', 'Documento anulado', copy=False)
    pa_doc_name = fields.Char('Nombre del documento', compute='_get_panamanian_doc_name')
    pa_invoice_state = fields.Selection(
        string='Estado cpe', related='pa_edocument_id.state', copy=False)
    state_dgi = fields.Char(string='Estado DGI', related='pa_edocument_id.response_code')
    pa_invoice_date = fields.Datetime('Hora/fecha de la factura', copy=False)
    dgi_qr_code = fields.Binary('QR Code Sunat', compute='_compute_get_qr_code')
    pa_total_discount = fields.Float('Descuento total', compute='_compute_discount')
    pa_amount_discount = fields.Monetary(
        string='Descuento', compute='_compute_discount', tracking=True)
    pa_total_discount_tax = fields.Monetary(
        string='Impuesto de descuento', compute='_compute_discount', tracking=True)
    pe_charge_total = fields.Monetary(
        'Precio a cobrar', compute='get_pe_charge_amount', currency_field='company_currency_id')
    pa_payment_lines = fields.One2many('pa.payment.date', 'move_id', 'Payment Lines')
    pa_qty_fees = fields.Integer("Cantidad de Cuotas", default=1, copy=False)
    from_wizard_revert = fields.Boolean()

    # ── Métodos de odoopanama_org_origin ──────────────────────────────────────
    @api.onchange('origin_move_id', 'reversed_entry_id', 'debit_origin_id')
    def _onchange_origin_move_id(self):
        origin_move_id = (
            self.origin_move_id or self.reversed_entry_id or self.debit_origin_id or False)
        document_type, invoice_date, number = self.get_data_from_origin_move_id(origin_move_id)
        self.update({
            'origin_l10n_latam_document_type_id': document_type,
            'origin_number': number,
            'origin_invoice_date': invoice_date,
        })

    @staticmethod
    def get_data_from_origin_move_id(origin_move_id):
        document_type = False
        invoice_date = False
        number = False
        if origin_move_id and origin_move_id.l10n_latam_document_type_id:
            if origin_move_id.payment_reference and origin_move_id.move_type != 'out_invoice':
                number = origin_move_id.payment_reference.replace(' ', '')
            elif origin_move_id.ref and origin_move_id.move_type != 'out_invoice':
                number = origin_move_id.ref.replace(' ', '')
            elif origin_move_id.move_type == 'out_invoice':
                number = origin_move_id.name.replace(' ', '')
            else:
                number = ''
            document_type = origin_move_id.l10n_latam_document_type_id.id
            invoice_date = origin_move_id.invoice_date
        return document_type, invoice_date, number

    def _reverse_moves(self, default_values_list=None, cancel=False):
        list_moves = super(AccountMove, self)._reverse_moves(
            default_values_list=default_values_list, cancel=cancel)
        for obj_move in list_moves:
            obj_move._onchange_origin_move_id()
        return list_moves

    # ── Métodos de odoopanama_org_base ────────────────────────────────────────
    @api.depends('amount_total')
    def _get_amount_text(self):
        for invoice in self:
            if invoice.amount_total < 2 and invoice.amount_total >= 1:
                currency_name = (
                    invoice.currency_id.singular_name
                    or invoice.currency_id.plural_name
                    or invoice.currency_id.name or "")
            else:
                currency_name = (
                    invoice.currency_id.plural_name
                    or invoice.currency_id.name or "")
            fraction_name = invoice.currency_id.fraction_name or ""
            amount_text = invoice.currency_id.amount_to_text(invoice.amount_total)
            invoice.amount_text = amount_text

    @api.depends('invoice_line_ids')
    def _get_related_ids(self):
        for move_id in self:
            related_ids = move_id.invoice_line_ids.mapped('pa_invoice_id').ids or []
            if move_id.debit_origin_id:
                related_ids.append(move_id.debit_origin_id.id)
            if move_id.reversed_entry_id:
                related_ids.append(move_id.reversed_entry_id.id)
            move_id.pa_related_ids = related_ids

    @api.model
    def _prepare_refund(self, invoice, date_invoice=None, date=None,
                        description=None, journal_id=None):
        res = super(AccountMove, self)._prepare_refund(
            invoice, date_invoice=date_invoice, date=date,
            description=description, journal_id=journal_id)
        journal_id = res.get('journal_id')
        if journal_id and not self.env.context.get("is_pa_debit_note"):
            journal = self.env['account.journal'].browse(journal_id)
            res['journal_id'] = journal.credit_note_id and journal.credit_note_id.id or journal.id
        elif journal_id and self.env.context.get("is_pa_debit_note"):
            journal = self.env['account.journal'].browse(journal_id)
            res['journal_id'] = journal.dedit_note_id and journal.dedit_note_id.id or journal.id
            res['type'] = "out_invoice"
            res['refund_invoice_id'] = invoice.id
        return res

    @api.depends('partner_id')
    def _compute_is_subject_to_retention(self):
        for move in self:
            move.is_subject_to_retention = move.partner_id.is_retainer

    @api.depends('amount_tax', 'is_subject_to_retention', 'partner_id.retention_code')
    def _compute_retention_amount(self):
        for move in self:
            if move.is_subject_to_retention and move.partner_id.retention_code:
                retention_percentage = (
                    1.0 if move.partner_id.retention_code in ['1', '3'] else 0.5)
                move.retention_amount = move.amount_tax * retention_percentage
            else:
                move.retention_amount = 0.0

    # ── Métodos de odoopanama_org_cpe ─────────────────────────────────────────
    @api.depends('move_type', 'company_id')
    def _compute_l10n_pa_edi_emission_type(self):
        for move in self:
            move.pa_dgi_type_emission = '01'

    @api.model
    def _l10n_pe_edi_amount_to_text(self):
        self.ensure_one()
        amount_i, amount_d = divmod(self.amount_total, 1)
        amount_d = int(round(amount_d * 100, 2))
        words = num2words(amount_i, lang='es')
        result = '%(words)s Y %(amount_d)02d/100 %(currency_name)s' % {
            'words': words,
            'amount_d': amount_d,
            'currency_name': self.currency_id.currency_unit_label,
        }
        return result.upper()

    @api.model
    def _get_payment_methods(self):
        return []

    def generate_pa_fees(self):
        self.ensure_one()
        if self.pa_qty_fees <= 0:
            raise UserError(_("Las cuotas deben ser superiores a cero"))
        if self.amount_total <= 0.0:
            raise UserError(_("El total debe ser mayor que cero"))
        if self.invoice_date == self.invoice_date_due:
            raise UserError(
                _("La fecha de la factura debe ser diferente a la fecha de vencimiento."))

        pa_start_date = self.invoice_date or fields.Date.context_today(self)
        pa_payment_date_end = self.invoice_date_due or fields.Date.context_today(self)
        self.pa_payment_lines.unlink()

        context = self.env.context.copy()
        context.update({
            'pa_payment_date_start': pa_start_date,
            'pa_payment_date_end': pa_payment_date_end,
            'pa_payment_qty': self.pa_qty_fees,
            'pa_payment_method': self._first_payment_method(),
            'pa_payment_amount': self.amount_total,
        })
        pa_payment_lines = self.env['pa.payment.date'].with_context(**context).get_payment_by_qty_date()
        self.pa_payment_lines = pa_payment_lines

    def _get_address_details(self, partner):
        self.ensure_one()
        address = ''
        if partner.l10n_pa_corregimiento:
            address = "%s" % (partner.l10n_pa_corregimiento.name)
        if partner.city:
            address += ", %s" % (partner.city)
        if partner.state_id.name:
            address += ", %s" % (partner.state_id.name)
        if partner.zip:
            address += ", %s" % (partner.zip)
        if partner.country_id.name:
            address += ", %s" % (partner.country_id.name)
        reload(sys)
        html_text = str(tools.plaintext2html(address, container_tag=True))
        data = html_text.split('p>')
        if data:
            return data[1][:-2]
        return False

    def _get_street(self, partner):
        self.ensure_one()
        address = ''
        if partner.street:
            address = "%s" % (partner.street)
        if partner.street2:
            address += ", %s" % (partner.street2)
        reload(sys)
        html_text = str(tools.plaintext2html(address, container_tag=True))
        data = html_text.split('p>')
        if data:
            return data[1][:-2]
        return False

    @api.model
    def get_pe_charge_amount(self):
        for invoice_id in self:
            pe_charge_total = 0.0
            for line in invoice_id.invoice_line_ids.filtered(lambda line: not line.display_type):
                pe_charge_total += line.pe_charge_amount
            invoice_id.pe_charge_total = pe_charge_total

    @api.onchange('invoice_date')
    def onchange_pa_invoice_date(self):
        self.action_date_assign()

    @api.model
    def action_date_assign(self):
        for inv in self:
            today = fields.Date.context_today(self)
            if not inv.invoice_date:
                inv.pa_invoice_date = today
            else:
                local_date = fields.Date.from_string(today)
                dt = (local_date == fields.Date.from_string(inv.invoice_date)
                      and today or str(inv.invoice_date) + ' 23:55:00')
                inv.pa_invoice_date = dt

    @api.depends(
        'amount_total', 'currency_id', 'invoice_line_ids',
        'invoice_line_ids.amount_discount')
    def _compute_discount(self):
        total_discount = 0.0
        ICPSudo = self.env['ir.config_parameter'].sudo()
        default_deposit_product_id = literal_eval(
            ICPSudo.get_param('sale.default_deposit_product_id', default='False'))
        discount = 0.0
        total_discount_tax = 0.0
        for line in self.invoice_line_ids.filtered(lambda line: not line.display_type):
            if line.price_total < 0.0:
                price = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
                taxes = line.tax_ids.compute_all(
                    price, self.currency_id, line.quantity, line.product_id, self.partner_id)
                if default_deposit_product_id:
                    if default_deposit_product_id != line.product_id.id:
                        if taxes:
                            for tax in taxes.get('taxes', []):
                                total_discount_tax += tax.get('amount', 0.0)
                        total_discount += line.price_total
                if not default_deposit_product_id:
                    total_discount += line.price_total
                    if taxes:
                        for tax in taxes.get('taxes', []):
                            total_discount_tax += tax.get('amount', 0.0)
            discount += line.amount_discount

        self.pa_total_discount = abs(total_discount)
        self.pa_total_discount_tax = abs(total_discount_tax)
        self.pa_amount_discount = discount

    @api.depends('l10n_latam_document_type_id')
    def _get_panamanian_doc_name(self):
        for invoice_id in self:
            if invoice_id.l10n_latam_document_type_id:
                pa_doc_name = (invoice_id.l10n_latam_document_type_id
                               and invoice_id.l10n_latam_document_type_id.name or '')
                invoice_id.pa_doc_name = pa_doc_name.title()
            else:
                invoice_id.pa_doc_name = ""

    @api.depends('name', 'journal_id.is_cpe', 'pa_edocument_id')
    def _compute_get_qr_code(self):
        for invoice in self:
            if not all((
                invoice.name != '/',
                invoice.journal_id.is_cpe,
                invoice.pa_edocument_id.qrcontent,
                qr_mod,
            )):
                invoice.dgi_qr_code = ''
            else:
                if invoice.pa_edocument_id.qrcontent and invoice.journal_id.is_cpe:
                    qr_string = str(invoice.pa_edocument_id.qrcontent)
                    qr = qrcode.QRCode(
                        version=1,
                        error_correction=(qrcode.constants.ERROR_CORRECT_Q),
                    )
                    qr.add_data(qr_string)
                    qr.make(fit=True)
                    image = qr.make_image(fill='black')
                    tmpf = BytesIO()
                    image.save(tmpf, 'png')
                    invoice.dgi_qr_code = encodebytes(tmpf.getvalue())
                else:
                    invoice.dgi_qr_code = ''

    def _first_payment_method(self):
        payment_methods = self.env['account.move']._get_payment_methods()
        first_payment_method = payment_methods[0][0] if payment_methods else False
        return first_payment_method

    def action_open_payment_wizard(self):
        payment_lines = []
        if self.pa_payment_lines:
            payment_lines = [(0, 0, {
                'amount': line.amount,
                'date': line.date,
                'pa_payment_method': line.pa_payment_method,
            }) for line in self.pa_payment_lines]
        else:
            payment_lines = [(0, 0, {
                'amount': self.amount_total,
                'date': self.invoice_date or fields.Date.context_today(self),
                'pa_payment_method': self._first_payment_method(),
            })]
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'payment.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_payment_line_ids': payment_lines},
        }

    def _validate_pe_fees(self):
        if not self.invoice_date == self.invoice_date_due and len(self.pa_payment_lines) < 1:
            if self.pa_qty_fees < 2:
                self.generate_pa_fees()
            else:
                if len(self.pa_payment_lines) < 2:
                    note = (
                        "Ud. Asignó {} cuotas. Por favor detalle las fechas y los montos "
                        "de las cuotas de crédito".format(self.pa_qty_fees))
                    raise UserError((note))

    def validate_dgi_invoice(self):
        lines = self.invoice_line_ids.filtered(lambda line: line.display_type == "product")
        doc_type = self.partner_id.l10n_latam_identification_type_id.l10n_pa_vat_code
        doc_codes = self.partner_id.get_doc_codes()
        government_codes = doc_codes.get('government', [])
        taxpayer_codes = doc_codes.get('taxpayer', [])

        for line in lines:
            if doc_type in government_codes and not line.product_id.pa_unspsc_code_id:
                raise UserError(
                    f'El cliente {self.partner_id.name} es una entidad gubernamental. '
                    f'Es necesario asignar un código UNSPSC en el producto: {line.product_id.name}'
                )

        if doc_type in taxpayer_codes and not self.partner_id.l10n_pa_corregimiento:
            raise UserError(f'Ingrese el Corregimiento del Cliente: {self.partner_id.name}')

        if not self.pa_payment_lines:
            default_method = self.company_id.default_payment_method
            if default_method:
                self.pa_payment_lines = [(0, 0, {
                    'amount': self.amount_total,
                    'date': self.invoice_date or fields.Date.context_today(self),
                    'pa_payment_method': default_method,
                })]
            else:
                raise UserError('Debe agregar al menos un método de pago.')

        for payment_line in self.pa_payment_lines:
            if not payment_line.pa_payment_method:
                raise UserError(
                    f'Cada línea de método de pago debe tener un método de pago asignado. \n'
                    f'Verifique la línea con monto {payment_line.amount}.')

        if self.partner_id.parent_id and self.partner_id.vat:
            raise UserError(
                f'Para generar este comprobante debe cambiar los datos de contacto '
                f'{self.partner_id.name} por los datos de la Empresa principal '
                f'{self.partner_id.parent_id.name}'
            )

        if not self.partner_id.vat and doc_type in taxpayer_codes + government_codes:
            raise UserError(
                f'El cliente {self.partner_id.name} no tiene asignado un número de documento.')

        date_invoice = fields.Datetime.from_string(self.pa_invoice_date or self.invoice_date)
        today = fields.Datetime.context_timestamp(self, datetime.now())
        days_diff = (today.replace(tzinfo=None) - date_invoice).days
        if days_diff < 0 or days_diff > 6:
            raise UserError(
                'La fecha de emisión no puede ser menor a 6 días de hoy ni mayor a la fecha de hoy.')

    @api.depends('l10n_latam_available_document_type_ids', 'debit_origin_id')
    def _compute_l10n_latam_document_type(self):
        debit_note = self.debit_origin_id
        for rec in self.filtered(lambda x: x.state == 'draft'):
            document_types = (
                rec.journal_id.l10n_latam_document_type_id
                or rec.l10n_latam_available_document_type_ids._origin)
            document_types = (
                debit_note
                and document_types.filtered(lambda x: x.internal_type == 'debit_note')
                or document_types)
            rec.l10n_latam_document_type_id = document_types and document_types[0].id

    def pa_generate_send(self):
        for invoice_id in self:
            if invoice_id.pa_edocument_id:
                invoice_id.pa_edocument_id.pa_edocument = False
            invoice_id.pa_edocument_id.generate_cpe()
            invoice_id.pa_edocument_id.action_send()

    def _post(self, soft=True):
        _logging.info("Step 1: Entrando a _post")
        res = super(AccountMove, self)._post()
        for invoice_id in self:
            _logging.info(f"Step 2: Procesando factura {invoice_id.name} ID: {invoice_id.id}")
            invoice_id.action_date_assign()
            is_cpe = invoice_id.is_cpe
            doc_type_code = invoice_id.journal_id.l10n_latam_document_type_id.code
            _logging.info(f"Step 3: is_cpe={is_cpe}, doc_type={doc_type_code}")

            if invoice_id.is_cpe and invoice_id.journal_id.l10n_latam_document_type_id.code in (
                    '01', '04', '05', '07', '08'):
                _logging.info("Step 4: Entrando al bloque CPE")
                to_write = {}
                if len(((invoice_id.name).replace(" ", "")).split("-")) < 2:
                    invoice_id.payment_reference = (invoice_id.name).replace(" ", "")
                _logging.info("Step 5: Validando DGI invoice")
                invoice_id.validate_dgi_invoice()
                _logging.info("Step 6: Validando PE fees")
                invoice_id._validate_pe_fees()
                if not invoice_id.pa_edocument_id:
                    _logging.info("Step 7: Creando pa_edocument_id")
                    cpe_id = self.env['odoopanama.cpe'].create_from_invoice(invoice_id)
                    invoice_id.pa_edocument_id = cpe_id.id
                else:
                    _logging.info(f"Step 7: Ya existe pa_edocument_id: {invoice_id.pa_edocument_id.id}")
                    cpe_id = invoice_id.pa_edocument_id
                is_sync = invoice_id.company_id.pe_is_sync
                _logging.info(f"Step 8: pe_is_sync={is_sync}")
                if invoice_id.company_id.pe_is_sync:
                    _logging.info("Step 9: Generando CPE (Sync)")
                    cpe_id.generate_cpe()
                    is_synchronous = invoice_id.journal_id.is_synchronous
                    _logging.info(f"Step 10: is_synchronous={is_synchronous}, doc_type_code={doc_type_code}")
                    if (invoice_id.journal_id.is_synchronous
                            or invoice_id.journal_id.l10n_latam_document_type_id.code in ('01', '04')):
                        if not self.env.context.get('is_pos_invoice'):
                            _logging.info("Step 11: Enviando CPE (Sync)")
                            cpe_id.action_send()
                        else:
                            _logging.info("Step 11: Omitiendo envio porque es POS invoice")
                else:
                    _logging.info("Step 9: Generando CPE (Async)")
                    cpe_id.generate_cpe()
            else:
                _logging.info("Step 4: No entra al bloque CPE")
        _logging.info("Step 12: Finalizando _post")
        return res

    @api.depends(
        'currency_id', 'partner_id', 'invoice_line_ids',
        'invoice_line_ids.tax_ids', 'invoice_line_ids.quantity',
        'invoice_line_ids.product_id', 'invoice_line_ids.discount')
    def _pe_compute_operations(self):
        for invoice_id in self:
            total_1004 = 0
            for line in invoice_id.invoice_line_ids.filtered(lambda line: not line.display_type):
                price_unit = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
                total_excluded = line.tax_ids.compute_all(
                    price_unit, invoice_id.currency_id, line.quantity,
                    line.product_id, invoice_id.partner_id)['total_excluded']
                price_unit = line.price_unit
                total_excluded = line.tax_ids.compute_all(
                    price_unit, invoice_id.currency_id, line.quantity,
                    line.product_id, invoice_id.partner_id)['total_excluded']
                total_1004 += total_excluded

    def button_cancel(self):
        res = super().button_cancel()
        if res:
            for invoice_id in self:
                if (invoice_id.is_cpe and invoice_id.pa_edocument_id
                        and invoice_id.pa_edocument_id.state not in ('draft', 'cancel')):
                    raise UserError(
                        'No puede cancelar este documento, esta enviado a la sunat')
        return res

    def action_annul(self):
        action = self.env["ir.actions.actions"]._for_xml_id(
            "odoopanama_org.action_view_account_move_annul")
        return action

    def button_annul(self):
        self.with_context(allow_draft_from_annul=True).button_cancel()
        self.write({'annul': True, 'state': 'annul'})
        for invoice_id in self:
            if (invoice_id.is_cpe and invoice_id.pa_edocument_id
                    and invoice_id.pa_edocument_id.state not in ["draft"]):
                invoice_date = invoice_id.pa_invoice_date or invoice_id.invoice_date
                if isinstance(invoice_date, str):
                    invoice_date = fields.Datetime.from_string(invoice_date)
                elif isinstance(invoice_date, date):
                    invoice_date = fields.Datetime.to_datetime(invoice_date)
                invoice_date = fields.Datetime.context_timestamp(
                    self.with_context(tz='UTC'), invoice_date)
                today = fields.Datetime.context_timestamp(
                    self.with_context(tz='UTC'), fields.Datetime.now())
                delta = today - invoice_date
                if delta.days > 7:
                    raise UserError(
                        "No puede anular este documento, solo se puede hacer dentro de los primeros 7 días."
                        "contadas a partir del día siguiente de la fecha consignada en el CDR (constancia de recepción)."
                        "\nPara cancelar este Documento emita una Nota de Crédito.")

                voided_id = self.env['odoopanama.cpe'].get_cpe_async('ra', invoice_id)
                invoice_id.pa_voided_id = voided_id.id

                if not invoice_id.pa_voided_id:
                    voided_id = self.env['odoopanama.cpe'].get_cpe_async('ra', voided_id)
                    invoice_id.pa_voided_id = voided_id.id
                else:
                    pa_voided_id = invoice_id.pa_voided_id
                if invoice_id.company_id.pe_is_sync:
                    pa_voided_id.generate_cpe()
                    if (invoice_id.journal_id.is_synchronous
                            or invoice_id.journal_id.l10n_latam_document_type_id.code == '01'):
                        if not self.env.context.get('is_pos_invoice'):
                            pa_voided_id.action_send()
                else:
                    pa_voided_id.generate_cpe()
        return True

    def button_draft(self):
        res = super().button_draft()
        if not self.env.context.get('allow_draft_from_annul'):
            if self.filtered(
                    lambda inv: inv.pa_edocument_id
                    and (inv.pa_edocument_id.state in ['send', 'verify', 'done'])
                    and inv.journal_id.is_cpe):
                raise UserError(
                    "Este documento ha sido informado a la DGI no se puede cambiar a borrador")
            self.write({'annul': False})
        return res

    def action_invoice_sent(self):
        res = super().action_invoice_sent()
        self.ensure_one()
        if self.journal_id.is_cpe and self.pa_edocument_id:
            template = self.env.ref(
                'odoopanama_org.email_template_edi_invoice_cpe2', False)
            attachment_ids = []
            attach = {}
            result_pdf = self.env['ir.actions.report']._render_qweb_pdf(
                'account.report_invoice', self.id)[0]
            attach['name'] = '%s.pdf' % self.pa_edocument_id.get_document_name()
            attach['type'] = 'binary'
            attach['datas'] = encodebytes(result_pdf)
            attach['res_model'] = 'mail.compose.message'
            attachment_id = self.env['ir.attachment'].create(attach)
            attachment_ids.append(attachment_id.id)
            vals = {}
            vals['default_use_template'] = bool(template)
            vals['default_template_id'] = template and template.id or False
            vals['default_attachment_ids'] = [(6, 0, attachment_ids)]
            res['context'].update(vals)
        return res

    def get_public_cpe(self):
        self.ensure_one()
        res = {}
        if self.journal_id.is_cpe and self.pa_edocument_id:
            result_pdf, type = self.env['ir.actions.report']._get_report_from_name(
                'account.report_invoice').render_qweb_pdf(self.ids)
            res['datas_invoice'] = str(encodebytes(result_pdf), "utf-8")
            res['name'] = self.pa_edocument_id.get_document_name()
        return res

    @api.onchange('partner_id', 'company_id')
    def _onchange_partner_id(self):
        res = super(AccountMove, self)._onchange_partner_id()
        journal_type = TYPE2JOURNAL.get(self.move_type)
        if not journal_type:
            return res
        journal = self.env['account.journal']
        if not all((self.partner_id, self.env.context.get('force_pe_journal'))):
            return res
        return res

    def _get_starting_sequence(self):
        journal = self.journal_id
        if (journal and journal.l10n_latam_use_documents
                and self.env.company.country_id.code == "PA"):
            return self._l10n_pe_cpe_get_formatted_sequence()
        return super(AccountMove, self)._get_starting_sequence()

    def _l10n_pe_cpe_get_formatted_sequence(self, number=0):
        return "{}-00000001".format(self.journal_id.code)

    @api.onchange('l10n_latam_document_type_id', 'l10n_latam_document_number')
    def _inverse_l10n_latam_document_number(self):
        from_reversed = self.filtered(
            lambda x: x.from_wizard_revert and x.name != '/' and not x._get_last_sequence(True))
        super(AccountMove, self - from_reversed)._inverse_l10n_latam_document_number()
        for rec in self.filtered(lambda x: x.name != '/'):
            if not rec.l10n_latam_document_number:
                rec.l10n_latam_document_number = rec.name
                continue
            rec.name = rec.l10n_latam_document_number
        self._set_sequence_from_revert()
        if self.l10n_latam_document_type_id.code == '03':
            self.pa_dgi_destiny_operation = '2'

    def _set_sequence_from_revert(self):
        for rec in self.filtered(lambda x: x.from_wizard_revert and x.name == '/'):
            rec._set_next_sequence()

    def _get_last_sequence_domain(self, relaxed=False):
        where_string, param = super(AccountMove, self)._get_last_sequence_domain(relaxed)
        if not self.date or not self.journal_id:
            return where_string, param
        if self.company_id.country_id.code == "PE" and self.l10n_latam_use_documents:
            if self.move_type in ('out_refund', 'out_invoice'):
                where_string = where_string.replace(
                    'AND sequence_prefix !~ %(anti_regex)s', '')
                where_string += (
                    ' AND l10n_latam_document_type_id = %(l10n_latam_document_type_id)s'
                    ' AND company_id = %(company_id)s'
                    " AND move_type IN ('out_invoice', 'out_refund')")
            param['company_id'] = self.company_id.id or False
            param['l10n_latam_document_type_id'] = self.l10n_latam_document_type_id.id or 0
        return where_string, param


# ── account.debit.note (de odoopanama_org_origin) ─────────────────────────────
class AccountDebitNote(models.TransientModel):
    _inherit = 'account.debit.note'

    def _prepare_default_values(self, move):
        default_values = super(AccountDebitNote, self)._prepare_default_values(move)
        if default_values['debit_origin_id']:
            debit_origin_id = self.env['account.move'].browse(default_values['debit_origin_id'])
            document_type, invoice_date, number = self.get_data_from_origin_debit_note_move_id(
                debit_origin_id)
            default_values.update({
                'origin_l10n_latam_document_type_id': document_type,
                'origin_number': number,
                'origin_invoice_date': invoice_date,
            })
        return default_values

    @staticmethod
    def get_data_from_origin_debit_note_move_id(origin_move_id):
        document_type = False
        invoice_date = False
        number = False
        if origin_move_id and origin_move_id.l10n_latam_document_type_id:
            if origin_move_id.payment_reference:
                number = origin_move_id.payment_reference.replace(' ', '')
            elif origin_move_id.ref:
                number = origin_move_id.ref.replace(' ', '')
            else:
                number = ''
            document_type = origin_move_id.l10n_latam_document_type_id.id
            invoice_date = origin_move_id.invoice_date
        return document_type, invoice_date, number


# ── account.move.line (fusión de base + cpe) ──────────────────────────────────
class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    # de odoopanama_org_base
    amount_discount = fields.Float("Amount Discount", compute="_compute_amount_discount")
    pa_invoice_ids = fields.Many2many(
        'account.move', 'pa_account_invoice_line_invoice_rel',
        'line_id', 'move_id', string="Invoices lines", copy=False, readonly=True)
    pa_invoice_id = fields.Many2one(
        'account.move', string="Invoices", copy=False, readonly=True)

    # de odoopanama_org_cpe
    pe_charge_amount = fields.Float('Charge Amount', compute='get_pe_charge_amount')

    @api.depends('price_unit', 'discount', 'move_id.currency_id')
    def _compute_amount_discount(self):
        for line in self:
            price = line.price_unit * (line.discount or 0.0) / 100.0
            amount_discount = line.tax_ids.compute_all(
                price, line.move_id.currency_id, line.quantity,
                line.product_id, line.move_id.partner_id)
            line.amount_discount = amount_discount['total_excluded']

    @api.depends('price_unit', 'tax_ids', 'discount')
    def get_pe_charge_amount(self):
        for line in self:
            pe_charge_amount = 0.0
            if line.tax_ids.filtered(lambda tax: tax.pa_is_charge is True):
                price_unit = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
                taxes = line.tax_ids.with_context(round=False).compute_all(
                    price_unit, line.move_id.currency_id, 1,
                    line.product_id, line.move_id.partner_id).get('taxes', [])
                for tax_val in taxes:
                    tax = self.env['account.tax'].browse(tax_val.get('id'))
                    if tax.pa_is_charge:
                        pe_charge_amount += tax_val.get('amount', 0.0)
            line.pe_charge_amount = pe_charge_amount

    def get_price_unit(self, all=False):
        self.ensure_one()
        price_unit = self.price_unit
        if all:
            price_unit = self.price_unit * (1 - (self.discount or 0.0) / 100.0)
            tax_ids = self.tax_ids
        res = tax_ids.with_context(round=False).compute_all(
            price_unit, self.move_id.currency_id, 1, self.product_id, self.move_id.partner_id)
        return res
