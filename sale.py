# -*- coding: utf-8 -*-
"""
    sale.py

"""
import json
from decimal import Decimal

from trytond.model import ModelView, fields
from trytond.pool import PoolMeta, Pool
from trytond.pyson import Eval, Not, Bool
from trytond.transaction import Transaction
from trytond.wizard import Wizard, StateView, Button, StateTransition
from babel.numbers import format_currency

__all__ = ['SaleLine', 'Sale']
__metaclass__ = PoolMeta


class Sale:
    "Sale"
    __name__ = 'sale.sale'

    is_international_shipping = fields.Function(
        fields.Boolean("Is International Shipping"),
        'on_change_with_is_international_shipping'
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

    available_carrier_services = fields.Function(
        fields.One2Many("carrier.service", None, 'Available Carrier Services'),
        getter="on_change_with_available_carrier_services"
    )
    carrier_service = fields.Many2One(
        "carrier.service", "Carrier Service", domain=[
            ('id', 'in', Eval('available_carrier_services'))
        ], states={
            "invisible": Not(Bool(Eval('carrier'))),
            "readonly": Eval('state') != 'draft',
        }, depends=['carrier', 'available_carrier_services', 'state']
    )
    carrier_cost_method = fields.Function(
        fields.Char('Carrier Cost Method'),
        "on_change_with_carrier_cost_method"
    )

    @classmethod
    @ModelView.button_action('shipping.wizard_sale_apply_shipping')
    def apply_shipping(cls, sales):
        pass

    @fields.depends("carrier")
    def on_change_with_carrier_cost_method(self, name=None):
        if self.carrier:
            return self.carrier.carrier_cost_method

    def on_change_lines(self):
        """Pass a flag in context which indicates the get_sale_price method
        of carrier not to calculate cost on each line change
        """
        with Transaction().set_context({'ignore_carrier_computation': True}):
            return super(Sale, self).on_change_lines()

    @fields.depends("carrier")
    def on_change_with_available_carrier_services(self, name=None):
        if self.carrier:
            return map(int, self.carrier.services)
        return []

    @classmethod
    def __setup__(cls):
        super(Sale, cls).__setup__()
        cls._error_messages.update({
            'warehouse_address_missing': 'Warehouse address is missing',
        })
        cls._buttons.update({
            'apply_shipping': {
                "invisible": ~Eval('state').in_([
                    'draft', 'quotation', 'confirmed'
                ])
            }
        })

    @fields.depends('weight_uom')
    def on_change_with_weight_digits(self, name=None):
        if self.weight_uom:
            return self.weight_uom.digits
        return 2

    def get_weight_uom(self, name):
        """
        Returns weight uom for the sale
        """
        ModelData = Pool().get('ir.model.data')

        return ModelData.get_id('product', 'uom_pound')

    def get_weight(self, name):
        """
        Returns sum of weight associated with each line
        """
        return sum(map(
            lambda line: line.get_weight(self.weight_uom, silent=True),
            self.lines
        ))

    @fields.depends('party', 'shipment_address', 'warehouse')
    def on_change_with_is_international_shipping(self, name=None):
        """
        Return True if international shipping
        """
        from_address = self._get_ship_from_address(silent=True)

        if self.shipment_address and from_address and \
                from_address.country and self.shipment_address.country and \
                from_address.country != self.shipment_address.country:
            return True
        return False

    def _get_ship_from_address(self, silent=False):
        """
        Usually the warehouse from which you ship
        """
        if not self.warehouse.address and not silent:
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
        Sale = Pool().get('sale.sale')

        Sale.write([self], {
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
            ],
            # reset the amount caches or function
            # fields will continue to return cached values
            'untaxed_amount_cache': None,
            'tax_amount_cache': None,
            'total_amount_cache': None,
        })
        # reset the order total cache
        if self.state not in ('draft', 'quote'):
            Sale.store_cache([self])

    def _get_carrier_context(self):
        "Pass sale in the context"
        context = super(Sale, self)._get_carrier_context()
        context = context.copy()
        context['sale'] = self.id
        return context

    def apply_shipping_rate(self, rate):
        """
        This method applies shipping rate. Rate is a dictionary with following
        minimum keys:
            {
                'display_name': Name to display,
                'carrier_service': carrier.service active record,
                'cost': cost,
                'cost_currency': currency.currency active repord,
                'carrier': carrier active record,
            }

        It also creates a shipment line by deleting all existing ones.
        """
        Currency = Pool().get('currency.currency')

        self.carrier = rate['carrier']
        self.carrier_service = rate['carrier_service']
        self.save()

        shipment_cost = rate['cost_currency'].round(rate['cost'])
        if self.currency != rate['cost_currency']:
            shipment_cost = Currency.compute(
                rate['cost_currency'], shipment_cost, self.currency
            )

        self.add_shipping_line(shipment_cost, rate['display_name'])

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
            rates.extend(self.get_shipping_rate(carrier, silent=silent))
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
                'carrier_service': carrier_service,
                'cost': carrier.carrier_product.list_price,
                'cost_currency': currency,
                'carrier': carrier,
            }
            display_name = carrier.rec_name
            rate_dict['display_name'] = display_name
            return [rate_dict]

        return []

    @classmethod
    def get_allowed_carriers_domain(cls):
        """This method returns domain to seach allowed carriers

        Downstream modules can inherit and update customize this domain.
        """
        return []

    def create_shipment(self, shipment_type):
        Shipment = Pool().get('stock.shipment.out')

        with Transaction().set_context(ignore_carrier_computation=True):
            shipments = super(Sale, self).create_shipment(shipment_type)

        if shipment_type == 'out' and shipments:
            for shipment in shipments:
                write_vals = {}

                if self.carrier:
                    write_vals['carrier'] = self.carrier.id
                    if self.carrier_service:
                        write_vals['carrier_service'] = self.carrier_service.id

                Shipment.write([shipment], write_vals)

        return shipments


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
        if self.product.weight_uom != weight_uom:
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

        Sale.write(Sale.browse(data['res_id']), {
            'carrier': None,
            'carrier_service': None,
        })

        return action, data


class ApplyShippingStart(ModelView):
    "Apply Shipping"
    __name__ = "sale.sale.apply_shipping.start"

    carrier = fields.Many2One("carrier", "Carrier")
    available_carrier_services = fields.Function(
        fields.One2Many("carrier.service", None, 'Available Carrier Services'),
        getter="on_change_with_available_carrier_services"
    )
    carrier_service = fields.Many2One(
        "carrier.service", "Service", domain=[
            ('id', 'in', Eval('available_carrier_services'))
        ], depends=['available_carrier_services']
    )
    weight = fields.Float("Weight", required=True)

    @fields.depends("carrier")
    def on_change_with_available_carrier_services(self, name=None):
        if self.carrier:
            return map(int, self.carrier.services)
        return []


class ApplyShippingSelectRate(ModelView):
    'Select Rate'
    __name__ = 'sale.sale.apply_shipping.select_rate'

    rate = fields.Selection([], 'Rate', required=True, sort=False)

    @classmethod
    def default_rate(cls):
        # Fill the first selection value
        return cls.rate.selection and cls.rate.selection[0][0] or None


class ApplyShipping(Wizard):
    "Apply Shipping"
    __name__ = "sale.sale.apply_shipping"
    start_state = 'check'

    check = StateTransition()
    start = StateView(
        'sale.sale.apply_shipping.start',
        'shipping.apply_shipping_start_form',
        [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Choose Rate', 'get_rates', 'tryton-go-next', default=True),
        ]
    )
    get_rates = StateTransition()
    select_rate = StateView(
        'sale.sale.apply_shipping.select_rate',
        'shipping.apply_shipping_select_rate_form',
        [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Apply', 'apply_rate', 'tryton-go-next', default=True),
        ]
    )
    apply_rate = StateTransition()

    def default_start(self, data):
        return {
            "carrier": self.sale.carrier and self.sale.carrier.id,
            "carrier_service": self.sale.carrier_service and
            self.sale.carrier_service.id,
            "weight": self.sale.weight,
        }

    @property
    def sale(self):
        Sale = Pool().get('sale.sale')
        return Sale(Transaction().context.get('active_id'))

    def transition_check(self):
        if self.sale.state not in ('draft', 'quotation', 'confirmed'):
            self.raise_user_error(
                "Shipping cannot be applied in %s state" % self.sale.state
            )
        return 'start'

    def transition_get_rates(self):
        if self.start.carrier:
            rates = self.sale.get_shipping_rate(
                self.start.carrier, self.start.carrier_service, silent=True
            )
        else:
            rates = self.sale.get_shipping_rates(silent=True)

        sorted_rates = sorted(rates, key=lambda r: Decimal("%s" % r['cost']))
        result = []
        for rate in sorted_rates:
            key = json.dumps({
                'display_name': rate['display_name'],
                'cost_currency': rate['cost_currency'].id,
                'cost': str(rate['cost']),
                'carrier': rate['carrier'].id,
                'carrier_service': rate['carrier_service'] and
                rate['carrier_service'].id
            })
            display_name = "%s %s" % (rate['display_name'], format_currency(
                rate['cost'], rate['cost_currency'].code,
                locale=Transaction().language
            ))
            result.append((key, display_name))
        self.select_rate.__class__.rate.selection = result

        return "select_rate"

    def transition_apply_rate(self):
        Currency = Pool().get('currency.currency')
        Carrier = Pool().get('carrier')
        CarrierService = Pool().get('carrier.service')

        # Build rate object
        rate = json.loads(self.select_rate.rate)
        rate['cost'] = Decimal(rate['cost'])
        rate['cost_currency'] = Currency(rate['cost_currency'])
        rate['carrier'] = Carrier(rate['carrier'])
        if rate['carrier_service']:
            rate['carrier_service'] = CarrierService(rate['carrier_service'])

        self.sale.apply_shipping_rate(rate)
        return 'end'
