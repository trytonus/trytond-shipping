# -*- coding: utf-8 -*-
"""
    manifest.py

    :copyright: (c) 2016 by Fulfil.IO Inc.
    :license: see LICENSE for more details.
"""
from datetime import datetime

from trytond.model import fields, ModelView, ModelSQL, Workflow
from trytond.pool import PoolMeta
from trytond.pyson import Eval

__metaclass__ = PoolMeta
__all__ = ["ShippingManifest"]


class ShippingManifest(Workflow, ModelSQL, ModelView):
    "Manifest Model for shipping."
    __name__ = "shipping.manifest"

    carrier = fields.Many2One("carrier", "Carrier", required=True, select=True)
    warehouse = fields.Many2One(
        "stock.location", "Warehouse", required=True, select=True,
        domain=[("type", "=", "warehouse")],
    )

    shipments = fields.One2Many(
        'stock.shipment.out', 'shipping_manifest', 'Shipments',
        states={
            "readonly": Eval("state") == "closed"
        },
        domain=[
            ('carrier', '=', Eval('carrier')),
            ('state', 'in', ('done', 'packed')),
            ('tracking_number', '!=', None)
        ],
        add_remove=[
            ('carrier', '=', Eval('carrier')),
            ('warehouse', '=', Eval('warehouse')),
            ('shipping_manifest', '=', None),
            ('state', '=', ('done', 'packed')),
            ('tracking_number', '!=', None)
        ], depends=['state', 'carrier', 'warehouse']
    )

    state = fields.Selection([
        ("open", "Open"),
        ("closed", "Closed")
        ], "State", required=True, select=True, readonly=True
    )

    close_date = fields.DateTime("Close Date", readonly=True)

    @classmethod
    @ModelView.button
    @Workflow.transition("closed")
    def close(cls, manifests):
        for manifest in manifests:
            manifest.close_date = datetime.utcnow()
            manifest.save()

    @staticmethod
    def default_state():
        return "open"

    @classmethod
    def __setup__(cls):
        super(ShippingManifest, cls).__setup__()
        cls._transitions |= set((
            ('open', 'closed'),
        ))
        cls._buttons.update({
            "close": {
                "invisible": Eval("state").in_(["closed"])
            },
        })

    def check_single_open_manifest(self):
        """
        Check if carrier has not more than 1 manifest
        """
        if self.search([
            ("state", "=", "open"),
            ("carrier", "=", self.carrier),
            ("id", "!=", self.id),
            ("warehouse", "=", self.warehouse)
        ]):
            self.raise_user_error(
                """One carrier cannot have more than 1
                open manifest in a warehouse at same time!"""
            )

    @classmethod
    def validate(cls, manifests):
        super(ShippingManifest, cls).validate(manifests)
        for manifest in manifests:
            manifest.check_single_open_manifest()

    @classmethod
    def get_manifest(cls, carrier, warehouse):
        """
        Returns currently opened manifest for carrier account. if not open new.
        """
        manifests = cls.search([
            ('state', '=', 'open'),
            ('carrier', '=', carrier),
            ('warehouse', '=', warehouse),
        ])

        if manifests:
            return manifests[0]

        return cls.create([{
            'carrier': carrier,
            'warehouse': warehouse
        }])[0]
