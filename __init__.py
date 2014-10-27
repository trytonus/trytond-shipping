# -*- coding: utf-8 -*-
"""
    __init__.py

    :copyright: (c) 2014 by Openlabs Technologies & Consulting (P) Limited
    :license: BSD, see LICENSE for more details.
"""
from trytond.pool import Pool

from carrier import Carrier
from shipment import ShipmentOut, StockMove
from sale import Sale, SaleLine


def register():
    Pool.register(
        Carrier,
        ShipmentOut,
        StockMove,
        Sale,
        SaleLine,
        module='shipping', type_='model'
    )
