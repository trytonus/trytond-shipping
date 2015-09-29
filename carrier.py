# -*- coding: utf-8 -*-
"""
    carrier.py

"""
from trytond.pool import PoolMeta, Pool
from trytond.model import fields
from trytond.transaction import Transaction

__all__ = ['Carrier']
__metaclass__ = PoolMeta


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
        # TODO: Remove this method in next version and use `get_shipping_rates`
        # method in sale instead
        return []  # pragma: no cover
