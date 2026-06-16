from odoo import api, fields, models

# ID del product.template que se quiere resaltar
HIGHLIGHTED_PRODUCT_TMPL_ID = 29


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    is_highlighted_product = fields.Boolean(
        string='Producto resaltado',
        compute='_compute_is_highlighted_product',
        store=False,
    )

    @api.depends('product_id')
    def _compute_is_highlighted_product(self):
        for line in self:
            line.is_highlighted_product = (
                line.product_id.product_tmpl_id.id == HIGHLIGHTED_PRODUCT_TMPL_ID
            )
