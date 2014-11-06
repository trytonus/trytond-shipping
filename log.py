# -*- coding: utf-8 -*-
"""
    log.py

    :copyright: (c) 2014 by Openlabs Technologies & Consulting (P) Limited
    :license: BSD, see LICENSE for more details.
"""
from trytond.model import ModelSQL, ModelView, fields
from trytond.pool import PoolMeta

__all__ = ['CarrierLog']
__metaclass__ = PoolMeta


class CarrierLog(ModelSQL, ModelView):
    "Carrier Log"
    __name__ = 'carrier.log'

    sale = fields.Many2One('sale.sale', 'Sale', readonly=True)
    shipment_out = fields.Many2One(
        'stock.shipment.out', 'Shipment Out', readonly=True
    )
    carrier = fields.Many2One(
        'carrier', 'Carrier', required=True, readonly=True
    )
    log = fields.Text('Log', required=True, readonly=True)
