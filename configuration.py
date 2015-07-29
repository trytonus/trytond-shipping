from trytond.model import fields
from trytond.pool import PoolMeta
from trytond import backend
from trytond.transaction import Transaction

__all__ = ['PartyConfiguration']
__metaclass__ = PoolMeta


class PartyConfiguration:
    'Party Configuration'
    __name__ = 'party.configuration'

    default_validation_carrier = fields.Many2One(
        'carrier', 'Default Validation Carrier'
    )

    @classmethod
    def __register__(cls, module_name):

        TableHandler = backend.get('TableHandler')
        cursor = Transaction().cursor

        table_exist = TableHandler.table_exist(cursor, 'carrier_configuration')
        super(PartyConfiguration, cls).__register__(module_name)

        if table_exist:
            cursor.execute(
                "UPDATE %s "
                "SET default_validation_carrier="
                "(SELECT default_validation_carrier from %s)"
                % (
                    cls._table, 'carrier_configuration'
                )
            )
            TableHandler.drop_table(
                cursor, 'carrier.configuration', 'carrier_configuration'
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
