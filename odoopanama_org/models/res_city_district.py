# -*- coding: utf-8 -*-

from odoo import models, fields, api

class L10nPaResCityCorregimiento(models.Model):
    _name = 'l10n_pa.res.city.corregimiento'
    _description = 'Corregimiento'
    _order = 'name'

    name = fields.Char(translate=True)
    city_id = fields.Many2one('res.city', 'City')
    code = fields.Char(
        help='This code will help with the identification of each district '
        'in Panama.')
