#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# Univention UCS@school
# SPDX-FileCopyrightText: 2016-2025 Univention GmbH
# SPDX-License-Identifier: AGPL-3.0-only

"""Singleton to the factory currently in use."""

import importlib
from typing import TYPE_CHECKING, Optional, Type  # noqa: F401

from .exceptions import InitialisationError

if TYPE_CHECKING:
    from .default_user_import_factory import DefaultUserImportFactory  # noqa: F401


def setup_factory(factory_cls_name):  # type: (str) -> DefaultUserImportFactory
    """
    Create import factory.

    :param str factory_cls_name: full dotted name of class
    :return: Factory object
    :rtype: Factory
    """
    fac_class = load_class(factory_cls_name)
    factory = Factory(fac_class())  # type: DefaultUserImportFactory
    return factory


def load_class(dotted_class_name):  # type: (str) -> type
    """
    Load class from its full dotted name.

    :param dotted_class_name: str: full dotted name of class
    :return: class
    :rtype: type
    """
    module_path, _, class_name = dotted_class_name.rpartition(".")
    module = importlib.import_module(module_path)
    return getattr(module, class_name)


class Factory(object):
    """Singleton to the global abstract factory object."""

    class __SingleFac:
        def __init__(self, factory):  # type: (Optional[DefaultUserImportFactory]) -> None
            if not factory:
                raise InitialisationError("Concrete factory not yet configured.")
            self.factory = factory

    _instance = None  # type: __SingleFac

    def __new__(cls, factory=None):
        # type: (Type[Factory], Optional[DefaultUserImportFactory]) -> DefaultUserImportFactory
        if not cls._instance:
            cls._instance = cls.__SingleFac(factory)
        return cls._instance.factory
