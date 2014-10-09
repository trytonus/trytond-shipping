# -*- coding: utf-8 -*-
"""
    tests/test_shipping.py

    :copyright: (C) 2014 by Openlabs Technologies & Consulting (P) Limited
    :license: BSD, see LICENSE for more details.
"""
import sys
import os
DIR = os.path.abspath(os.path.normpath(os.path.join(
    __file__, '..', '..', '..', '..', '..', 'trytond'
)))
if os.path.isdir(DIR):
    sys.path.insert(0, os.path.dirname(DIR))
import unittest
from decimal import Decimal

import trytond.tests.test_tryton
from trytond.tests.test_tryton import POOL, DB_NAME, USER, CONTEXT
from trytond.transaction import Transaction


class TestShipping(unittest.TestCase):
    '''
    Test views and depends
    '''

    def setUp(self):
        """
        Set up data used in the tests.
        this method is called before each test function execution.
        """
        trytond.tests.test_tryton.install_module('shipping')

        self.Party = POOL.get('party.party')
        self.Category = POOL.get('product.category')
        self.Party = POOL.get('party.party')
        self.Payment_term = POOL.get('account.invoice.payment_term')
        self.Country = POOL.get('country.country')
        self.CountrySubdivision = POOL.get('country.subdivision')
        self.Sale = POOL.get('sale.sale')
        self.Currency = POOL.get('currency.currency')
        self.Company = POOL.get('company.company')
        self.Template = POOL.get('product.template')
        self.SaleLine = POOL.get('sale.line')
        self.Uom = POOL.get('product.uom')
        self.User = POOL.get('res.user')
        self.Account = POOL.get('account.account')

    def setup_defaults(self):
        """
        Setup defaults
        """
        # Create currency
        currency, = self.Currency.create([{
            'name': 'United Stated Dollar',
            'code': 'USD',
            'symbol': 'USD',
        }])

        with Transaction().set_context(company=None):
            company_party, = self.Party.create([{
                'name': 'Test Party',
            }])

        self.company, = self.Company.create([{
            'party': company_party.id,
            'currency': currency.id,
        }])
        country_us, = self.Country.create([{
            'name': 'United States',
            'code': 'US',
        }])

        subdivision_florida, = self.CountrySubdivision.create([{
            'name': 'Florida',
            'code': 'US-FL',
            'country': country_us.id,
            'type': 'state'
        }])

        self.User.write(
            [self.User(USER)], {
                'main_company': self.company.id,
                'company': self.company.id,
            }
        )

        self._create_coa_minimal(company=self.company)
        self.payment_term, = self._create_payment_term()

        self.uom_kg, = self.Uom.search([('symbol', '=', 'kg')])
        self.uom_pound, = self.Uom.search([('symbol', '=', 'lb')])

        account_revenue, = self.Account.search([
            ('kind', '=', 'revenue')
        ])

        # Create product category
        category, = self.Category.create([{
            'name': 'Test Category',
        }])

        # Create product
        template, = self.Template.create([{
            'name': 'Test Product',
            'category': category.id,
            'type': 'goods',
            'sale_uom': self.uom_kg,
            'list_price': Decimal('10'),
            'cost_price': Decimal('5'),
            'default_uom': self.uom_kg,
            'salable': True,
            'account_revenue': account_revenue.id,
            'products': [('create', self.Template.default_products())]
        }])

        self.product = template.products[0]

        # Carrier Carrier Product
        carrier_product_template, = self.Template.create([{
            'name': 'Test Carrier Product',
            'category': category.id,
            'type': 'service',
            'salable': True,
            'sale_uom': self.uom_kg,
            'list_price': Decimal('10'),
            'cost_price': Decimal('5'),
            'default_uom': self.uom_kg,
            'cost_price_method': 'fixed',
            'account_revenue': account_revenue.id,
            'products': [('create', self.Template.default_products())]
        }])

        self.carrier_product = carrier_product_template.products[0]

        self.sale_party, = self.Party.create([{
            'name': 'Test Sale Party',
            'vat_number': '123456',
            'addresses': [('create', [{
                'name': 'John Doe',
                'street': '250 NE 25th St',
                'zip': '33137',
                'city': 'Miami, Miami-Dade',
                'country': country_us.id,
                'subdivision': subdivision_florida.id,
            }])]
        }])

    def _create_coa_minimal(self, company):
        """Create a minimal chart of accounts
        """
        AccountTemplate = POOL.get('account.account.template')
        Account = POOL.get('account.account')

        account_create_chart = POOL.get(
            'account.create_chart', type="wizard"
        )

        account_template, = AccountTemplate.search(
            [('parent', '=', None)]
        )

        session_id, _, _ = account_create_chart.create()
        create_chart = account_create_chart(session_id)
        create_chart.account.account_template = account_template
        create_chart.account.company = company
        create_chart.transition_create_account()

        receivable, = Account.search([
            ('kind', '=', 'receivable'),
            ('company', '=', company),
        ])
        payable, = Account.search([
            ('kind', '=', 'payable'),
            ('company', '=', company),
        ])
        create_chart.properties.company = company
        create_chart.properties.account_receivable = receivable
        create_chart.properties.account_payable = payable
        create_chart.transition_create_properties()

    def _get_account_by_kind(self, kind, company=None, silent=True):
        """Returns an account with given spec

        :param kind: receivable/payable/expense/revenue
        :param silent: dont raise error if account is not found
        """
        Account = POOL.get('account.account')
        Company = POOL.get('company.company')

        if company is None:
            company, = Company.search([], limit=1)

        accounts = Account.search([
            ('kind', '=', kind),
            ('company', '=', company)
        ], limit=1)
        if not accounts and not silent:
            raise Exception("Account not found")
        return accounts[0] if accounts else None

    def _create_payment_term(self):
        """Create a simple payment term with all advance
        """
        PaymentTerm = POOL.get('account.invoice.payment_term')

        return PaymentTerm.create([{
            'name': 'Direct',
            'lines': [('create', [{'type': 'remainder'}])]
        }])

    def test_0005_sale_line_weight(self):
        '''
        Check weight for product in sale line
        '''

        with Transaction().start(DB_NAME, USER, context=CONTEXT):
            self.setup_defaults()

            # Create sale order
            with Transaction().set_context(company=self.company.id):
                sale, = self.Sale.create([{
                    'reference': 'S-1001',
                    'payment_term': self.payment_term.id,
                    'party': self.sale_party.id,
                    'invoice_address': self.sale_party.addresses[0].id,
                    'shipment_address': self.sale_party.addresses[0].id,
                }])

            # Sale line without product
            sale_line, = self.SaleLine.create([{
                'sale': sale.id,
                'type': 'line',
                'quantity': 1,
                'unit_price': Decimal('10.00'),
                'description': 'Test Description1',
                'unit': self.product.template.default_uom,
            }])
            weight = sale_line.get_weight(self.uom_kg)

            self.assertEqual(weight, Decimal('0'))

            # Sale line with product but quantity as 0
            sale_line, = self.SaleLine.create([{
                'sale': sale.id,
                'type': 'line',
                'quantity': 0,
                'product': self.product.id,
                'unit_price': Decimal('10.00'),
                'description': 'Test Description1',
                'unit': self.product.template.default_uom,
            }])
            weight = sale_line.get_weight(self.uom_kg)

            self.assertEqual(weight, Decimal('0'))

            # Sale line with service product and quantity > 0
            sale_line, = self.SaleLine.create([{
                'sale': sale.id,
                'type': 'line',
                'quantity': 1,
                'product': self.carrier_product.id,
                'unit_price': Decimal('10.00'),
                'description': 'Test Description1',
                'unit': self.carrier_product.template.default_uom,
            }])

            weight = sale_line.get_weight(self.uom_kg)

            self.assertEqual(weight, Decimal('0'))

            # Sale line with product having no weight
            sale_line, = self.SaleLine.create([{
                'sale': sale.id,
                'type': 'line',
                'quantity': 1,
                'product': self.product.id,
                'unit_price': Decimal('10.00'),
                'description': 'Test Description1',
                'unit': self.product.template.default_uom,
            }])

            with self.assertRaises(Exception):
                sale_line.get_weight(self.uom_pound)

            # Assign weight
            self.product.template.weight = Decimal('0.5')
            self.product.template.weight_uom = self.uom_kg
            self.product.template.save()

            # Sale line with uom different from product uom
            sale_line, = self.SaleLine.create([{
                'sale': sale.id,
                'type': 'line',
                'quantity': 1,
                'product': self.product.id,
                'unit_price': Decimal('10.00'),
                'description': 'Test Description1',
                'unit': self.uom_pound,
            }])

            weight = sale_line.get_weight(self.uom_pound)

            self.assertEqual(weight, Decimal('1.0'))

            # Sale line with uom same as product uom
            sale_line, = self.SaleLine.create([{
                'sale': sale.id,
                'type': 'line',
                'quantity': 1,
                'product': self.product.id,
                'unit_price': Decimal('10.00'),
                'description': 'Test Description1',
                'unit': self.product.template.default_uom,
            }])

            weight = sale_line.get_weight(self.uom_kg)

            self.assertEqual(weight, Decimal('1.0'))

    def test_0005_stock_move_weight(self):
        '''
        Check weight for product in shipment
        '''
        StockLocation = POOL.get('stock.location')
        StockMove = POOL.get('stock.move')

        with Transaction().start(DB_NAME, USER, context=CONTEXT):
            self.setup_defaults()

            customer_location, = StockLocation.search([
                ('code', '=', 'CUS')
            ])

            input_location, = StockLocation.search([
                ('code', '=', 'IN')
            ])

            with Transaction().set_context(company=self.company.id):

                # Stock move with quantity as 0
                move, = StockMove.create([{
                    'from_location': customer_location.id,
                    'to_location': input_location.id,
                    'product': self.product.id,
                    'uom': self.product.template.default_uom,
                    'quantity': 0,
                }])

                self.assertEqual(
                    move.get_weight(self.uom_pound), Decimal('0')
                )

                # Stock move with product having no weight
                move, = StockMove.create([{
                    'from_location': customer_location.id,
                    'to_location': input_location.id,
                    'product': self.product.id,
                    'quantity': 1,
                    'uom': self.product.template.default_uom,
                }])

                with self.assertRaises(Exception):
                    move.get_weight(self.uom_pound)

                # Assign weight
                self.product.template.weight = Decimal('0.5')
                self.product.template.weight_uom = self.uom_kg
                self.product.template.save()

                # Stock move with uom different from product uom
                move, = StockMove.create([{
                    'from_location': customer_location.id,
                    'to_location': input_location.id,
                    'product': self.product.id,
                    'quantity': 1,
                    'uom': self.uom_pound,
                }])

                self.assertEqual(
                    move.get_weight(self.uom_pound), Decimal('1.0')
                )

                # Stock move with uom as product uom
                move, = StockMove.create([{
                    'from_location': customer_location.id,
                    'to_location': input_location.id,
                    'product': self.product.id,
                    'quantity': 1,
                    'uom': self.product.template.default_uom,
                }])

                self.assertEqual(
                    move.get_weight(self.uom_kg), Decimal('1.0')
                )


def suite():
    """
    Define suite
    """
    test_suite = trytond.tests.test_tryton.suite()
    test_suite.addTests(
        unittest.TestLoader().loadTestsFromTestCase(TestShipping)
    )
    return test_suite

if __name__ == '__main__':
    unittest.TextTestRunner(verbosity=2).run(suite())
