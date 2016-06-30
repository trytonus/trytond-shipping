# -*- coding: utf-8 -*-
"""
    tracking.py

"""
from trytond.model import fields, ModelView, ModelSQL
from trytond.pool import PoolMeta, Pool
from trytond.pyson import Eval

__metaclass__ = PoolMeta
__all__ = ['ShipmentTracking']


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
