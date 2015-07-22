# -*- coding: utf-8 -*-
"""
    carrier.py

"""
from trytond import backend
from trytond.pool import PoolMeta, Pool
from trytond.model import ModelView, ModelSQL, ModelSingleton, fields
from trytond.transaction import Transaction

__all__ = ['Carrier', 'CarrierConfig']
__metaclass__ = PoolMeta


class CarrierConfig(ModelSingleton, ModelSQL, ModelView):
    "Carrier Configuration"
    __name__ = 'carrier.configuration'

    default_validation_carrier = fields.Many2One(
        'carrier', 'Default Validation Carrier'
    )

    @classmethod
    def __register__(cls, module_name):
        super(CarrierConfig, cls).__register__(module_name)

        TableHandler = backend.get('TableHandler')
        cursor = Transaction().cursor
        table = TableHandler(cursor, cls, module_name)

        if table.column_exist('default_validation_provider'):
            table.drop_column('default_validation_provider')

    @classmethod
    def __setup__(cls):
        super(CarrierConfig, cls).__setup__()

        carrier_cost_methods = cls.get_carrier_methods_for_domain()
        cls.default_validation_carrier.domain = [
            ('carrier_cost_method', 'in', carrier_cost_methods)
        ]

    @classmethod
    def get_carrier_methods_for_domain(cls):
        """
        Return the list of carrier methods that can be used for
        address validation
        """
        return []


class Carrier:
    "Carrier"
    __name__ = 'carrier'

    currency = fields.Many2One('currency.currency', 'Currency', required=True)

    @staticmethod
    def default_currency():
        Company = Pool().get('company.company')

        company = Transaction().context.get('company')
        if company:
            return Company(company).currency.id

    def get_rates(self):
        """
        Expects a list of tuples as:
            [
                (
                    <display method name>, <rate>, <currency>, <metadata>,
                    <write_vals>
                )
                ...
            ]

        Downstream shipping modules can implement this to get shipping rates.
        """
        return []  # pragma: no cover
