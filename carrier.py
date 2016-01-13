# -*- coding: utf-8 -*-
"""
    carrier.py

"""
from decimal import Decimal

from trytond.pool import PoolMeta, Pool
from trytond.model import ModelSQL, ModelView, fields
from trytond.transaction import Transaction
from trytond.pyson import Eval, Or, Bool, Id

__all__ = [
    'Carrier', 'Service', 'CarrierService', 'BoxType', 'CarrierBoxType'
]
__metaclass__ = PoolMeta


class Carrier:
    "Carrier"
    __name__ = 'carrier'

    currency = fields.Many2One('currency.currency', 'Currency', required=True)

    tracking_numbers = fields.One2Many(
        "shipment.tracking", "carrier", "Tracking Numbers"
    )
    services = fields.Many2Many(
        "carrier.carrier-service", "carrier", "service", "Services",
        domain=[
            ('carrier_cost_method', '=', Eval('carrier_cost_method'))
        ], depends=['carrier_cost_method']
    )
    box_types = fields.Many2Many(
        "carrier.carrier-box-type", "carrier", "box_type", "Box Types",
        domain=['OR', [
            ('carrier_cost_method', '=', Eval('carrier_cost_method'))
        ], [
            ('carrier_cost_method', '=', None)
        ]], depends=['carrier_cost_method']
    )

    @staticmethod
    def default_currency():
        Company = Pool().get('company.company')

        company = Transaction().context.get('company')
        if company:
            return Company(company).currency.id

    def get_sale_price(self):
        if Transaction().context.get('ignore_carrier_computation'):
            return Decimal('0'), self.currency.id
        return super(Carrier, self).get_sale_price()


class Service(ModelSQL, ModelView):
    "Carrier Service"
    __name__ = 'carrier.service'

    carrier_cost_method = fields.Selection(
        [], "Carrier Cost Method", required=True, select=True
    )
    name = fields.Char("Name", required=True, select=True)
    code = fields.Char("Code", required=True, select=True)


class CarrierService(ModelSQL):
    "Carrier - Service"
    __name__ = "carrier.carrier-service"

    carrier = fields.Many2One(
        "carrier", "Carrier", ondelete="CASCADE", required=True, select=True
    )
    service = fields.Many2One(
        "carrier.service", "Service", ondelete="CASCADE", required=True,
        select=True
    )


class BoxType(ModelSQL, ModelView):
    "Carrier Box Type"
    __name__ = 'carrier.box_type'

    name = fields.Char('Name', required=True)
    carrier_cost_method = fields.Selection([(None, '')], 'Carrier Cost Method')
    code = fields.Char('Code', required=True)
    length = fields.Float('Length')
    width = fields.Float('Width')
    height = fields.Float('Height')
    distance_unit = fields.Many2One(
        'product.uom', 'Distance Unit', states={
            'required': Or(Bool(Eval('length')), Bool(
                Eval('width')), Bool(Eval('height')))
        },
        domain=[
            ('category', '=', Id('product', 'uom_cat_length'))
        ], depends=['length', 'width', 'height']
    )


class CarrierBoxType(ModelSQL):
    "Carrier - Box Type"
    __name__ = "carrier.carrier-box-type"

    carrier = fields.Many2One(
        "carrier", "Carrier", ondelete="CASCADE", required=True, select=True
    )
    box_type = fields.Many2One(
        "carrier.box_type", "Box Type", ondelete="CASCADE", required=True,
        select=True
    )
