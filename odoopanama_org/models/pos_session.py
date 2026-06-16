# -*- coding: utf-8 -*-
from odoo import api, models


class AccountJournal(models.Model):
    _inherit = 'account.journal'

    def _load_pos_data(self, data):
        """Cargar journals de facturación para el POS"""
        domain = self._load_pos_data_domain(data)
        fields = self._load_pos_data_fields(data.get('pos.config', {}).get('data', [{}])[0].get('id'))

        journals = self.search_read(domain=domain, fields=fields)

        return {
            'data': journals,
            'fields': fields,
        }

    def _load_pos_data_domain(self, data):
        """Dominio para filtrar journals según configuración del POS"""
        config_id = data.get('pos.config', {}).get('data', [{}])[0].get('id')
        if config_id:
            config = self.env['pos.config'].browse(config_id)
            return [('id', 'in', config.invoice_journal_ids.ids)]
        return []

    def _load_pos_data_fields(self, config_id):
        """Campos a cargar para journals en el POS"""
        return ['id', 'name', 'l10n_latam_document_type_id', 'code', 'type']


class LatamDocumentType(models.Model):
    _inherit = 'l10n_latam.document.type'

    def _load_pos_data(self, data):
        """Cargar tipos de documento latam para el POS"""
        fields = self._load_pos_data_fields(data.get('pos.config', {}).get('data', [{}])[0].get('id'))
        document_types = self.search_read(domain=[], fields=fields)

        return {
            'data': document_types,
            'fields': fields,
        }

    def _load_pos_data_fields(self, config_id):
        """Campos a cargar para tipos de documento en el POS"""
        return ['id', 'name', 'code']


class LatamIdentificationType(models.Model):
    _inherit = 'l10n_latam.identification.type'

    def _load_pos_data(self, data):
        """Cargar tipos de identificación latam para el POS"""
        fields = self._load_pos_data_fields(data.get('pos.config', {}).get('data', [{}])[0].get('id'))
        identification_types = self.search_read(domain=[], fields=fields)

        return {
            'data': identification_types,
            'fields': fields,
        }

    def _load_pos_data_fields(self, config_id):
        """Campos a cargar para tipos de identificación en el POS"""
        return ['id', 'name', 'l10n_pa_vat_code']


class PosSession(models.Model):
    _inherit = 'pos.session'

    @api.model
    def _load_pos_data_models(self, config_id):
        """
        Agregar modelos adicionales necesarios para facturación electrónica
        """
        data = super()._load_pos_data_models(config_id)
        data += [
            'account.journal',
            'l10n_latam.document.type',
            'l10n_latam.identification.type',
        ]
        return data
