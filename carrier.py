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

    save_carrier_logs = fields.Boolean('Save Carrier Logs')

    @staticmethod
    def default_save_carrier_logs():
        return True


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
