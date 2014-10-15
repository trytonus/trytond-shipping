# -*- coding: utf-8 -*-
"""
    shipment.py

    :copyright: (c) 2014 by Openlabs Technologies & Consulting (P) Limited
    :license: BSD, see LICENSE for more details.
"""
import math
from decimal import Decimal

from trytond.model import fields
from trytond.pool import PoolMeta, Pool
from trytond.pyson import Eval

__metaclass__ = PoolMeta
__all__ = ['ShipmentOut', 'StockMove']

STATES = {
    'readonly': Eval('state') == 'done',
}


class ShipmentOut:
    "Shipment Out"
    __name__ = 'stock.shipment.out'

    tracking_number = fields.Char('Tracking Number', states=STATES)

    package_weight = fields.Function(
        fields.Numeric("Package weight", digits=(16,  2)),
        'get_package_weight'
    )

    weight_uom = fields.Function(
        fields.Many2One('product.uom', 'Weight UOM'),
        'get_weight_uom'
    )

    def get_weight_uom(self, name):
        """
        Returns weight uom for the package
        """
        return self._get_weight_uom().id

    def _get_weight_uom(self):
        """
        Returns Pound as default value for uom

        Downstream module can override this method to change weight uom as per
        carrier
        """
        UOM = Pool().get('product.uom')

        return UOM.search([('symbol', '=', 'lb')])[0]

    def get_package_weight(self, name):
        """
        Returns sum of weight associated with each move line
        """
        weight_uom = self._get_weight_uom()
        return sum(
            map(
                lambda move: move.get_weight(weight_uom, silent=True),
                self.outgoing_moves
            )
        )


class StockMove:
    "Stock move"
    __name__ = "stock.move"

    @classmethod
    def __setup__(cls):
        super(StockMove, cls).__setup__()
        cls._error_messages.update({
            'weight_required':
                'Weight for product %s in stock move is missing',
        })

    def get_weight(self, weight_uom, silent=False):
        """
        Returns weight as required for carrier

        :param weight_uom: Weight uom used by carrier
        :param silent: Raise error if not silent
        """
        ProductUom = Pool().get('product.uom')

        if self.quantity <= 0:
            return Decimal('0')

        if not self.product.weight:
            if silent:
                return Decimal('0')
            self.raise_user_error(
                'weight_required',
                error_args=(self.product.name,)
            )

        # Find the quantity in the default uom of the product as the weight
        # is for per unit in that uom
        if self.uom != self.product.default_uom:
            quantity = ProductUom.compute_qty(
                self.uom,
                self.quantity,
                self.product.default_uom
            )
        else:
            quantity = self.quantity

        weight = self.product.weight * quantity

        # Compare product weight uom with the weight uom used by carrier
        # and calculate weight if botth are not same
        if self.product.weight_uom.symbol != weight_uom.symbol:
            weight = ProductUom.compute_qty(
                self.product.weight_uom,
                weight,
                weight_uom
            )
        return Decimal(math.ceil(weight))
