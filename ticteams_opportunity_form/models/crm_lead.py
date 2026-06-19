# -*- coding: utf-8 -*-
from odoo import api, fields, models


class CrmLead(models.Model):
    _inherit = "crm.lead"

    # ------------------------------------------------------------------
    # Marker / metadata
    # ------------------------------------------------------------------
    x_diag_is_form = fields.Boolean(
        string="Desde el formulario de diagnóstico",
        help="Se activa automáticamente cuando la oportunidad se crea desde "
             "el formulario público de diagnóstico Odoo.",
        readonly=True,
        copy=False,
    )
    x_diag_submitted_on = fields.Datetime(
        string="Formulario enviado el",
        readonly=True,
        copy=False,
    )

    # ------------------------------------------------------------------
    # Step 1 - Industry
    # ------------------------------------------------------------------
    x_diag_industry = fields.Selection(
        selection=[
            ("distribution", "Distribución / Comercio"),
            ("manufacturing", "Fabricación / Producción"),
            ("professional_services", "Servicios profesionales"),
            ("retail", "Retail / Tienda"),
            ("construction", "Construcción"),
            ("health", "Salud"),
            ("other", "Otro"),
        ],
        string="Sector",
    )

    # ------------------------------------------------------------------
    # Step 2 - Company size
    # ------------------------------------------------------------------
    x_diag_company_size = fields.Selection(
        selection=[
            ("5_15", "De 5 a 15 personas"),
            ("16_30", "De 16 a 30 personas"),
            ("31_80", "De 31 a 80 personas"),
            ("81_200", "De 81 a 200 personas"),
            ("200_plus", "Más de 200 personas"),
        ],
        string="Tamaño de la empresa",
    )

    # ------------------------------------------------------------------
    # Step 3 - Current management (multi-select)
    # ------------------------------------------------------------------
    x_diag_mgmt_excel = fields.Boolean(string="Excel / hojas de cálculo")
    x_diag_mgmt_basic_accounting = fields.Boolean(string="Software contable básico")
    x_diag_mgmt_disconnected = fields.Boolean(string="Herramientas desconectadas")
    x_diag_mgmt_existing_erp = fields.Boolean(string="Tiene un ERP y quiere cambiar")
    x_diag_mgmt_none = fields.Boolean(string="Sin un sistema claro")
    x_diag_country = fields.Char(
        string="País de operación",
        help="Determina la configuración fiscal y la facturación electrónica.",
    )
    x_diag_migration_notes = fields.Text(
        string="Datos a migrar",
        help="Software actual y datos que el prospecto necesita migrar.",
    )

    # ------------------------------------------------------------------
    # Step 4 - Modules to configure (multi-select)
    # ------------------------------------------------------------------
    x_diag_mod_sales_crm = fields.Boolean(string="Ventas y CRM")
    x_diag_mod_inventory = fields.Boolean(string="Inventario y almacén")
    x_diag_mod_purchase = fields.Boolean(string="Compras y proveedores")
    x_diag_mod_accounting = fields.Boolean(string="Contabilidad y facturación")
    x_diag_mod_hr = fields.Boolean(string="Recursos humanos")
    x_diag_mod_manufacturing = fields.Boolean(string="Fabricación / MRP")
    x_diag_mod_projects = fields.Boolean(string="Proyectos")
    x_diag_mod_pos = fields.Boolean(string="Punto de venta")
    x_diag_mod_ecommerce = fields.Boolean(string="Sitio web / Comercio electrónico")
    x_diag_mod_other = fields.Boolean(string="Otros módulos")

    # ------------------------------------------------------------------
    # Step 5 - Custom development
    # ------------------------------------------------------------------
    x_diag_custom_modules = fields.Selection(
        selection=[
            ("yes", "Sí, necesito módulos a medida"),
            ("maybe", "Quizás / aún no estoy seguro"),
            ("no", "No, Odoo estándar es suficiente"),
        ],
        string="Necesita módulos a medida",
    )
    x_diag_custom_modules_desc = fields.Text(string="Detalle del desarrollo a medida")

    # ------------------------------------------------------------------
    # Step 6 - Accounting & e-invoicing
    # ------------------------------------------------------------------
    x_diag_accounting_status = fields.Selection(
        selection=[
            ("developed", "Ya desarrollada / localizada"),
            ("partial", "Configurada parcialmente"),
            ("needs_dev", "Necesita desarrollarse"),
            ("none", "Aún no usa contabilidad"),
        ],
        string="Estado de la contabilidad",
    )
    x_diag_einvoice_provider = fields.Char(
        string="Proveedor de facturación electrónica",
        help="Proveedor de facturación electrónica actual o preferido.",
    )
    x_diag_fiscal_docs = fields.Text(
        string="Documentos fiscales necesarios",
        help="Facturas, notas de crédito, recibos por honorarios, etc.",
    )

    # ------------------------------------------------------------------
    # Step 7 - Point of Sale
    # ------------------------------------------------------------------
    x_diag_pos_count = fields.Integer(string="Cantidad de puntos de venta físicos")
    x_diag_pos_hardware = fields.Selection(
        selection=[
            ("yes", "Sí, necesita integración de hardware"),
            ("no", "No necesita hardware"),
            ("na", "No aplica"),
        ],
        string="Integración de hardware en el POS",
        help="Impresora de tickets, lector de códigos de barras, cajón de dinero, etc.",
    )

    # ------------------------------------------------------------------
    # Step 8 - Inventory & traceability
    # ------------------------------------------------------------------
    x_diag_multi_location = fields.Selection(
        selection=[
            ("yes", "Sí, varios almacenes / ubicaciones"),
            ("no", "No, una sola ubicación"),
        ],
        string="Múltiples ubicaciones",
    )
    x_diag_sku_range = fields.Selection(
        selection=[
            ("lt_100", "Menos de 100 SKU"),
            ("100_1000", "De 100 a 1.000 SKU"),
            ("1000_10000", "De 1.000 a 10.000 SKU"),
            ("gt_10000", "Más de 10.000 SKU"),
        ],
        string="Rango de productos / SKU",
    )
    x_diag_variants = fields.Selection(
        selection=[
            ("yes", "Sí, los productos tienen variantes"),
            ("no", "Sin variantes"),
        ],
        string="Variantes de producto",
    )
    x_diag_traceability = fields.Selection(
        selection=[
            ("none", "No necesita trazabilidad"),
            ("serial", "Por número de serie"),
            ("lot", "Por lote"),
            ("both", "Por serie y lote"),
        ],
        string="Trazabilidad",
    )
    x_diag_multi_currency = fields.Selection(
        selection=[
            ("yes", "Sí, opera con varias monedas"),
            ("no", "No, una sola moneda"),
        ],
        string="Multimoneda",
    )

    # ------------------------------------------------------------------
    # Step 9 - Integrations (multi-select)
    # ------------------------------------------------------------------
    x_diag_int_shopify = fields.Boolean(string="Shopify")
    x_diag_int_woocommerce = fields.Boolean(string="WooCommerce")
    x_diag_int_payment_gateway = fields.Boolean(string="Pasarela de pago")
    x_diag_int_other = fields.Boolean(string="Otra integración")
    x_diag_integration_notes = fields.Text(string="Detalle de la integración")

    # ------------------------------------------------------------------
    # Step 10 - Timeline
    # ------------------------------------------------------------------
    x_diag_timeline = fields.Selection(
        selection=[
            ("now", "Listo para empezar ya mismo"),
            ("1_2m", "Puede empezar en 1-2 meses"),
            ("3_6m", "Todo en orden en 3-6 meses"),
            ("evaluating", "Aún evaluando, sin fecha definida"),
        ],
        string="Plazo de implementación",
    )

    # ------------------------------------------------------------------
    # Step 11 - Budget
    # ------------------------------------------------------------------
    x_diag_budget = fields.Selection(
        selection=[
            ("5_10k", "USD $5.000 - $10.000"),
            ("10_15k", "USD $10.000 - $15.000"),
            ("15_25k", "USD $15.000 - $25.000"),
            ("not_sure", "Aún no lo sé"),
        ],
        string="Presupuesto estimado",
    )

    # ------------------------------------------------------------------
    # Step 12 - Main problem
    # ------------------------------------------------------------------
    x_diag_main_problem = fields.Text(
        string="Principal problema a resolver",
    )

    # ==================================================================
    # Spec used both to validate incoming answers and to build a readable
    # chatter summary. Keys are the JSON keys posted by the form.
    # ==================================================================
    @api.model
    def _diag_field_spec(self):
        """Return the list of accepted form keys and their field type.

        type: 'selection' | 'boolean' | 'char' | 'text' | 'integer'
        """
        return [
            ("x_diag_industry", "selection"),
            ("x_diag_company_size", "selection"),
            ("x_diag_mgmt_excel", "boolean"),
            ("x_diag_mgmt_basic_accounting", "boolean"),
            ("x_diag_mgmt_disconnected", "boolean"),
            ("x_diag_mgmt_existing_erp", "boolean"),
            ("x_diag_mgmt_none", "boolean"),
            ("x_diag_country", "char"),
            ("x_diag_migration_notes", "text"),
            ("x_diag_mod_sales_crm", "boolean"),
            ("x_diag_mod_inventory", "boolean"),
            ("x_diag_mod_purchase", "boolean"),
            ("x_diag_mod_accounting", "boolean"),
            ("x_diag_mod_hr", "boolean"),
            ("x_diag_mod_manufacturing", "boolean"),
            ("x_diag_mod_projects", "boolean"),
            ("x_diag_mod_pos", "boolean"),
            ("x_diag_mod_ecommerce", "boolean"),
            ("x_diag_mod_other", "boolean"),
            ("x_diag_custom_modules", "selection"),
            ("x_diag_custom_modules_desc", "text"),
            ("x_diag_accounting_status", "selection"),
            ("x_diag_einvoice_provider", "char"),
            ("x_diag_fiscal_docs", "text"),
            ("x_diag_pos_count", "integer"),
            ("x_diag_pos_hardware", "selection"),
            ("x_diag_multi_location", "selection"),
            ("x_diag_sku_range", "selection"),
            ("x_diag_variants", "selection"),
            ("x_diag_traceability", "selection"),
            ("x_diag_multi_currency", "selection"),
            ("x_diag_int_shopify", "boolean"),
            ("x_diag_int_woocommerce", "boolean"),
            ("x_diag_int_payment_gateway", "boolean"),
            ("x_diag_int_other", "boolean"),
            ("x_diag_integration_notes", "text"),
            ("x_diag_timeline", "selection"),
            ("x_diag_budget", "selection"),
            ("x_diag_main_problem", "text"),
        ]

    @api.model
    def _diag_sanitize_answers(self, answers):
        """Convert the raw JSON payload into a safe write() dict.

        Only whitelisted keys are accepted; values are coerced to the field
        type so a malicious payload cannot write arbitrary fields.
        """
        if not isinstance(answers, dict):
            return {}
        vals = {}
        for fname, ftype in self._diag_field_spec():
            if fname not in answers:
                continue
            raw = answers.get(fname)
            if ftype == "boolean":
                vals[fname] = bool(raw)
            elif ftype == "integer":
                try:
                    vals[fname] = int(raw or 0)
                except (TypeError, ValueError):
                    vals[fname] = 0
            elif ftype == "selection":
                valid = dict(self._fields[fname].selection)
                if raw in valid:
                    vals[fname] = raw
            else:  # char / text
                vals[fname] = (raw or "").strip()
        return vals

    def _diag_field_display(self, fname, ftype):
        """Return the human-readable value of a diagnosis field, or None."""
        field = self._fields[fname]
        value = self[fname]
        if not value:
            return None
        if ftype == "selection":
            return dict(field.selection).get(value, value)
        if ftype == "boolean":
            return "Sí"
        return value

    def _diag_build_summary(self):
        """Return an HTML summary of the diagnosis answers for the chatter."""
        self.ensure_one()
        rows = []
        for fname, ftype in self._diag_field_spec():
            value = self._diag_field_display(fname, ftype)
            if value is None:
                continue
            label = self._fields[fname].string
            rows.append(
                "<li><strong>%s:</strong> %s</li>" % (label, value)
            )
        if not rows:
            return ""
        return (
            "<p><strong>Respuestas del formulario de diagnóstico Odoo</strong></p>"
            "<ul>%s</ul>" % "".join(rows)
        )

    # ==================================================================
    # PDF report
    # ==================================================================
    def _diag_report_groups(self):
        """Return the diagnosis answers grouped into sections for the PDF.

        Each section is a dict: {"title": str, "rows": [(label, value), ...]}.
        Sections without any answered field are omitted.
        """
        self.ensure_one()
        spec = dict(self._diag_field_spec())
        sections = [
            ("Perfil de la empresa", [
                "x_diag_industry",
                "x_diag_company_size",
                "x_diag_country",
                "x_diag_multi_currency",
            ]),
            ("Gestión actual", [
                "x_diag_mgmt_excel",
                "x_diag_mgmt_basic_accounting",
                "x_diag_mgmt_disconnected",
                "x_diag_mgmt_existing_erp",
                "x_diag_mgmt_none",
                "x_diag_migration_notes",
            ]),
            ("Módulos a configurar", [
                "x_diag_mod_sales_crm",
                "x_diag_mod_inventory",
                "x_diag_mod_purchase",
                "x_diag_mod_accounting",
                "x_diag_mod_hr",
                "x_diag_mod_manufacturing",
                "x_diag_mod_projects",
                "x_diag_mod_pos",
                "x_diag_mod_ecommerce",
                "x_diag_mod_other",
            ]),
            ("Desarrollo a medida", [
                "x_diag_custom_modules",
                "x_diag_custom_modules_desc",
            ]),
            ("Contabilidad y facturación electrónica", [
                "x_diag_accounting_status",
                "x_diag_einvoice_provider",
                "x_diag_fiscal_docs",
            ]),
            ("Punto de venta", [
                "x_diag_pos_count",
                "x_diag_pos_hardware",
            ]),
            ("Inventario y trazabilidad", [
                "x_diag_multi_location",
                "x_diag_sku_range",
                "x_diag_variants",
                "x_diag_traceability",
            ]),
            ("Integraciones", [
                "x_diag_int_shopify",
                "x_diag_int_woocommerce",
                "x_diag_int_payment_gateway",
                "x_diag_int_other",
                "x_diag_integration_notes",
            ]),
            ("Plazo y presupuesto", [
                "x_diag_timeline",
                "x_diag_budget",
            ]),
            ("Principal problema a resolver", [
                "x_diag_main_problem",
            ]),
        ]
        result = []
        for title, fnames in sections:
            rows = []
            for fname in fnames:
                ftype = spec[fname]
                value = self._diag_field_display(fname, ftype)
                if value is None:
                    continue
                rows.append((self._fields[fname].string, value))
            if rows:
                result.append({"title": title, "rows": rows})
        return result
