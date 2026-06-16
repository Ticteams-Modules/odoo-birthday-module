# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class AccountDebitNote(models.TransientModel):
    _inherit = "account.debit.note"



    def _prepare_default_values(self, move):
        res = super()._prepare_default_values(move)
        journal_id = move.journal_id.dedit_note_id.id or res.get('journal_id')
        journal = self.env['account.journal'].browse(journal_id)
        res.update({
            'journal_id': journal.id,
            'l10n_latam_document_type_id': journal.l10n_latam_document_type_id.id,
        })
        return res
