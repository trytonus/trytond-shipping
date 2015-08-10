# -*- coding: utf-8 -*-
"""
    tests/test_party.py

"""
import sys
import os
import unittest
from decimal import Decimal

import trytond.tests.test_tryton
from trytond.tests.test_tryton import POOL, DB_NAME, USER, CONTEXT
from trytond.transaction import Transaction
from trytond.exceptions import UserError

DIR = os.path.abspath(os.path.normpath(os.path.join(
    __file__, '..', '..', '..', '..', '..', 'trytond'
)))
if os.path.isdir(DIR):
    sys.path.insert(0, os.path.dirname(DIR))


class TestParty(unittest.TestCase):
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
        self.PartyContact = POOL.get('party.contact_mechanism')
        self.Address = POOL.get('party.address')
        self.Category = POOL.get('product.category')
        self.Party = POOL.get('party.party')
        self.Payment_term = POOL.get('account.invoice.payment_term')
        self.Country = POOL.get('country.country')
        self.CountrySubdivision = POOL.get('country.subdivision')
        self.Sale = POOL.get('sale.sale')
        self.SaleConfiguration = POOL.get('sale.configuration')
        self.Currency = POOL.get('currency.currency')
        self.Company = POOL.get('company.company')
        self.Template = POOL.get('product.template')
        self.SaleLine = POOL.get('sale.line')
        self.Uom = POOL.get('product.uom')
        self.User = POOL.get('res.user')
        self.Account = POOL.get('account.account')
        self.Product = POOL.get('product.product')
        self.Carrier = POOL.get('carrier')
        self.PartyConf = POOL.get('party.configuration')
        self.AddrValWizard = POOL.get('party.address.validation', type='wizard')
        self.Attachment = POOL.get('ir.attachment')
        self.Shipment = POOL.get('stock.shipment.out')
        self.StockLocation = POOL.get('stock.location')

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
            company_party, carrier_party = self.Party.create([{
                'name': 'Test Party',
                'vat_number': '33065',
            }, {
                'name': 'Carrier Party',
            }])

        self.company, = self.Company.create([{
            'party': company_party.id,
            'currency': currency.id,
        }])
        self.PartyContact.create([{
            'type': 'phone',
            'value': '8005551212',
            'party': self.company.party.id
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
            }])],
        }])
        self.PartyContact.create([{
            'type': 'phone',
            'value': '8005763279',
            'party': self.sale_party.id
        }])

        carrier_product = self.create_product(is_service=True)

        self.carrier, = self.Carrier.create([{
            'party': carrier_party,
            'carrier_product': carrier_product,
            'currency': currency,
        }])

        warehouse_address, = self.Address.create([{
            'party': self.company.party.id,
            'name': 'Amine Khechfe',
            'street': '247 High Street',
            'zip': '32003',
            'city': 'Palo Alto',
            'country': country_us.id,
            'subdivision': subdivision_florida.id,
        }])

        warehouse = self.StockLocation.search([('type', '=', 'warehouse')])[0]
        warehouse.address = warehouse_address
        warehouse.save()

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

    def create_product(self, weight=None, weight_uom=None, is_service=False):
        """
        Create product
        """
        # Create product category
        category, = self.Category.create([{
            'name': 'Test Category',
        }])

        account_revenue, = self.Account.search([
            ('kind', '=', 'revenue')
        ])

        # Create product
        template, = self.Template.create([{
            'name': 'Test Product',
            'category': category.id,
            'type': is_service and 'service' or 'goods',
            'sale_uom': self.uom_kg,
            'list_price': Decimal('10'),
            'cost_price': Decimal('5'),
            'default_uom': self.uom_kg,
            'weight': weight,
            'weight_uom': weight_uom,
            'salable': True,
            'account_revenue': account_revenue.id,
            'products': [
                ('create', [{
                    'code': 'Test Product'
                }])
            ]
        }])

        return template.products[0]

    def test_0010_address_validation_wizard(self):
        """
        Test the address validation wizard.
        """
        with Transaction().start(DB_NAME, USER, context=CONTEXT):
            self.setup_defaults()

            with Transaction().set_context(
                active_id=self.sale_party.addresses[0].id
            ):
                # UserError is raised as no configuration provider is available.
                session_id, start_state, end_state = self.AddrValWizard.create()

                with self.assertRaises(UserError) as e:
                    self.AddrValWizard(session_id).transition_init()

                self.assertIn(
                    'Validation Carrier is not selected', e.exception.message
                )


def suite():
    """
    Define suite
    """
    test_suite = trytond.tests.test_tryton.suite()
    test_suite.addTests(
        unittest.TestLoader().loadTestsFromTestCase(TestParty)
    )
    return test_suite

if __name__ == '__main__':
    unittest.TextTestRunner(verbosity=2).run(suite())
