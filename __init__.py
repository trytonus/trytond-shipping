# -*- coding: utf-8 -*-
"""
    __init__.py

    :copyright: (c) 2014-2015 by Openlabs Technologies & Consulting (P) Limited
    :license: BSD, see LICENSE for more details.
"""
from trytond.pool import Pool

from carrier import Carrier, CarrierConfig
from party import (
    Address, AddressValidationMsg, AddressValidationWizard,
    AddressValidationSuggestionView
)
from shipment import (
    ShipmentOut, StockMove, GenerateShippingLabelMessage, GenerateShippingLabel,
    ShippingCarrierSelector, ShippingLabelNoModules, Package
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
        Package,
        Sale,
        SaleLine,
        GenerateShippingLabelMessage,
        ShippingLabelNoModules,
        ShippingCarrierSelector,
        AddressValidationMsg,
        AddressValidationSuggestionView,
        module='shipping', type_='model'
    )
    Pool.register(
        GenerateShippingLabel,
        AddressValidationWizard,
        module='shipping', type_='wizard'
    )
