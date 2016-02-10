# -*- coding: utf-8 -*-
"""
    stock.py

"""
from trytond.pool import PoolMeta, Pool

__metaclass__ = PoolMeta
__all__ = ['StockMove']


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
            return 0

        if not self.product.weight:
            if silent:
                return 0
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

        return weight
