.. _api:

API Reference
=============

Following is the complete api reference for trytond-shipping.

Carrier
-------

.. currentmodule:: carrier

*Fields*
````````

.. autoattribute:: Carrier.services 
.. autoattribute:: Carrier.box_types

*Methods*
`````````

.. automethod:: Carrier.get_sale_price


Carrier Service
---------------

.. currentmodule:: carrier

*Fields*
````````

.. autoattribute:: Service.carrier_cost_method
.. autoattribute:: Service.name
.. autoattribute:: Service.code


Box Type
--------

.. currentmodule:: carrier

*Fields*
````````

.. autoattribute:: BoxType.carrier_cost_method
.. autoattribute:: BoxType.name
.. autoattribute:: BoxType.code
.. autoattribute:: BoxType.length
.. autoattribute:: BoxType.width
.. autoattribute:: BoxType.height
.. autoattribute:: BoxType.distance_unit


Sale
----

.. currentmodule:: sale

*Fields*
````````

.. autoattribute:: Sale.is_international_shipping
.. autoattribute:: Sale.weight
.. autoattribute:: Sale.carrier_cost_method
.. autoattribute:: Sale.carrier_service

*Methods*
`````````

.. automethod:: Sale.get_shipping_rates
.. automethod:: Sale.get_shipping_rate
.. automethod:: Sale.apply_shipping_rate


Package
-------

.. currentmodule:: shipment

*Fields*
````````

.. autoattribute:: Package.tracking_number
.. autoattribute:: Package.weight
.. autoattribute:: Package.computed_weight
.. autoattribute:: Package.override_weight
.. autoattribute:: Package.weight_uom
.. autoattribute:: Package.box_type
.. autoattribute:: Package.length
.. autoattribute:: Package.width
.. autoattribute:: Package.height
.. autoattribute:: Package.distance_unit


Shipment
--------

.. currentmodule:: shipment

*Fields*
````````

.. autoattribute:: ShipmentOut.is_international_shipping
.. autoattribute:: ShipmentOut.weight
.. autoattribute:: ShipmentOut.carrier_cost_method
.. autoattribute:: ShipmentOut.carrier_service
.. autoattribute:: ShipmentOut.tracking_number
.. autoattribute:: ShipmentOut.shipping_instructions

*Methods*
`````````

.. automethod:: ShipmentOut.get_shipping_rates
.. automethod:: ShipmentOut.get_shipping_rate
.. automethod:: ShipmentOut.apply_shipping_rate
.. automethod:: ShipmentOut.generate_shipping_labels


Generate Shipping Label Wizard
------------------------------

.. currentmodule:: shipment

*States*
````````

.. autoattribute:: GenerateShippingLabel.start
.. autoattribute:: GenerateShippingLabel.no_modules
.. autoattribute:: GenerateShippingLabel.generate

*Transitions*
`````````````

.. autoattribute:: GenerateShippingLabel.next
.. autoattribute:: GenerateShippingLabel.generate_labels

*Methods*
`````````

.. automethod:: GenerateShippingLabel.default_start
.. automethod:: GenerateShippingLabel.default_generate

*Property*
``````````
.. autoattribute:: GenerateShippingLabel.shipment


Shipment Tracking
-----------------

.. currentmodule:: shipment

*Fields*
````````

.. autoattribute:: ShipmentTracking.is_master
.. autoattribute:: ShipmentTracking.origin
.. autoattribute:: ShipmentTracking.tracking_number
.. autoattribute:: ShipmentTracking.carrier
.. autoattribute:: ShipmentTracking.tracking_url
.. autoattribute:: ShipmentTracking.state
