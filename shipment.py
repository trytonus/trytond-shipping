# -*- coding: utf-8 -*-
"""
    shipment.py

"""
from trytond.model import fields, ModelView, ModelSQL
from trytond.pool import PoolMeta, Pool
from trytond.wizard import Wizard, StateView, Button, StateTransition
from trytond.pyson import Eval, Or, Bool, Id
from trytond.transaction import Transaction

__metaclass__ = PoolMeta
__all__ = [
    'ShipmentOut', 'GenerateShippingLabelMessage',
    'GenerateShippingLabel', 'ShippingCarrierSelector',
    'ShippingLabelNoModules', 'Package', 'ShipmentTracking'
]


class Package:
    __name__ = 'stock.package'

    tracking_number = fields.Function(
        fields.Many2One('shipment.tracking', 'Tracking Number'),
        'get_tracking_number', searcher="search_tracking_number"
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

    available_box_types = fields.Function(
        fields.One2Many("carrier.box_type", None, "Available Box Types"),
        getter="on_change_with_available_box_types"
    )
    box_type = fields.Many2One(
        'carrier.box_type', 'Box Types', domain=[
            ('id', 'in', Eval('available_box_types'))
        ], depends=["available_box_types"]
    )

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

    @fields.depends("_parent_shipment", "_parent_shipment.carrier")
    def on_change_with_available_box_types(self, name=None):
        if self.shipment.carrier:
            return map(int, self.shipment.carrier.box_types)
        return []

    def _process_raw_label(self, data, **kwargs):
        "Downstream modules can use this method to process label image"
        return data

    def get_tracking_number(self, name):
        """
        Return first tracking number for this package
        """
        Tracking = Pool().get('shipment.tracking')

        tracking_numbers = Tracking.search([
            ('origin', '=', '%s,%s' % (self.__name__, self.id)),
        ], limit=1)

        return tracking_numbers and tracking_numbers[0].id or None

    @classmethod
    def search_tracking_number(cls, name, clause):
        Tracking = Pool().get('shipment.tracking')

        tracking_numbers = Tracking.search([
            ('origin', 'like', 'stock.package,%'),
            ('tracking_number', ) + tuple(clause[1:])
        ])
        return [
            ('id', 'in', map(lambda x: x.origin.id, tracking_numbers))
        ]

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
        return sum(map(
            lambda move: move.get_weight(self.weight_uom, silent=True),
            self.moves
        ))

    @staticmethod
    def default_type():
        ModelData = Pool().get('ir.model.data')
        return ModelData.get_id(
            'shipping', 'shipment_package_type'
        )

    @staticmethod
    def default_distance_unit():
        ModelData = Pool().get('ir.model.data')
        return ModelData.get_id(
            'product', 'uom_inch'
        )


class ShipmentOut:
    "Shipment Out"
    __name__ = 'stock.shipment.out'

    is_international_shipping = fields.Function(
        fields.Boolean("Is International Shipping"),
        'on_change_with_is_international_shipping'
    )

    has_exception = fields.Function(
        fields.Boolean("Has Expection"), 'get_has_exception'
    )

    weight = fields.Function(
        fields.Float(
            "Weight", digits=(16, Eval('weight_digits', 2)),
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

    tracking_number = fields.Many2One(
        'shipment.tracking', 'Tracking Number', select=True,
        states={'readonly': Eval('state') == 'done'}, depends=['state']
    )

    shipping_instructions = fields.Text(
        'Shipping Instructions', states={
            'readonly': Eval('state').in_(['cancel', 'done']),
        }, depends=['state']
    )

    available_carrier_services = fields.Function(
        fields.One2Many("carrier.service", None, "Available Carrier Services"),
        getter="on_change_with_available_carrier_services"
    )
    carrier_service = fields.Many2One(
        "carrier.service", "Carrier Service", domain=[
            ('id', 'in', Eval('available_carrier_services'))
        ], depends=['available_carrier_services', 'state']
    )
    carrier_cost_method = fields.Function(
        fields.Char('Carrier Cost Method'),
        "on_change_with_carrier_cost_method"
    )
    shipping_manifest = fields.Many2One(
        "shipping.manifest", "Shipping Manifest", readonly=True, select=True
    )

    def get_has_exception(self, name):
        """
        Returs True if sale has exception
        """
        for sale in self.sales:
            if sale.has_channel_exception:
                return True
        return False

    @fields.depends("carrier")
    def on_change_with_carrier_cost_method(self, name=None):
        if self.carrier:
            return self.carrier.carrier_cost_method

    @fields.depends('carrier')
    def on_change_with_available_carrier_services(self, name=None):
        if self.carrier:
            return map(int, self.carrier.services)
        return []

    def on_change_inventory_moves(self):
        with Transaction().set_context(ignore_carrier_computation=True):
            return super(ShipmentOut, self).on_change_inventory_moves()

    def get_weight(self, name=None):
        """
        Returns sum of weight associated with each move line
        """
        return sum(map(
            lambda move: move.get_weight(self.weight_uom, silent=True),
            self.outgoing_moves
        ))

    @fields.depends('weight_uom')
    def on_change_with_weight_digits(self, name=None):
        if self.weight_uom:
            return self.weight_uom.digits
        return 2

    @classmethod
    def __setup__(cls):
        super(ShipmentOut, cls).__setup__()
        readonly_when_done = {
            'readonly': Eval('state') == 'done',
        }
        cls.carrier.states = readonly_when_done
        cls.carrier_service.states = readonly_when_done
        cls._buttons.update({
            'label_wizard': {
                'invisible': Or(
                    (~Eval('state').in_(['packed', 'done'])),
                    (Bool(Eval('tracking_number')))
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
    @ModelView.button_action('shipping.wizard_generate_shipping_label')
    def label_wizard(cls, shipments):
        if len(shipments) == 0:
            cls.raise_user_error('no_shipments')
        elif len(shipments) > 1:
            cls.raise_user_error('too_many_shipments')

    @classmethod
    def copy(cls, shipments, default=None):
        if default is None:
            default = {}
        default = default.copy()
        default['tracking_number'] = None
        return super(ShipmentOut, cls).copy(shipments, default=default)

    @fields.depends('delivery_address', 'warehouse')
    def on_change_with_is_international_shipping(self, name=None):
        """
        Return True if international shipping
        """
        from_address = self._get_ship_from_address(silent=True)
        if self.delivery_address and from_address and \
           from_address.country and self.delivery_address.country and \
           from_address.country != self.delivery_address.country:
            return True
        return False

    def get_weight_uom(self, name):
        """
        Returns weight uom for the shipment
        """
        ModelData = Pool().get('ir.model.data')

        return ModelData.get_id('product', 'uom_pound')

    def _get_ship_from_address(self, silent=False):
        """
        Usually the warehouse from which you ship
        """
        if not self.warehouse.address and not silent:
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

    def _create_default_package(self, box_type=None):
        """
        Create a single stock package for the whole shipment
        """
        Package = Pool().get('stock.package')

        package, = Package.create([{
            'shipment': '%s,%d' % (self.__name__, self.id),
            'box_type': box_type and box_type.id,
            'moves': [('add', self.outgoing_moves)],
        }])
        return package

    def get_shipping_rates(self, carriers=None, silent=False):
        """
        Gives a list of rates from carriers provided. If no carriers provided,
        return rates from all the carriers.

        List contains dictionary with following minimum keys:
            [
                {
                    'display_name': Name to display,
                    'carrier_service': carrier.service active record,
                    'cost': cost,
                    'cost_currency': currency.currency active repord,
                    'carrier': carrier active record,
                }..
            ]
        """
        Carrier = Pool().get('carrier')

        if carriers is None:
            carriers = Carrier.search([])

        rates = []
        for carrier in carriers:
            rates.extend(self.get_shipping_rate(carrier, silent))
        return rates

    def get_shipping_rate(self, carrier, carrier_service=None, silent=False):
        """
        Gives a list of rates from provided carrier and carrier service.

        List contains dictionary with following minimum keys:
            [
                {
                    'display_name': Name to display,
                    'carrier_service': carrier.service active record,
                    'cost': cost,
                    'cost_currency': currency.currency active repord,
                    'carrier': carrier active record,
                }..
            ]
        """
        Company = Pool().get('company.company')

        if carrier.carrier_cost_method == 'product':
            currency = Company(Transaction().context['company']).currency
            rate_dict = {
                'display_name': carrier.rec_name,
                'carrier_service': carrier_service,
                'cost': carrier.carrier_product.list_price,
                'cost_currency': currency,
                'carrier': carrier,
            }
            return [rate_dict]

        return []

    def apply_shipping_rate(self, rate):
        """
        This method applies shipping rate. Rate is a dictionary with
        following minimum keys:

            {
                'display_name': Name to display,
                'carrier_service': carrier.service active record,
                'cost': cost,
                'cost_currency': currency.currency active repord,
                'carrier': carrier active record,
            }
        """
        Currency = Pool().get('currency.currency')

        shipment_cost = rate['cost_currency'].round(rate['cost'])
        if self.cost_currency != rate['cost_currency']:
            shipment_cost = Currency.compute(
                rate['cost_currency'], shipment_cost, self.cost_currency
            )

        self.cost = shipment_cost
        self.cost_currency = self.cost_currency
        self.carrier = rate['carrier']
        self.carrier_service = rate['carrier_service']
        self.save()

    def generate_shipping_labels(self, **kwargs):
        """
        Generates shipment label for shipment and saves labels,
        tracking numbers.
        """
        self.raise_user_error(
            "Shipping label generation feature is not available"
        )


class ShippingCarrierSelector(ModelView):
    'View To Select Carrier'
    __name__ = 'shipping.label.start'

    carrier = fields.Many2One(
        "carrier", "Carrier", required=True
    )
    override_weight = fields.Float("Override Weight", digits=(16,  2))
    no_of_packages = fields.Integer('Number of packages', readonly=True)
    box_type = fields.Many2One(
        "carrier.box_type", "Box Type", required=True, domain=[
            ('id', 'in', Eval("available_box_types"))
        ], depends=["available_box_types"]
    )

    shipping_instructions = fields.Text('Shipping Instructions', readonly=True)
    carrier_service = fields.Many2One(
        "carrier.service", "Carrier Service", domain=[
            ('id', 'in', Eval("available_carrier_services"))
        ], depends=["available_carrier_services"]
    )

    available_box_types = fields.Function(
        fields.One2Many("carrier.box_type", None, 'Available Box Types'),
        getter="on_change_with_available_box_types"
    )
    available_carrier_services = fields.Function(
        fields.One2Many("carrier.service", None, 'Available Carrier Services'),
        getter="on_change_with_available_carrier_services"
    )

    @fields.depends("carrier")
    def on_change_with_available_box_types(self, name=None):
        if self.carrier:
            return map(int, self.carrier.box_types)
        return []

    @fields.depends("carrier")
    def on_change_with_available_carrier_services(self, name=None):
        if self.carrier:
            return map(int, self.carrier.services)
        return []


class GenerateShippingLabelMessage(ModelView):
    'Generate Labels Message'
    __name__ = 'shipping.label.end'

    tracking_number = fields.Many2One(
        "shipment.tracking", "Tracking number", readonly=True
    )
    message = fields.Text("Message", readonly=True)
    attachments = fields.One2Many(
        'ir.attachment', None, 'Attachments', readonly=True
    )
    cost = fields.Numeric("Cost", digits=(16, 2), readonly=True)
    cost_currency = fields.Many2One(
        'currency.currency', 'Cost Currency', readonly=True
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

    #: This is the first state of wizard to generate shipping label.
    #: It asks for carrier, carrier_service, box_type and override weight,
    #: once entered, it move to `next` transition where it saves all the
    #: values on shipment.
    start = StateView(
        'shipping.label.start',
        'shipping.select_carrier_view_form',
        [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Continue', 'next', 'tryton-go-next'),
        ]
    )

    #: Transition saves values from `start` state to the shipment.
    next = StateTransition()

    #: This state is showed up when shipping provider doesnt give facility
    #: to generate labels.
    no_modules = StateView(
        'shipping.label.no_modules',
        'shipping.no_module_view_form',
        [
            Button('Ok', 'end', 'tryton-ok')
        ]
    )

    #: Transition generates shipping labels.
    generate_labels = StateTransition()

    #: State shows the generated label, tracking number, cost and cost
    #: currency.
    generate = StateView(
        'shipping.label.end',
        'shipping.generate_shipping_label_message_view_form',
        [
            Button('Ok', 'end', 'tryton-ok'),
        ]
    )

    @property
    def shipment(self):
        "Gives the active shipment."
        Shipment = Pool().get('stock.shipment.out')
        return Shipment(Transaction().context.get('active_id'))

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

    def default_start(self, data):
        """Fill the default values for `start` state.
        """
        if self.shipment.allow_label_generation():
            values = {
                'no_of_packages': len(self.shipment.packages),
                'shipping_instructions': self.shipment.shipping_instructions,
            }

        if self.shipment.carrier:
            values.update({
                'carrier': self.shipment.carrier.id,
            })
        if self.shipment.packages:
            package_weights = [
                p.override_weight
                for p in self.shipment.packages if p.override_weight
            ]
            values['override_weight'] = sum(package_weights)

        if self.shipment.carrier_service:
            values['carrier_service'] = self.shipment.carrier_service.id

        return values

    def transition_next(self):
        Company = Pool().get('company.company')

        shipment = self.shipment
        company = Company(Transaction().context['company'])
        shipment.carrier = self.start.carrier
        shipment.cost_currency = company.currency
        shipment.carrier_service = self.start.carrier_service
        shipment.save()

        if not shipment.packages:
            shipment._create_default_package(self.start.box_type)

        default_values = self.default_start({})
        per_package_weight = None
        if self.start.override_weight and \
                default_values['override_weight'] != self.start.override_weight:
            # Distribute weight equally
            per_package_weight = (
                self.start.override_weight / len(shipment.packages)
            )

        for package in shipment.packages:
            if per_package_weight:
                package.override_weight = per_package_weight
            if self.start.box_type != package.box_type:
                package.box_type = self.start.box_type
            package.save()

        return 'no_modules'

    def transition_generate_labels(self):
        "Generates shipping labels from data provided by earlier states"
        self.shipment.generate_shipping_labels()

        return "generate"

    def get_attachments(self):  # pragma: no cover
        """
        Returns list of attachments corresponding to shipment.
        """
        Attachment = Pool().get('ir.attachment')

        return map(int, Attachment.search([
            ('resource', '=', '%s,%d' %
                (self.shipment.__name__, self.shipment.id))
            ])
        )

    def get_message(self):
        """
        Returns message to be displayed on wizard
        """
        message = 'Shipment labels have been generated via %s and saved as ' \
            'attachments for the shipment' % (
                self.shipment.carrier.carrier_cost_method.upper()
            )
        return message

    def default_generate(self, data):
        return {
            'tracking_number': self.shipment.tracking_number and
            self.shipment.tracking_number.id,
            'message': self.get_message(),
            'attachments': self.get_attachments(),
            'cost': self.shipment.cost,
            'cost_currency': self.shipment.cost_currency.id,
        }


class ShipmentTracking(ModelSQL, ModelView):
    """Shipment Tracking
    """
    __name__ = 'shipment.tracking'
    _rec_name = 'tracking_number'

    #: Boolean to indicate if tracking number is master.
    is_master = fields.Boolean("Is Master ?", readonly=True, select=True)

    origin = fields.Reference(
        'Origin', selection='get_origin', select=True, readonly=True
    )
    tracking_number = fields.Char(
        "Tracking Number", required=True, select=True, readonly=True
    )
    carrier = fields.Many2One(
        'carrier', 'Carrier', required=True, readonly=True
    )
    tracking_url = fields.Char("Tracking Url", readonly=True)
    state = fields.Selection([
        ('waiting', 'Waiting'),
        ('in_transit', 'In Transit'),
        ('delivered', 'Delivered'),
        ('failure', 'Failure'),
        ('returned', 'Returned'),
        ('cancelled', 'Cancelled'),
        ('pending_cancellation', 'Pending Cancellation'),
        ], 'State', readonly=True, required=True, select=True)

    @staticmethod
    def default_state():
        return 'waiting'

    @classmethod
    def __setup__(cls):
        """
        Setup the class before adding to pool
        """
        super(ShipmentTracking, cls).__setup__()
        cls._buttons.update({
            'cancel_tracking_number_button': {
                'invisible': Eval('state') == 'cancelled',
            },
            'refresh_status_button': {},
        })

    def cancel_tracking_number(self):
        "Cancel tracking number"
        self.state = 'cancelled'
        self.save()

    @classmethod
    @ModelView.button
    def cancel_tracking_number_button(cls, tracking_numbers):
        """
        Cancel tracking numbers
        """
        for tracking_number in tracking_numbers:
            tracking_number.cancel_tracking_number()

    def refresh_status(self):
        """
        Downstream module can implement this
        """
        pass

    @classmethod
    @ModelView.button
    def refresh_status_button(cls, tracking_numbers):
        """
        Update tracking numbers state
        """
        for tracking_number in tracking_numbers:
            tracking_number.refresh_status()

    @classmethod
    def refresh_tracking_numbers_cron(cls):
        """
        This is a cron method, responsible for updating state of
        shipments.
        """
        states_to_refresh = [
            'pending_cancellation',
            'failure',
            'waiting',
            'in_transit',
        ]

        tracking_numbers = cls.search([
            ('state', 'in', states_to_refresh),
        ])
        for tracking_number in tracking_numbers:
            tracking_number.refresh_status()

    @classmethod
    def _get_origin(cls):
        'Return list of Model names for origin Reference'
        return ['stock.shipment.out', 'stock.package']

    @classmethod
    def get_origin(cls):
        Model = Pool().get('ir.model')
        models = cls._get_origin()
        models = Model.search([
            ('model', 'in', models),
        ])
        return [(None, '')] + [(m.model, m.name) for m in models]
