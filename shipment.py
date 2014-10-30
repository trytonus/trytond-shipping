# -*- coding: utf-8 -*-
"""
    shipment.py

    :copyright: (c) 2014 by Openlabs Technologies & Consulting (P) Limited
    :license: BSD, see LICENSE for more details.
"""
from decimal import Decimal

from trytond.model import fields, ModelView
from trytond.pool import PoolMeta, Pool
from trytond.wizard import Wizard, StateView, Button, StateTransition
from trytond.pyson import Eval
from trytond.transaction import Transaction

__metaclass__ = PoolMeta
__all__ = [
    'ShipmentOut', 'StockMove', 'GenerateShippingLabelMessage',
    'GenerateShippingLabel', 'ShippingCarrier'
]

STATES = {
    'readonly': Eval('state') == 'done',
}


class ShipmentOut:
    "Shipment Out"
    __name__ = 'stock.shipment.out'

    tracking_number = fields.Char('Tracking Number', states=STATES)

    carrier_logs = fields.One2Many(
        'carrier.log', 'shipment_out', 'Carrier Logs', readonly=True
    )
    package_weight = fields.Function(
        fields.Numeric("Package weight", digits=(16,  2)),
        'get_package_weight'
    )

    weight_uom = fields.Function(
        fields.Many2One('product.uom', 'Weight UOM'),
        'get_weight_uom'
    )

    computed_weight = fields.Function(
        fields.Numeric("Computed Weight", digits=(16,  2)),
        'get_computed_weight'
    )

    override_weight = fields.Numeric("Override Weight", digits=(16,  2))

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
        Returns package weight if weight is not overriden
        otherwise returns overriden weight
        """
        return self.override_weight or self.get_computed_weight()

    def get_computed_weight(self, name=None):
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

    def add_carrier_log(self, log_data, carrier):
        """
        Save log for shipment out
        """
        CarrierLog = Pool().get('carrier.log')
        Config = Pool().get('carrier.configuration')

        if not Config(1).save_carrier_logs:
            return

        log, = CarrierLog.create([{
            'shipment_out': self.id,
            'carrier': carrier,
            'log': log_data,
        }])
        return log


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

        return Decimal(weight)


class ShippingCarrier(ModelView):  # pragma: no cover
    'View To Select Carrier'
    __name__ = 'shipping.carrier'

    shipment = fields.Many2One(
        'stock.shipment.out', 'Shipment', required=True, readonly=True
    )
    carrier = fields.Many2One(
        "carrier", "Carrier", required=True, depends=['shipment']
    )
    cost = fields.Numeric("Cost", digits=(16, 2))
    cost_currency = fields.Many2One(
        'currency.currency', 'Cost Currency', required=True
    )

    @staticmethod
    def default_cost():
        return Decimal('0')

    @fields.depends('carrier', 'shipment', 'cost', 'cost_currency')
    def on_change_carrier(self):
        res = dict.fromkeys(['cost_currency', 'cost'])
        if self.carrier and self.shipment:
            self.shipment.carrier = self.carrier
            with Transaction().set_context(self.shipment.get_carrier_context()):
                cost, currency_id = self.carrier.get_sale_price()
                res['cost'] = cost
                res['cost_currency'] = currency_id
        return res


class GenerateShippingLabelMessage(ModelView):  # pragma: no cover
    'Generate UPS Labels Message'
    __name__ = 'generate.shipping.label.message'

    tracking_number = fields.Char("Tracking number", readonly=True)
    message = fields.Text("Message", readonly=True)


class GenerateShippingLabel(Wizard):  # pragma: no cover
    'Generate Labels'
    __name__ = 'generate.shipping.label'

    start = StateView(
        'shipping.carrier',
        'shipping.select_carrier_view_form',
        [
            Button('Continue', 'next', 'tryton-ok'),
        ]
    )
    next = StateTransition()

    generate = StateView(
        'generate.shipping.label.message',
        'shipping.generate_shipping_label_message_view_form',
        [
            Button('Ok', 'end', 'tryton-ok'),
        ]
    )

    @classmethod
    def __setup__(cls):
        super(GenerateShippingLabel, cls).__setup__()
        cls._error_messages.update({
            'tracking_number_already_present':
                'Tracking Number is already present for this shipment.',
            'invalid_state': 'Labels can only be generated when the '
                'shipment is in Packed or Done states only',
        })

    def _get_message(self):
        """
        Returns message to be displayed on wizard
        """
        message = 'Shipment labels have been generated via %s and saved as ' \
            'attachments for the shipment' % (
                self.start.shipment.carrier.carrier_cost_method.upper()
            )
        return message

    def validate_shipment(self):
        """
        Label can be genrated only for 1 shipment
        """
        Shipment = Pool().get('stock.shipment.out')

        try:
            shipment, = Shipment.browse(Transaction().context['active_ids'])
        except ValueError:
            self.raise_user_error(
                'This wizard can be called for only one shipment at a time'
            )

        if shipment.state not in ('packed', 'done'):
            self.raise_user_error('invalid_state')

        if shipment.tracking_number:
            self.raise_user_error('tracking_number_already_present')

        return shipment

    def default_start(self, data):
        shipment = self.validate_shipment()

        values = {
            'shipment': shipment.id,
            'is_done': (shipment.state == 'done')
        }

        if shipment.carrier:
            res = shipment.on_change_carrier()
            values.update({
                'carrier': shipment.carrier.id,
                'cost': res.get('cost'),
                'cost_currency': res.get('cost_currency')
            })
        return values

    def default_generate(self, data):  # pragma: no cover
        return {
            'tracking_number': self.generate_label(),
            'message': self._get_message()
        }

    def update_shipment(self):
        """
        Returns updated shipment
        """
        shipment = self.start.shipment
        shipment.carrier = self.start.carrier
        shipment.cost = self.start.cost
        shipment.cost_currency = self.start.cost_currency
        shipment.save()

        return shipment

    def generate_label(self):
        """
        Generate label for carrier chosen
        """
        shipment = self.update_shipment()

        method_name = 'make_%s_labels' % shipment.carrier.carrier_cost_method

        if not hasattr(shipment, method_name):
            self.raise_user_error(
                "This feature is not available"
            )

        return getattr(shipment, method_name)()

    def transition_next(self):
        return 'generate'
>>>>>>> Add general wizard to generate shipping lables #6059
