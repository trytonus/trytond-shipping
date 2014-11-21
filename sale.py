# -*- coding: utf-8 -*-
"""
    sale.py

    :copyright: (c) 2014 by Openlabs Technologies & Consulting (P) Limited
    :license: BSD, see LICENSE for more details.
"""
from decimal import Decimal

from trytond.model import fields
from trytond.pool import PoolMeta, Pool

__all__ = ['SaleLine', 'Sale']
__metaclass__ = PoolMeta


class Sale:
    "Sale"
    __name__ = 'sale.sale'

    carrier_logs = fields.One2Many(
        'carrier.log', 'sale', 'Carrier Logs', readonly=True
    )
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
        Returns sum of weight associated with each line
        """
        weight_uom = self._get_weight_uom()
        return self._get_package_weight(weight_uom)

    def _get_package_weight(self, uom):
        """
        Returns sum of weight associated with package
        """
        return sum(
            map(
                lambda line: line.get_weight(uom, silent=True),
                self.lines
            )
        )

    def add_carrier_log(self, log_data, carrier):
        """
        Save log for sale
        """
        CarrierLog = Pool().get('carrier.log')
        Config = Pool().get('carrier.configuration')

        if not Config(1).save_carrier_logs:
            return

        log, = CarrierLog.create([{
            'sale': self.id,
            'carrier': carrier,
            'log': log_data,
        }])
        return log


class SaleLine:
    'Sale Line'
    __name__ = 'sale.line'

    @classmethod
    def __setup__(cls):
        super(SaleLine, cls).__setup__()
        cls._error_messages.update({
            'weight_required': 'Weight is missing on the product %s',
        })

    def get_weight(self, weight_uom, silent=False):
        """
        Returns weight as required for carriers

        :param weight_uom: Weight uom used by carriers
        :param silent: Raise error if not silent
        """
        ProductUom = Pool().get('product.uom')

        if not self.product or self.quantity <= 0 or \
                self.product.type == 'service':
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
        if self.unit != self.product.default_uom:
            quantity = ProductUom.compute_qty(
                self.unit,
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
                weight_uom,
            )

        return Decimal(weight)
