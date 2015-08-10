# -*- coding: utf-8 -*-
"""
    __init__.py

"""
from trytond.pool import Pool

from carrier import Carrier
from party import (
    Address, AddressValidationMsg, AddressValidationWizard,
    AddressValidationSuggestionView
)
from shipment import (
    ShipmentOut, StockMove, GenerateShippingLabelMessage, GenerateShippingLabel,
    ShippingCarrierSelector, ShippingLabelNoModules, Package
)
from sale import Sale, SaleLine, ReturnSale
from configuration import PartyConfiguration
from log import CarrierLog


def register():
    Pool.register(
        PartyConfiguration,
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
        ReturnSale,
        module='shipping', type_='wizard'
    )
