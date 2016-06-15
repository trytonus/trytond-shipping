# -*- coding: utf-8 -*-
"""
    location.py

"""
from trytond.pool import PoolMeta
from trytond.model import fields
from trytond.pyson import Eval

__all__ = ['Location']
__metaclass__ = PoolMeta


class Location:
    __name__ = "stock.location"

    return_address = fields.Many2One(
        "party.address", "Return Address", states={
            'invisible': Eval('type') != 'warehouse',
            'readonly': ~Eval('active'),
        }, depends=['type', 'active'],
        help="Return address to print on shipping label"
    )
