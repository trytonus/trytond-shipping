# -*- coding: utf-8 -*-
"""
    party.py

"""
from trytond.pool import PoolMeta, Pool
from trytond.transaction import Transaction
from trytond.pyson import Eval, Bool
from trytond.model import ModelView, fields
from trytond.wizard import Wizard, StateView, StateTransition, Button

__all__ = [
    'Address', 'AddressValidationMsg', 'AddressValidationWizard',
    'AddressValidationSuggestionView'
]
__metaclass__ = PoolMeta


class Address:
    "Party"
    __name__ = 'party.address'

    @classmethod
    def __setup__(cls):
        super(Address, cls).__setup__()
        cls._buttons.update({
            'validate_address_button': {
                'readonly': ~Bool(Eval('active')),
            },
        })

    @classmethod
    @ModelView.button_action('shipping.wizard_address_validation')
    def validate_address_button(cls, addresses):
        pass  # pragma: no cover

    def validate_address(self, carrier=None):
        """
        This method provides a generic address validation API that delegates
        actual calls to external services (or perhaps even database lookups)
        which should be implemented by other modules.

        When called without a provider, the system looks into configuration and
        checks if a default validation provider exists. If one does, it uses
        that.

        When there is no provider specified and a default is not configured
        a `UserError` is raised.

        If you wish to implement an address validation API, the interface it
        should follow is explained below with pseudcode. The basic idea of the
        implementation is to handle three cases:

        * case 1: Perfect Address. Bingo! just return a True.
        * case 2: Possible matches: Return list of active records (unsaved).
        * case 3: No matches, just return an empty list.
        * everything else including errors should raise `UserError`

            class Address:
                __name__ = 'party.address'

                def _providername_address_validate(self):
                    '''
                    Validate the address using the web service of providername
                    and return a list of active records of addresses with
                    any or all the information filled.
                    '''
                    # Step 1: Call my provider's API with the address
                    try:
                        response = myprovider.validate_address(
                            name=self.name,
                            street=self.street,
                            city=self.city,
                            zip=self.zip
                        )
                    except MyProviderError, err:
                        raise UserError(
                            'Address Validation Failed: %s' % err.message
                        )

                    matches = []

                    # Step 2: Check the response to see how the address is
                    if response.address_is_correct:
                        return True
                    elif response.possible_matches:
                        Address = Pool().get('party.address')
                        for suggestion in response.suggestions:
                            matches.append(
                                Address(
                                    name=self.name,
                                    street=self.street,
                                    state=state_id,
                                    city=city,
                                    country=country_id
                                )
                            )
                    return matches

        A good example can be found in the UPS module's implementation of this
        in
        :ref:`address class <trytond-ups:party.Address._ups_address_validate>`.
        """
        CarrierConfig = Pool().get('party.configuration')

        config = CarrierConfig(1)
        carrier = carrier or config.default_validation_carrier

        if not carrier:
            # TODO: Make this translatable error message
            self.raise_user_error(
                "Validation Carrier is not selected in carrier configuration."
            )

        return getattr(
            self, '_{0}_address_validate'.format(carrier.carrier_cost_method)
        )()  # pragma: no cover

    def serialize(self, purpose=None):
        """
        Serialize address record.
        """
        if purpose == 'validation':
            return {
                'name': self.name or None,
                'street': self.street or None,
                'zip': self.zip or None,
                'city': self.city or None,
                'country': self.country and self.country.id or None,
                'subdivision': self.subdivision and self.subdivision.id or None,
            }
        elif hasattr(super(Address, self), 'serialize'):  # pragma: no cover
            return super(Address, self).serialize(purpose=purpose)


class AddressValidationSuggestionView(ModelView):
    """
    Address Validation Wizard Suggestion View
    """
    __name__ = 'party.address.validation.start'

    # Older Values
    current_name = fields.Char('Current Name', readonly=True)
    current_street = fields.Char('Current Street', readonly=True)
    current_zip = fields.Char('Current Zip', readonly=True)
    current_city = fields.Char('Current City', readonly=True)
    current_country = fields.Many2One(
        'country.country', 'Current Country', readonly=True
    )
    current_subdivision = fields.Many2One(
        "country.subdivision", 'Current Subdivision', readonly=True
    )

    # Editable suggestions
    street = fields.Char('Suggested Street')
    zip = fields.Char('Suggested Zip')
    city = fields.Char('Suggested City')
    country = fields.Many2One('country.country', 'Suggested Country')
    subdivision = fields.Many2One(
        "country.subdivision", 'Suggested Subdivision',
        domain=[('country', '=', Eval('country'))],
        depends=['country']
    )


class AddressValidationMsg(ModelView):
    'End State for Address Validation'
    __name__ = 'party.address.validation.end'

    done_msg = fields.Text("Message", readonly=True)

    @staticmethod
    def default_done_msg():  # pragma: no cover
        """
        Returns default message.
        """
        return (
            'Address validation is complete.'
        )


class AddressValidationWizard(Wizard):
    """
    Wizard to validate the given address.
    """
    __name__ = 'party.address.validation'

    start_state = 'init'
    end_state = 'end'

    init = StateTransition()
    start = StateView(
        'party.address.validation.start',
        'shipping.address_suggestion_view_form',
        [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button(
                'Save', 'update',
                'tryton-ok', default=True
            )
        ]
    )
    done = StateView(
        'party.address.validation.end',
        'shipping.address_validation_end_view_form',
        [
            Button('OK', 'end', 'tryton-ok')
        ]
    )
    update = StateTransition()

    @classmethod
    def __setup__(cls):
        super(AddressValidationWizard, cls).__setup__()
        cls._error_messages.update({
            'incomplete_address': (
                'Please fill out the address completely before attempting '
                'validation.'
            ),
        })

    def transition_init(self):
        """
        Initial transition where address validation is performed.
        """
        Address = Pool().get('party.address')

        address = Address(Transaction().context.get('active_id'))
        self.check_for_address_fields(address)

        # Now perform the validation
        try:
            match_addresses = address.validate_address()
        except:
            raise

        if match_addresses is True:  # pragma: no cover
            # If match_addresses is simply True, return 'done' state.
            return 'done'

        if isinstance(match_addresses, list):  # pragma: no cover
            # Pick highest ranked suggestion.
            # Save fields in self.start.
            self.start.street = match_addresses[0].street
            self.start.zip = match_addresses[0].zip
            self.start.city = match_addresses[0].city
            self.start.country = match_addresses[0].country.id
            self.start.subdivision = match_addresses[0].subdivision.id
        return 'start'

    def default_start(self, data):
        """
        Fills the values in the ModelView.
        """
        Address = Pool().get('party.address')

        old_address = Address(Transaction().context.get('active_id'))

        # First fill in the old values
        values = {
            'current_' + str(key): value
            for key, value in old_address.serialize(purpose='validation')
            .iteritems()
        }

        # Update the new values.
        # The `values` dict needs to contain specifically the newer address
        # key-value pairs or else the fields become blank.
        values.update({
            'street': self.start.street,
            'zip': self.start.zip,
            'city': self.start.city,
            'country': self.start.country.id,
            'subdivision': self.start.subdivision.id,
        })

        return values

    def transition_update(self):  # pragma: no cover
        """
        Updates the address and returns the next state.
        """
        Address = Pool().get('party.address')

        address = Address(Transaction().context.get('active_id'))
        Address.write([address], {
            'street': self.start.street,
            'zip': self.start.zip,
            'city': self.start.city,
            'country': self.start.country.id,
            'subdivision': self.start.subdivision.id,
        })
        return 'done'

    def default_done(self, data):
        """
        Validation completion state.
        """
        Address = Pool().get('party.address')

        address = Address(Transaction().context.get('active_id'))
        return {
            'done_msg': (
                'Address validation is now complete. '
                'The full address is as follows -: \n%s'
                % address.full_address
            ),
        }

    def check_for_address_fields(self, address):
        """
        This method checks that the address is complete before allowing any
        validation.

        :param address: Active record to be checked against
        """
        for key, value in address.serialize(purpose='validation').iteritems():
            if value is None:
                self.raise_user_error('incomplete_address')
