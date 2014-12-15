# -*- coding: utf-8 -*-
"""
    __init__.py

    :copyright: (c) 2014 by Openlabs Technologies & Consulting (P) Limited
    :license: BSD, see LICENSE for more details.
"""
from trytond.pool import Pool

from carrier import Carrier, CarrierConfig
from party import Address
from shipment import (
    ShipmentOut, StockMove, GenerateShippingLabelMessage, GenerateShippingLabel,
    ShippingCarrierSelector, ShippingLabelNoModules
)
from sale import Sale, SaleLine
from log import CarrierLog


def register():
    Pool.register(
        CarrierConfig,
        Carrier,
        CarrierLog,
        Address,
        ShipmentOut,
        StockMove,
        Sale,
        SaleLine,
        GenerateShippingLabelMessage,
        ShippingLabelNoModules,
        ShippingCarrierSelector,
        module='shipping', type_='model'
    )
    Pool.register(
        GenerateShippingLabel,
        module='shipping', type_='wizard'
    )
