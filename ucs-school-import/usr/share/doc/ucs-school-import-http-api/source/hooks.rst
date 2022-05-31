Hooks
=====

The import software (both cmdline and HTTP-API) can be extended by customers through hooks. This individualization method is officially supported for the long-term and thus sustainable.

The modern Python-based PyHooks are saved in ``/usr/share/ucs-school-import/pyhooks/``. They are documented in Commandline import documentation chapter `Hooks <http://docs.software-univention.de/ucsschool-import-handbuch-4.3.html#extending:hooks>`_.

There is a collection of PyHooks in a dedicated git repository: `components/ucsschool-hooks <https://git.knut.univention.de/univention/components/ucsschool-hooks>`_.

Sequence
--------
The order in which (hook) code is executed during an import job:

.. image:: import-pyhooks.svg
   :alt: Hook execution sequence.

