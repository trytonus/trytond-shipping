# -*- coding: utf-8 -*-
"""
    party.py

    :copyright: (c) 2014 by Openlabs Technologies & Consulting (P) Limited
    :license: BSD, see LICENSE for more details.
"""
from trytond.pool import PoolMeta, Pool

__all__ = ['Address']
__metaclass__ = PoolMeta


class Address:
    "Party"
    __name__ = 'party.address'

    def validate_address(self, provider=None):
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
        CarrierConfig = Pool().get('carrier.configuration')

        config = CarrierConfig(1)
        provider = provider or config.default_validation_provider

        if not provider:
            # TODO: Make this translatable error message
            self.raise_user_error(
                "Validation method is not selected in carrier configuration."
            )

        return getattr(self, '_{0}_address_validate'.format(provider))()
