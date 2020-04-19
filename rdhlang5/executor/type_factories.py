from rdhlang5.executor.exceptions import PreparationException
from rdhlang5_types.core_types import AnyType, OneOfType, IntegerType, \
    NoValueType, StringType, UnitType, BooleanType
from rdhlang5_types.list_types import RDHListType
from rdhlang5_types.object_types import RDHObjectType, RDHObject


TYPES = {
    "Any": lambda data: AnyType(),
    "Object": lambda data: RDHObjectType({
        name: enrich_type(type) for name, type in data.properties.__dict__.items()
    }),
    "List": lambda data: RDHListType(
        [ enrich_type(type) for type in data["entry_types"] ],
        enrich_type(data["wildcard_type"])
    ),
    "OneOf": lambda data: OneOfType(
        [ enrich_type(type) for type in data["types"] ],
        
    ),
    "Integer": lambda data: IntegerType(),
    "Boolean": lambda data: BooleanType(),
    "NoValue": lambda data: NoValueType(),
    "String": lambda data: StringType(),
    "Unit": lambda data: UnitType(data["value"])
}


def enrich_type(data):
    if not isinstance(data, RDHObject):
        raise PreparationException("Unknown type data {}, {}".format(data, type(data)))
    if not hasattr(data, "type"):
        raise PreparationException("Missing type in data {}".format(data))
    if data.type not in TYPES:
        raise PreparationException("Unknown type {}".format(data["type"]))

    return TYPES[data.type](data)
