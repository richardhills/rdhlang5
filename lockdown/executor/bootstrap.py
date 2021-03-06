# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from time import time

from lockdown.executor.flow_control import FrameManager, \
    break_exception_to_string
from lockdown.executor.function import prepare
from lockdown.executor.opcodes import get_context_type
from lockdown.executor.raw_code_factories import inferred_type, function_lit, \
    int_type, infer_all, dereference, loop_op, comma_op, condition_op, \
    binary_integer_op, nop, list_type, \
    function_type, list_template_op, insert_op, transform_op, literal_op, \
    invoke_op, object_template_op, prepared_function, no_value_type, \
    assignment_op, dict_template_op, addition_op, reset_op, shift_op, \
    transform, local_function, map_op
from lockdown.type_system.default_composite_types import DEFAULT_OBJECT_TYPE, \
    READONLY_DEFAULT_OBJECT_TYPE
from lockdown.type_system.managers import get_manager
from lockdown.type_system.object_types import RDHObject
from lockdown.utils import NO_VALUE, print_code, MISSING


class ObjectDictWrapper(object):
    def __init__(self, data):
        for k, v in data.items():
            self.__dict__[k] = v

class BootstrapException(Exception):
    pass

def get_default_global_context():
    return RDHObject({
        "static": RDHObject({
            "any": RDHObject({
                "type": "Any"
            }, debug_reason="default-global-context"),
            "int": RDHObject({
                "type": "Integer"
            }, debug_reason="default-global-context"),
            "void": RDHObject({
                "type": "NoValue"
            }, debug_reason="default-global-context"),
            "var": RDHObject({
                "type": "Inferred"
            }, debug_reason="default-global-context"),
            "range": prepare(
                function_lit(
                    list_type([ int_type(), int_type() ], None),
                    infer_all(), int_type(), dereference("argument.0"),
                    prepared_function(
                        loop_op(
                            condition_op(
                                binary_integer_op("lt", dereference("outer.local"), dereference("outer.argument.1")),
                                comma_op(
                                    shift_op(dereference("outer.local"), no_value_type()),
                                    assignment_op(dereference("outer"), literal_op("local"), addition_op(dereference("outer.local"), literal_op(1)))
                                ),
                                transform_op("break")
                            )
                        )
                    )
                ),
                None, FrameManager()
            ).close(None),
            "list": prepare(
                function_lit(
                    list_type([
                        function_type(no_value_type(), {
                            "yield": list_template_op([ dict_template_op({
                                "in": no_value_type(),
                                "out": int_type()
                            })]),
                            "value": list_template_op([ dict_template_op({
                                "out": no_value_type()
                            })]),
                        }),
                    ], None),
                    infer_all(),
                    inferred_type(),
                    dereference("argument.0"),
                    loop_op(
                        invoke_op(
                            local_function(
                                transform(
                                    ("yield", "value"),
                                    ("value", "end"),
                                    reset_op(dereference("outer.local"), nop())
                                ),
                                comma_op(
                                    assignment_op(
                                        dereference("outer"),
                                        literal_op("local"),
                                        dereference("local.continuation")
                                    ),
                                    transform_op(
                                        "value",
                                        "continue",
                                        dereference("local.value")
                                    )
                                )
                            )
                        )
                    )
                ),
                None, FrameManager()
            ).close(None),
            "max": prepare(
                function_lit(
                    list_type([ int_type() ], int_type()),
                    infer_all(),
                    inferred_type(),
                    dereference("argument.0"),
                    map_op(
                        dereference("argument"),
                        prepared_function(
                            int_type(),
                            condition_op(
                                binary_integer_op(
                                    "gt",
                                    dereference("argument"),
                                    dereference("outer.local")
                                ),
                                assignment_op(
                                    dereference("outer"),
                                    literal_op("local"),
                                    dereference("argument")
                                ),
                                nop()
                            )
                        )
                    )
                ),
                None, FrameManager()
            ).close(None),
        }, debug_reason="default-global-context")
    }, bind=READONLY_DEFAULT_OBJECT_TYPE, debug_reason="default-global-context")

def format_unhandled_break_type(break_type, raw_code):
    if not raw_code:
        return str(break_type) + " (no raw code)"

    out_break_type = break_type["out"]

    opcode = getattr(out_break_type, "from_opcode", None)
    if not opcode:
        return str(break_type) + " (break_type has no from_opcode)"

    line, column = opcode.get_line_and_column()

    if line is None or column is None:
        return str(break_type) + " (no line and column)"

    lines = raw_code.split("\n")

    padding = " " * column

    return """
{}
{}^
{}| {}""".format(lines[line - 1], padding, padding, str(out_break_type))

def raise_unhandled_break_types(open_function, data):
    function_break_types = open_function.get_type().break_types

    error_msgs = []

    for mode, break_types in function_break_types.items():
        if mode not in ("exit", "return", "value"):
            breaks_messages = [format_unhandled_break_type(break_type, getattr(data, "raw_code", None)) for break_type in break_types]
            for break_message in breaks_messages:
                error_msgs.append("""---- break mode {} is not safe ----

{}""".format(mode, break_message))
            continue

    if error_msgs:
        raise BootstrapException("\n\n".join(error_msgs))

def format_unhandled_break(mode, value, caused_by, opcode, data):
    raw_code = getattr(data, "raw_code", None)

    break_str = break_exception_to_string(mode, value, caused_by)

    if not raw_code:
        return break_str + " (no raw code)"

    if not opcode:
        return break_str + " (break_exception has no from_opcode)"

    line, column = opcode.get_line_and_column()

    if line is None or column is None:
        return break_str + " (no line and column)"

    lines = raw_code.split("\n")

    padding = " " * column

    return """
{}
{}^
{}| {}""".format(lines[line - 1], padding, padding, break_str)

def raise_unhandled_break(mode, value, caused_by, opcode, data):
    raise BootstrapException(format_unhandled_break(mode, value, caused_by, opcode, data))

def bootstrap_function(data, argument=None, context=None, check_safe_exit=False, transpile=False, measure=False, print_ast=False):
    if argument is None:
        argument = NO_VALUE
    if context is None:
        context = get_default_global_context()

    get_manager(context).add_composite_type(READONLY_DEFAULT_OBJECT_TYPE)

    frame_manager = FrameManager()

    with frame_manager.capture() as capture_preparation:
        if print_ast:
            print_code(data)
        open_function = prepare(
            data,
            context,
            frame_manager,
            immediate_context={
                "suggested_outer_type": get_context_type(context)
            }
        )

        if check_safe_exit:
            raise_unhandled_break_types(open_function, data)

        closed_function = open_function.close(context)

    if capture_preparation.caught_break_mode is not MISSING:
        raise_unhandled_break(capture_preparation.caught_break_mode, capture_preparation.value, None, capture_preparation.opcode, data)

    with frame_manager.capture() as capture_result:
        if transpile:
            closed_function = closed_function.transpile()

        if measure:
            start = time()

        capture_result.attempt_capture_or_raise(*closed_function.invoke(argument, frame_manager))

        if measure:
            end = time()
            print end - start

    return capture_result
