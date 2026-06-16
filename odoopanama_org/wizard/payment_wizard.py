from odoo import models, fields, api

class PaymentWizard(models.TransientModel):
    _name = 'payment.wizard'
    _description = 'Payment Method Wizard'

    payment_line_ids = fields.One2many(
        'payment.wizard.line', 'wizard_id', string='Payment Lines')

    def action_confirm(self):
        move_id = self.env.context.get('active_id')
        move = self.env['account.move'].browse(move_id)
        move.pa_payment_lines.unlink()
        new_lines = []
        for line in self.payment_line_ids:
            new_lines.append({
                'move_id': move.id,
                'amount': line.amount,
                'date': line.date,
                'pa_payment_method': line.pa_payment_method,
            })
        move.write({'pa_payment_lines': [(0, 0, line) for line in new_lines]})
        return {'type': 'ir.actions.act_window_close'}
    
    
class PaymentWizardLine(models.TransientModel):
    _name = 'payment.wizard.line'
    _description = 'Payment Wizard Line'

    wizard_id = fields.Many2one('payment.wizard', string='Wizard', required=True)
    amount = fields.Float(string="Monto", required=True)
    date = fields.Date(string="Fecha", required=True)
    pa_payment_method = fields.Selection(
        selection='_get_payment_methods', string='Método de pago para DGI', required=True)

    @api.model
    def _get_payment_methods(self):
        return self.env['account.move']._get_payment_methods()

