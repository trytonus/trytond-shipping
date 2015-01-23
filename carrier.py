# -*- coding: utf-8 -*-
"""
    carrier.py

    :copyright: (c) 2014 by Openlabs Technologies & Consulting (P) Limited
    :license: BSD, see LICENSE for more details.
"""
from trytond.pool import PoolMeta
from trytond.model import ModelView, ModelSQL, ModelSingleton, fields

__all__ = ['Carrier', 'CarrierConfig']
__metaclass__ = PoolMeta


class CarrierConfig(ModelSingleton, ModelSQL, ModelView):
    "Carrier Configuration"
    __name__ = 'carrier.configuration'

    default_validation_provider = fields.Selection(
        'get_default_validation_providers', 'Default Validation Provider'
    )

    @classmethod
    def get_default_validation_providers(cls):
        """
        Downstream modules can implement `_<provider>_address_validation`
        method in address and append <provider> to this list.
        """
        return [(None, '')]


class Carrier:
    "Carrier"
    __name__ = 'carrier'

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
