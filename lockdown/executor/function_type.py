# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from lockdown.type_system.core_types import Type
from lockdown.type_system.dict_types import RDHDict
from lockdown.type_system.exceptions import FatalError


def enrich_break_type(data):
    from lockdown.executor.type_factories import enrich_type
    result = {
        "out": enrich_type(data["out"])
    }
    if "in" in data:
        result["in"] = enrich_type(data.get("in"))
    return RDHDict(result)

def are_break_types_a_subset(self, other):
    if other is None or other.break_types is None:
        raise FatalError
    for mode, other_break_types_for_mode in other.break_types.items():
        for other_break_type_for_mode in other_break_types_for_mode:
            our_break_types_for_mode = self.break_types.get(mode, None)
            if our_break_types_for_mode is None:
                return False

            for our_break_type_for_mode in our_break_types_for_mode:
                our_out = our_break_type_for_mode["out"]
                our_in = our_break_type_for_mode.get("in", None)

                other_out = other_break_type_for_mode["out"]
                other_in = other_break_type_for_mode.get("in", None)

                if our_in is not None and other_in is None:
                    continue

                out_is_compatible = our_out.is_copyable_from(other_out)
                in_is_compatible = our_in is None or other_in.is_copyable_from(our_in)

                if out_is_compatible and in_is_compatible:
                    break
            else:
                return False
    return True

class OpenFunctionType(Type):
    def __init__(self, argument_type, outer_type, break_types):
        self.argument_type = argument_type
        self.outer_type = outer_type
        self.break_types = break_types

    def is_copyable_from(self, other):
        if not isinstance(other, OpenFunctionType):
            return False
        if not other.argument_type.is_copyable_from(self.argument_type):
            return False
        if not other.outer_type.is_copyable_from(self.outer_type):
            return False
        if not are_break_types_a_subset(self, other):
            return False
        return True

class ClosedFunctionType(Type):
    def __init__(self, argument_type, break_types):
        self.argument_type = argument_type
        self.break_types = break_types
        if argument_type is None:
            raise FatalError()
        if break_types is None:
            raise FatalError()

    def is_copyable_from(self, other):
        if not isinstance(other, ClosedFunctionType):
            return False
        if not other.argument_type.is_copyable_from(self.argument_type):
            return False
        if not are_break_types_a_subset(self, other):
            are_break_types_a_subset(self, other)
            return False
        return True

    def __repr__(self):
        return "ClosedFunctionType<{} => {}>".format(self.argument_type, self.break_types)
