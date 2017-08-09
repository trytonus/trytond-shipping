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

    active = fields.Boolean("Active?", select=True)

    # XXX: Pending for deprecation
    currency = fields.Many2One('currency.currency', 'Currency')

    #: A One2Many to `carrier.service` model, reflects which services
    #: are available for a carrier.
    services = fields.Many2Many(
        "carrier.carrier-service", "carrier", "service", "Services",
        domain=[
            ('carrier_cost_method', '=', Eval('carrier_cost_method'))
        ], depends=['carrier_cost_method']
    )

    #: A One2Many to `carrier.box_type` model, reflects which box types
    #: are available for a carrier.
    box_types = fields.Many2Many(
        "carrier.carrier-box-type", "carrier", "box_type", "Box Types",
        domain=['OR', [
            ('carrier_cost_method', '=', Eval('carrier_cost_method'))
        ], [
            ('carrier_cost_method', '=', None)
        ]], depends=['carrier_cost_method']
    )

    @staticmethod
    def default_active():
        return True

    @staticmethod
    def default_currency():
        Company = Pool().get('company.company')

        company = Transaction().context.get('company')
        if company:
            return Company(company).currency.id

    def get_sale_price(self):
        """
        Returns sale price for a carrier in following format:
            price, currency_id

        You can ignore the computation by passing `ignore_carrier_computation`
        variable in context, in that case it will always return sale price as
        zero.

        :Example:

        >>> with Transaction().set_context(ignore_carrier_computation=True):
        ...   sale.get_sale_price()
        Decimal('0'), 1
        """
        if Transaction().context.get('ignore_carrier_computation'):
            return Decimal('0'), self.currency.id
        return super(Carrier, self).get_sale_price()


class Service(ModelSQL, ModelView):
    "Carrier Service"
    __name__ = 'carrier.service'

    #: Same as `carrier.carrier_cost_method`.
    carrier_cost_method = fields.Selection(
        [], "Carrier Cost Method", required=True, select=True
    )

    #: Name of the service.
    name = fields.Char("Name", required=True, select=True)

    #: Code of the service.
    code = fields.Char("Code", required=True, select=True)

    @staticmethod
    def check_xml_record(records, values):
        return True


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

    #: Name of the box.
    name = fields.Char('Name', required=True)

    #: Same as `carrier.carrier_cost_method`.
    carrier_cost_method = fields.Selection([(None, '')], 'Carrier Cost Method')

    #: Code of the box.
    code = fields.Char('Code', readonly=True)

    #: Length of the box.
    length = fields.Float('Length')

    #: Width of the box.
    width = fields.Float('Width')

    #: Height of the box.
    height = fields.Float('Height')

    #: Measuring unit of length, height and width.
    distance_unit = fields.Many2One(
        'product.uom', 'Distance Unit', states={
            'required': Or(Bool(Eval('length')), Bool(
                Eval('width')), Bool(Eval('height')))
        },
        domain=[
            ('category', '=', Id('product', 'uom_cat_length'))
        ], depends=['length', 'width', 'height']
    )

    @staticmethod
    def check_xml_record(records, values):
        return True


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
