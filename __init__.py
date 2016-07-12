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
    ShippingCarrierSelector, SelectShippingRate
)
from stock import StockMove
from sale import Sale, SaleLine, ReturnSale, ApplyShippingStart, \
    ApplyShippingSelectRate, ApplyShipping
from configuration import PartyConfiguration
from log import CarrierLog
from manifest import ShippingManifest
from location import Location
from package import Package
from tracking import ShipmentTracking


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
        ShipmentTracking,
        ShippingManifest,
        ShipmentOut,
        StockMove,
        Package,
        Sale,
        SaleLine,
        ApplyShippingStart,
        ApplyShippingSelectRate,
        GenerateShippingLabelMessage,
        SelectShippingRate,
        ShippingCarrierSelector,
        AddressValidationMsg,
        AddressValidationSuggestionView,
        Location,
        module='shipping', type_='model'
    )
    Pool.register(
        GenerateShippingLabel,
        AddressValidationWizard,
        ReturnSale,
        ApplyShipping,
        module='shipping', type_='wizard'
    )
