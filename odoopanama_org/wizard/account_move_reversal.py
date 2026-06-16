# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class AccountMoveReversal(models.TransientModel):
	_inherit = "account.move.reversal"

	def _prepare_default_reversal(self, move):
		res = super()._prepare_default_reversal(move)
		journal_id = move.journal_id.credit_note_id.id or res.get('journal_id')
		journal = self.env['account.journal'].browse(journal_id)
		res.update({
			'journal_id': journal.id,
			'l10n_latam_document_type_id': journal.l10n_latam_document_type_id.id,
			'from_wizard_revert': True,
		})
		return res

	def reverse_moves(self, is_modify=False):
		res = super(AccountMoveReversal, self).reverse_moves(is_modify=is_modify)
		if self.env.context.get("is_pa_debit_note", False):
			invoice_domain = res['domain']
			if invoice_domain:
				del invoice_domain[0]
				res['domain'] = invoice_domain
		return res
