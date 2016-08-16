from trytond.model import fields
from trytond.pool import PoolMeta

__all__ = ['PartyConfiguration']
__metaclass__ = PoolMeta


class PartyConfiguration:
    'Party Configuration'
    __name__ = 'party.configuration'

    default_validation_carrier = fields.Many2One(
        'carrier', 'Default Validation Carrier'
    )

    @classmethod
    def __setup__(cls):
        super(PartyConfiguration, cls).__setup__()

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
