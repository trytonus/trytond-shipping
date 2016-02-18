# -*- coding: utf-8 -*-
"""
    __init__.py

"""
from trytond.pool import Pool

from carrier import Carrier, Service, CarrierService, BoxType, CarrierBoxType
from party import (
    Address, AddressValidationMsg, AddressValidationWizard,
    AddressValidationSuggestionView
)
from shipment import (
    ShipmentOut, GenerateShippingLabelMessage, GenerateShippingLabel,
    ShippingCarrierSelector, ShippingLabelNoModules, Package, ShipmentTracking,
)
from stock import StockMove
from sale import Sale, SaleLine, ReturnSale
from configuration import PartyConfiguration
from log import CarrierLog


def register():
    Pool.register(
        PartyConfiguration,
        Carrier,
        Service,
        CarrierService,
        BoxType,
        CarrierBoxType,
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
        ShipmentTracking,
        module='shipping', type_='model'
    )
    Pool.register(
        GenerateShippingLabel,
        AddressValidationWizard,
        ReturnSale,
        module='shipping', type_='wizard'
    )
