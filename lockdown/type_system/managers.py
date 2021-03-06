import weakref

from lockdown.type_system.core_types import Type, UnitType, NoValueType
from lockdown.type_system.exceptions import FatalError, InvalidData
from lockdown.type_system.runtime import replace_all_refs
from lockdown.utils import InternalMarker, NO_VALUE, is_debug,\
    runtime_type_information

managers_by_object_id = {}

def get_manager(obj, trigger=None):
    manager = managers_by_object_id.get(id(obj), None)
    if manager:
        return manager

    if isinstance(obj, InternalMarker):
        return None

    from lockdown.type_system.composites import Composite
    if not isinstance(obj, (list, tuple, dict, Composite)) and not hasattr(obj, "__dict__"):
        return None

    if isinstance(obj, Type):
        return None

    from lockdown.executor.function import RDHFunction, OpenFunction
    if isinstance(obj, (RDHFunction, OpenFunction)):
        return None

    from lockdown.executor.opcodes import Opcode
    if isinstance(obj, Opcode):
        return None

    from lockdown.type_system.composites import CompositeObjectManager

    old_obj = obj
    if isinstance(obj, Composite):
        manager = CompositeObjectManager(obj, obj_cleared_callback)
    elif isinstance(obj, list):
        if is_debug() and not runtime_type_information():
            raise FatalError()
        from lockdown.type_system.list_types import RDHList
        obj = RDHList(obj)
        replace_all_refs(old_obj, obj)            
        manager = CompositeObjectManager(obj, obj_cleared_callback)
    elif isinstance(obj, tuple):
        if is_debug() and not runtime_type_information():
            raise FatalError()
        from lockdown.type_system.list_types import RDHList
        obj = RDHList(obj)
        replace_all_refs(old_obj, obj)            
        manager = CompositeObjectManager(obj, obj_cleared_callback)
    elif isinstance(obj, dict):
        if is_debug() and not runtime_type_information():
            raise FatalError()
        from lockdown.type_system.dict_types import RDHDict
        obj = RDHDict(obj, debug_reason="monkey-patch")
        replace_all_refs(old_obj, obj)
        manager = CompositeObjectManager(obj, obj_cleared_callback)
    elif isinstance(obj, object) and hasattr(obj, "__dict__"):
        if is_debug() and not runtime_type_information():
            raise FatalError()
        from lockdown.type_system.object_types import RDHObject
        original_type = obj.__class__
        new_type = type("RDH{}".format(original_type.__name__), (RDHObject, original_type,), {})
        obj = new_type(obj.__dict__)
        replace_all_refs(old_obj, obj)
        manager = CompositeObjectManager(obj, obj_cleared_callback)
        manager.debug_reason = "monkey-patch"
    else:
        raise FatalError()

    managers_by_object_id[id(obj)] = manager

    return manager


def obj_cleared_callback(obj_id):
    del managers_by_object_id[obj_id]


def get_type_of_value(value):
    if isinstance(value, (basestring, int)):
        return UnitType(value)
    if value is None:
        return NoValueType()
    if value is NO_VALUE:
        return NoValueType()
    if isinstance(value, Type):
        return NoValueType()

    from lockdown.executor.function import RDHFunction, OpenFunction
    if isinstance(value, (RDHFunction, OpenFunction)):
        return value.get_type()

    manager = get_manager(value, "get_type_of_value")
    if manager:
        return manager.get_effective_composite_type()

    raise InvalidData(type(value), value)
