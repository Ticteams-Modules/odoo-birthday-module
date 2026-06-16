# -*- coding: utf-8 -*-
from odoo import api, fields, models, _

class AccountTax(models.Model):
	_inherit = 'account.tax'

	pa_is_charge = fields.Boolean("Cargo")
	pa_is_retention_tax = fields.Boolean(
		"Impuesto de Retención (50%)",
		help="Marcar si este impuesto representa la retención del 50% de ITBMS "
		     "que aplica a clientes retenedores. Se agregará automáticamente "
		     "a las líneas de factura cuando el cliente sea retenedor al 50%."
	)
	pa_is_exemption_tax = fields.Boolean(
		"Impuesto de Exención",
		help="Marcar si este impuesto representa la exención de ITBMS "
		     "que aplica a clientes exentos. Se agregará automáticamente "
		     "a las líneas de factura cuando el cliente esté exento de ITBMS."
	)



