# coding: utf-8
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api
from odoo.osv import expression



class ProductTemplate(models.Model):
    _inherit = 'product.template'

    pa_unspsc_code_id = fields.Many2one('panama.unspsc.code', 'UNSPSC Product Category', domain=[('applies_to', '=', 'product')],
        help='The UNSPSC code related to this product.  Used for edi in Panama')


class UomUom(models.Model):
    _inherit = 'uom.uom'

    pa_unspsc_code_id = fields.Many2one('panama.unspsc.code', 'UNSPSC Product Category',
                                                domain=[('applies_to', '=', 'uom')],
                                                help='The UNSPSC code related to this UoM. ')


class ProductCode(models.Model):
    """Product and UoM codes defined by UNSPSC
    Used by Panama
    """
    _name = 'panama.unspsc.code'
    _description = "Product and UOM Codes from UNSPSC"
    _rec_names_search = ['name', 'code']

    code = fields.Char('Code', required=True)
    name = fields.Char('Name', required=True, translate=True)
    applies_to = fields.Selection([('product', 'Product'), ('uom', 'UoM'),], required=True,
        help='Indicate if this code could be used in products or in UoM',)
    active = fields.Boolean()

    @api.depends('code')
    def _compute_display_name(self):
        for prod in self:
            prod.display_name = f"{prod.code} {prod.name or ''}"
