Hooks
=====

The import software (both cmdline and HTTP-API) can be extended by customers through hooks. This individualization method is officially supported for the long-term and thus sustainable.

All versions of the user import support saving executables in directories below ``/usr/share/ucs-school-import/hooks/``. The directories are named after the objects that are changed and the situation in which they should run.

Those hooks, while still being supported, are deprecated. Documentation for them can be found in the UCS\@school administrator manual in chapter `Pre- und Post-Hook-Skripte für den Import <http://docs.software-univention.de/ucsschool-handbuch-4.3.html#import>`_.

The modern Python-based PyHooks are saved in ``/usr/share/ucs-school-import/pyhooks/``. They are documented in Commandline import documentation chapter `Hooks <http://docs.software-univention.de/ucsschool-import-handbuch-4.3.html#extending:hooks>`_.

There is a collection of hooks (both legacy and PyHooks) in a dedicated git repository: `components/ucsschool-hooks <https://git.knut.univention.de/univention/components/ucsschool-hooks>`_.

Sequence
--------
The order in which (hook) code is executed during an import job:

.. image:: import-pyhooks.svg
   :alt: Hook execution sequence.

