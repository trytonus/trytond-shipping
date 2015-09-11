# -*- coding: utf-8 -*-
"""
    shipment.py

"""
from trytond.model import fields, ModelView
from trytond.pool import PoolMeta, Pool
from trytond.wizard import Wizard, StateView, Button, StateTransition
from trytond.pyson import Eval, Or
from trytond.transaction import Transaction

__metaclass__ = PoolMeta
__all__ = [
    'ShipmentOut', 'StockMove', 'GenerateShippingLabelMessage',
    'GenerateShippingLabel', 'ShippingCarrierSelector',
    'ShippingLabelNoModules', 'Package'
]

STATES = {
    'readonly': Eval('state') == 'done',
}


class Package:
    __name__ = 'stock.package'

    tracking_number = fields.Char('Tracking Number')

    weight = fields.Function(
        fields.Float(
            "Weight", digits=(16,  Eval('weight_digits', 2)),
            depends=['weight_digits'],
        ),
        'get_weight'
    )
    weight_uom = fields.Function(
        fields.Many2One('product.uom', 'Weight UOM'),
        'get_weight_uom'
    )
    weight_digits = fields.Function(
        fields.Integer('Weight Digits'), 'on_change_with_weight_digits'
    )

    computed_weight = fields.Function(
        fields.Float(
            "Computed Weight", digits=(16,  Eval('weight_digits', 2)),
            depends=['weight_digits'],
        ),
        'get_computed_weight'
    )

    override_weight = fields.Float(
        "Override Weight", digits=(16,  Eval('weight_digits', 2)),
        depends=['weight_digits'],
    )

    @fields.depends('weight_uom')
    def on_change_with_weight_digits(self, name=None):
        if self.weight_uom:
            return self.weight_uom.digits
        return 2

    def get_weight_uom(self, name):
        """
        Returns weight uom for the package from shipment
        """
        return self.shipment.weight_uom.id

    def get_weight(self, name):
        """
        Returns package weight if weight is not overriden
        otherwise returns overriden weight
        """
        return self.override_weight or self.get_computed_weight()

    def get_computed_weight(self, name=None):
        """
        Returns sum of weight associated with each move line
        """
        weight = sum(
            map(
                lambda move: move.get_weight(self.weight_uom, silent=True),
                self.moves
            )
        )
        return weight


class ShipmentOut:
    "Shipment Out"
    __name__ = 'stock.shipment.out'

    is_international_shipping = fields.Function(
        fields.Boolean("Is International Shipping"),
        'on_change_with_is_international_shipping'
    )

    weight = fields.Function(
        fields.Float(
            "Weight", digits=(16,  Eval('weight_digits', 2)),
            depends=['weight_digits'],
        ),
        'get_weight'
    )
    weight_uom = fields.Function(
        fields.Many2One('product.uom', 'Weight UOM'),
        'get_weight_uom'
    )
    weight_digits = fields.Function(
        fields.Integer('Weight Digits'), 'on_change_with_weight_digits'
    )

    tracking_number = fields.Char(
        'Tracking Number', states=STATES, depends=['state'])

    def get_weight(self, name=None):
        """
        Returns sum of weight associated with each move line
        """
        return sum(
            map(
                lambda move: move.get_weight(self.weight_uom, silent=True),
                self.outgoing_moves
            )
        )

    @fields.depends('weight_uom')
    def on_change_with_weight_digits(self, name=None):
        if self.weight_uom:
            return self.weight_uom.digits
        return 2

    @classmethod
    def __setup__(cls):
        super(ShipmentOut, cls).__setup__()
        cls._buttons.update({
            'label_wizard': {
                'invisible': Or(
                    (~Eval('state').in_(['packed', 'done'])),
                    (Eval('tracking_number') != '')
                ),
                'icon': 'tryton-executable',
            },
        })
        cls._error_messages.update({
            'no_shipments': 'There must be atleast one shipment.',
            'too_many_shipments':
                'The wizard can be called on only one shipment',
            'tracking_number_already_present':
                'Tracking Number is already present for this shipment.',
            'invalid_state': 'Labels can only be generated when the '
                'shipment is in Packed or Done states only',
            'wrong_carrier':
                'Carrier for selected shipment is not of %s',
            'no_packages': 'Shipment %s has no packages',
            'warehouse_address_missing': 'Warehouse address is missing',
        })

    @classmethod
    def copy(cls, shipments, default=None):
        if default is None:
            default = {}
        default = default.copy()
        default['tracking_number'] = None
        return super(ShipmentOut, cls).copy(shipments, default=default)

    @classmethod
    @ModelView.button_action('shipping.wizard_generate_shipping_label')
    def label_wizard(cls, shipments):
        if len(shipments) == 0:
            cls.raise_user_error('no_shipments')
        elif len(shipments) > 1:
            cls.raise_user_error('too_many_shipments')

    @fields.depends('delivery_address', 'warehouse')
    def on_change_with_is_international_shipping(self, name=None):
        """
        Return True if international shipping
        """
        from_address = self._get_ship_from_address()
        if self.delivery_address and from_address and \
           from_address.country and self.delivery_address.country and \
           from_address.country != self.delivery_address.country:
            return True
        return False

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

    def _get_ship_from_address(self):
        """
        Usually the warehouse from which you ship
        """
        if self.warehouse and not self.warehouse.address:
            return self.raise_user_error('warehouse_address_missing')
        return self.warehouse and self.warehouse.address

    def allow_label_generation(self):
        """
        Shipment must be in the right states and tracking number must not
        be present.
        """
        if self.state not in ('packed', 'done'):
            self.raise_user_error('invalid_state')

        if self.tracking_number:
            self.raise_user_error('tracking_number_already_present')

        return True


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


class ShippingCarrierSelector(ModelView):
    'View To Select Carrier'
    __name__ = 'shipping.label.start'

    carrier = fields.Many2One(
        "carrier", "Carrier", required=True
    )
    shipment = fields.Many2One(
        'stock.shipment.out', 'Shipment', required=True, readonly=True
    )
    override_weight = fields.Float("Override Weight", digits=(16,  2))
    no_of_packages = fields.Integer('Number of packages', readonly=True)


class GenerateShippingLabelMessage(ModelView):
    'Generate UPS Labels Message'
    __name__ = 'shipping.label.end'

    tracking_number = fields.Char("Tracking number", readonly=True)
    message = fields.Text("Message", readonly=True)
    attachments = fields.One2Many(
        'ir.attachment', None,
        'Attachments', readonly=True
    )
    cost = fields.Numeric("Cost", digits=(16, 2), readonly=True)
    cost_currency = fields.Many2One(
        'currency.currency', 'Cost Currency', required=True, readonly=True
    )


class ShippingLabelNoModules(ModelView):
    'Wizard State for No Modules'
    __name__ = 'shipping.label.no_modules'

    no_module_msg = fields.Text("Message", readonly=True)

    @staticmethod
    def default_no_module_msg():
        """
        Returns default message.
        """
        return (
            'No shipping module is available for label generation.'
            'Please install a shipping module first.'
        )


class GenerateShippingLabel(Wizard):
    'Generate Labels'
    __name__ = 'shipping.label'

    start = StateView(
        'shipping.label.start',
        'shipping.select_carrier_view_form',
        [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Continue', 'next', 'tryton-go-next'),
        ]
    )
    next = StateTransition()

    no_modules = StateView(
        'shipping.label.no_modules',
        'shipping.no_module_view_form',
        [
            Button('Ok', 'end', 'tryton-ok')
        ]
    )

    generate = StateView(
        'shipping.label.end',
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
            'invalid_state': (
                'Labels can only be generated when the shipment is in Packed or'
                ' Done states only'
            ),
            'no_packages': 'Shipment %s has no packages',
        })

    def _get_message(self):  # pragma: no cover
        """
        Returns message to be displayed on wizard
        """
        shipment = self.start.shipment
        message = 'Shipment labels have been generated via %s and saved as ' \
            'attachments for the shipment' % (
                shipment.carrier.carrier_cost_method.upper()
            )
        return message

    def default_start(self, data):
        Shipment = Pool().get('stock.shipment.out')

        shipment = Shipment(Transaction().context.get('active_id'))

        if shipment.allow_label_generation():
            values = {
                'shipment': shipment.id,
                'no_of_packages': len(shipment.packages)
            }

        if shipment.carrier:
            values.update({
                'carrier': shipment.carrier.id,
            })
        if shipment.packages:
            package_weights = [
                p.override_weight
                for p in shipment.packages if p.override_weight
            ]
            values['override_weight'] = sum(package_weights)

        return values

    def transition_next(self):
        Shipment = Pool().get('stock.shipment.out')

        shipment = Shipment(Transaction().context.get('active_id'))
        self.start.shipment = shipment

        if not shipment.packages:
            self._create_shipment_package()

        if self.start.override_weight:
            # Distribute weight equally
            per_package_weight = (
                self.start.override_weight / len(shipment.packages)
            )
            for package in shipment.packages:
                package.override_weight = per_package_weight
                package.save()

        return 'no_modules'

    def _create_shipment_package(self):
        """
        Create a single stock package for the whole shipment
        """
        Package = Pool().get('stock.package')
        ModelData = Pool().get('ir.model.data')

        shipment = self.start.shipment
        type_id = ModelData.get_id(
            "shipping", "shipment_package_type"
        )

        package, = Package.create([{
            'shipment': '%s,%d' % (shipment.__name__, shipment.id),
            'type': type_id,
            'moves': [('add', shipment.outgoing_moves)],
        }])
        return package

    def default_generate(self, data):
        shipment = self.update_shipment()
        shipment.save()

        tracking_number = self.generate_label(shipment)

        values = {
            'tracking_number': tracking_number,
            'message': self._get_message(),
            'attachments': self.get_attachments(),
            'cost': shipment.cost,
            'cost_currency': shipment.cost_currency.id,
        }

        return values

    def get_attachments(self):  # pragma: no cover
        """
        Returns list of attachments corresponding to shipment.
        """
        Attachment = Pool().get('ir.attachment')

        shipment = self.start.shipment

        # TODO: Show attachments related to this label.

        return map(
            int, Attachment.search([
                (
                    'resource', '=', '%s,%d' %
                    (shipment.__name__, shipment.id))
            ])
        )

    def update_shipment(self):
        """
        Returns unsaved instance of shipment.
        Downstream modules can update the field.
        """
        shipment = self.start.shipment
        shipment.carrier = self.start.carrier

        return shipment

    def generate_label(self, shipment):
        """
        Generate label for carrier chosen

        :param shipment: Active record used to generate label
        """
        method_name = 'make_%s_labels' % shipment.carrier.carrier_cost_method

        if not hasattr(shipment, method_name):
            self.raise_user_error(
                "This feature is not available"
            )

        return getattr(shipment, method_name)()
