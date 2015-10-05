# -*- coding: utf-8 -*-
"""
    sale.py

"""
import warnings
from trytond.model import fields
from trytond.pool import PoolMeta, Pool
from trytond.pyson import Eval
from trytond.transaction import Transaction

__all__ = ['SaleLine', 'Sale']
__metaclass__ = PoolMeta


class Sale:
    "Sale"
    __name__ = 'sale.sale'

    is_international_shipping = fields.Function(
        fields.Boolean("Is International Shipping"),
        'on_change_with_is_international_shipping'
    )
    package_weight = fields.Function(
        fields.Float(
            "Package weight", digits=(16,  Eval('weight_digits', 2)),
            depends=['weight_digits'],
        ),
        'get_package_weight'
    )

    total_weight = fields.Function(
        fields.Float(
            "Total weight", digits=(16,  Eval('weight_digits', 2)),
            depends=['weight_digits'],
        ),
        'get_total_weight'
    )

    weight_uom = fields.Function(
        fields.Many2One('product.uom', 'Weight UOM'),
        'get_weight_uom'
    )
    weight_digits = fields.Function(
        fields.Integer('Weight Digits'), 'on_change_with_weight_digits'
    )

    @classmethod
    def __setup__(cls):
        super(Sale, cls).__setup__()
        cls._error_messages.update({
            'warehouse_address_missing': 'Warehouse address is missing',
        })

    @fields.depends('weight_uom')
    def on_change_with_weight_digits(self, name=None):
        if self.weight_uom:
            return self.weight_uom.digits
        return 2

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
        warnings.warn(
            'Field package_weight is depricated, use total_weight instead',
            DeprecationWarning, stacklevel=2
        )
        weight_uom = self._get_weight_uom()
        return self._get_package_weight(weight_uom)

    def get_total_weight(self, name):
        """
        Returns sum of weight associated with each line
        """
        weight_uom = self._get_weight_uom()
        return self._get_total_weight(weight_uom)

    @fields.depends('party', 'shipment_address', 'warehouse')
    def on_change_with_is_international_shipping(self, name=None):
        """
        Return True if international shipping
        """
        from_address = self._get_ship_from_address()

        if self.shipment_address and from_address and \
           from_address.country and self.shipment_address.country and \
           from_address.country != self.shipment_address.country:
            return True
        return False

    def _get_package_weight(self, uom):
        """
        Returns sum of weight associated with package
        """
        warnings.warn(
            '_get_package_weight is depricated, use _get_total_weight instead',
            DeprecationWarning, stacklevel=2
        )
        return sum(
            map(
                lambda line: line.get_weight(uom, silent=True),
                self.lines
            )
        )

    def _get_total_weight(self, uom):
        """
        Returns sum of weight for given uom
        """
        return sum(
            map(
                lambda line: line.get_weight(uom, silent=True),
                self.lines
            )
        )

    def _get_ship_from_address(self):
        """
        Usually the warehouse from which you ship
        """
        if not self.warehouse.address:
            return self.raise_user_error('warehouse_address_missing')
        return self.warehouse and self.warehouse.address

    def add_shipping_line(self, shipment_cost, description):
        """
        This method takes shipping_cost and description as arguments and writes
        a shipping line. It deletes any previous shipping lines which have
        a shipment_cost.
        :param shipment_cost: The shipment cost calculated according to carrier
        :param description: Shipping line description
        """
        self.__class__.write([self], {
            'lines': [
                ('create', [{
                    'type': 'line',
                    'product': self.carrier.carrier_product.id,
                    'description': description,
                    'quantity': 1,  # XXX
                    'unit': self.carrier.carrier_product.sale_uom.id,
                    'unit_price': shipment_cost,
                    'shipment_cost': shipment_cost,
                    'amount': shipment_cost,
                    'taxes': [],
                    'sequence': 9999,  # XXX
                }]),
                ('delete', [
                    line for line in self.lines
                    if line.shipment_cost is not None
                ]),
            ]
        })

    def apply_product_shipping(self):
        """
        This method apply product(carrier) shipping.
        """
        Currency = Pool().get('currency.currency')

        with Transaction().set_context(self._get_carrier_context()):
            shipment_cost, currency_id = self.carrier.get_sale_price()

        shipment_cost = Currency.compute(
            Currency(currency_id), shipment_cost, self.currency
        )
        self.add_shipping_line(shipment_cost, self.carrier.rec_name)

    def get_shipping_rates(self, carrier):
        """
        Return list of tuples as:
            [
                (
                    <display method name>, <cost>, <currency>, <metadata>,
                    <write_vals>
                )
                ...
            ]
        """
        Currency = Pool().get('currency.currency')

        if carrier.carrier_cost_method == 'product':
            with Transaction().set_context(self._get_carrier_context()):
                cost, currency_id = carrier.get_sale_price()
            return [(
                carrier.rec_name,
                cost,
                Currency(currency_id),
                {},
                {'carrier': carrier.id},
            )]
        return []


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

        return weight


class ReturnSale:
    __name__ = 'sale.return_sale'

    def do_return_(self, action):
        Sale = Pool().get('sale.sale')
        action, data = super(ReturnSale, self).do_return_(action)

        Sale.write(Sale.browse(data['res_id']), {'carrier': None})

        return action, data
