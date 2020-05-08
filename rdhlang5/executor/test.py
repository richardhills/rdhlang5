from unittest import main
from unittest.case import TestCase

from rdhlang5.executor.bootstrap import bootstrap_function, prepare, \
    create_application_flow_manager, create_no_escape_flow_manager
from rdhlang5.executor.exceptions import PreparationException
from rdhlang5.executor.raw_code_factories import function_lit, literal_op, \
    no_value_type, return_op, int_type, addition_op, dereference_op, context_op, \
    comma_op, yield_op, any_type, build_break_types, assignment_op, nop, \
    object_template_op, object_type, unit_type, loop_op, condition_op, \
    equality_op, inferred_type, infer_all, invoke_op, prepare_op, function_type, \
    dereference, prepared_function, unbound_dereference, match_op, one_of_type, \
    string_type, bool_type, try_catch_op, throw_op, const_string_type
from rdhlang5_types.core_types import AnyType, IntegerType, StringType
from rdhlang5_types.default_composite_types import DEFAULT_OBJECT_TYPE, \
    rich_composite_type
from rdhlang5_types.list_types import RDHList, RDHListType
from rdhlang5_types.managers import get_manager
from rdhlang5_types.object_types import RDHObject, RDHObjectType
from rdhlang5_types.utils import NO_VALUE


class TestPreparedFunction(TestCase):
    def test_basic_function(self):
        func = function_lit(
            no_value_type, build_break_types(value_type=int_type), literal_op(42)
        )

        result = bootstrap_function(func)

        self.assertEquals(result.mode, "value")
        self.assertEquals(result.value, 42)


    def test_basic_function_return(self):
        func = function_lit(no_value_type, build_break_types(int_type), return_op(literal_op(42)))

        result = bootstrap_function(func, check_safe_exit=True)

        self.assertEquals(result.mode, "return")
        self.assertEquals(result.value, 42)

    def test_addition(self):
        func = function_lit(no_value_type, build_break_types(int_type), return_op(addition_op(literal_op(40), literal_op(2))))

        result = bootstrap_function(func, check_safe_exit=True)

        self.assertEquals(result.mode, "return")
        self.assertEquals(result.value, 42)

class TestDereference(TestCase):
    def test_return_variable(self):
        func = function_lit(
            no_value_type, build_break_types(int_type),
            return_op(
                dereference_op(
                    dereference_op(
                        context_op(),
                        literal_op("outer")
                    ),
                    literal_op("local")
                )
            )
        )

        context = RDHObject({
            "local": 42,
            "types": RDHObject({
                "local": IntegerType()
            })
        }, bind=RDHObjectType({
            "local": IntegerType(),
            "types": DEFAULT_OBJECT_TYPE
        }, wildcard_type=rich_composite_type))

        result = bootstrap_function(func, context=context, check_safe_exit=True)

        self.assertEquals(result.mode, "return")
        self.assertEquals(result.value, 42)


    def test_add_locals(self):
        func = function_lit(
            no_value_type, build_break_types(int_type),
            return_op(
                addition_op(
                    dereference_op(
                        dereference_op(
                            dereference_op(
                                context_op(),
                                literal_op("outer")
                            ),
                            literal_op("local")
                        ),
                        literal_op(0)
                    ),
                    dereference_op(
                        dereference_op(
                            dereference_op(
                                context_op(),
                                literal_op("outer")
                            ),
                            literal_op("local")
                        ),
                        literal_op(1)
                    )
                )
            )
        )

        context = RDHObject({
            "local": RDHList([ 39, 3 ]),
            "types": RDHObject({
                "local": RDHListType([ IntegerType(), IntegerType() ], None)
            })
        }, bind=RDHObjectType({
            "local": RDHListType([ IntegerType(), IntegerType() ], None),
            "types": DEFAULT_OBJECT_TYPE
        }, wildcard_type=rich_composite_type))

        result = bootstrap_function(func, context=context, check_safe_exit=True)

        self.assertEquals(result.mode, "return")
        self.assertEquals(result.value, 42)

class TestComma(TestCase):
    def test_comma(self):
        result = bootstrap_function(
            function_lit(
                no_value_type, build_break_types(int_type),
                return_op(comma_op(literal_op(5), literal_op(8), literal_op(42)))
            ),
            check_safe_exit=True
        )

        self.assertEquals(result.mode, "return")
        self.assertEquals(result.value, 42)

    def test_restart_comma(self):
        context = RDHObject({})
        flow_manager = create_application_flow_manager()

        func = prepare(
            function_lit(
                no_value_type, build_break_types(int_type, yield_types={ "out": any_type, "in": int_type }),
                return_op(comma_op(
                    literal_op(5),
                    yield_op(literal_op("first"), int_type),
                    yield_op(literal_op("second"), int_type)
                ))
            ),
            context, create_no_escape_flow_manager()
        )

        first_yielder = flow_manager.capture("yield", { "out": AnyType(), "in": IntegerType() }, lambda new_fm: func.invoke(NO_VALUE, context, new_fm))
        self.assertEquals(first_yielder.result, "first")

        second_yielder = flow_manager.capture("yield", { "out": AnyType(), "in": IntegerType() }, lambda new_fm: first_yielder.restart_continuation.invoke(4, context, new_fm))
        self.assertEquals(second_yielder.result, "second")

        returner = flow_manager.capture("return", { "out": AnyType() }, lambda new_fm: second_yielder.restart_continuation.invoke(42, context, new_fm))

        self.assertEquals(returner.result, 42)

class TestTemplates(TestCase):
    def test_return(self):
        result = bootstrap_function(
            function_lit(
                no_value_type, build_break_types(object_type({ "foo": int_type })),
                comma_op(
                    return_op(object_template_op({ "foo": literal_op(42) }))
                )
            ),
            check_safe_exit=True
        )

        self.assertEquals(result.mode, "return")
        self.assertTrue(isinstance(result.value, RDHObject))
        get_manager(result.value).add_composite_type(DEFAULT_OBJECT_TYPE)
        self.assertEquals(result.value.foo, 42)

    def test_nested_return(self):
        result = bootstrap_function(
            function_lit(
                no_value_type, build_break_types(object_type({ "foo": object_type({ "bar": int_type }) })),
                comma_op(
                    return_op(object_template_op({ "foo": object_template_op({ "bar": literal_op(42) }) }))
                )
            ),
            check_safe_exit=True
        )

        self.assertEquals(result.mode, "return")
        self.assertTrue(isinstance(result.value, RDHObject))
        get_manager(result.value).add_composite_type(DEFAULT_OBJECT_TYPE)
        self.assertEquals(result.value.foo.bar, 42)

    def test_return_with_dereference1(self):
        result = bootstrap_function(
            function_lit(
                int_type, build_break_types(object_type({ "foo": unit_type(42), "bar": any_type })),
                comma_op(
                    return_op(object_template_op({ "foo": literal_op(42), "bar": dereference_op(context_op(), literal_op("argument")) }))
                )
            ),
            argument=42,
            check_safe_exit=True
        )

        self.assertEquals(result.mode, "return")
        self.assertTrue(isinstance(result.value, RDHObject))
        get_manager(result.value).add_composite_type(DEFAULT_OBJECT_TYPE)
        self.assertEquals(result.value.foo, 42)
        self.assertEquals(result.value.bar, 42)

    def test_return_with_dereference2(self):
        result = bootstrap_function(
            function_lit(
                int_type, build_break_types(object_type({ "foo": unit_type(42), "bar": int_type })),
                comma_op(
                    return_op(object_template_op({ "foo": literal_op(42), "bar": dereference_op(context_op(), literal_op("argument")) }))
                )
            ),
            argument=42,
            check_safe_exit=True
        )

        self.assertEquals(result.mode, "return")
        self.assertTrue(isinstance(result.value, RDHObject))
        get_manager(result.value).add_composite_type(DEFAULT_OBJECT_TYPE)
        self.assertEquals(result.value.foo, 42)
        self.assertEquals(result.value.bar, 42)

    def test_return_with_dereference3(self):
        result = bootstrap_function(
            function_lit(
                int_type, build_break_types(object_type({ "foo": int_type, "bar": any_type })),
                comma_op(
                    return_op(object_template_op({ "foo": literal_op(42), "bar": dereference_op(context_op(), literal_op("argument")) }))
                )
            ),
            argument=42,
            check_safe_exit=True
        )

        self.assertEquals(result.mode, "return")
        self.assertTrue(isinstance(result.value, RDHObject))
        get_manager(result.value).add_composite_type(DEFAULT_OBJECT_TYPE)
        self.assertEquals(result.value.foo, 42)
        self.assertEquals(result.value.bar, 42)

    def test_return_with_dereference4(self):
        result = bootstrap_function(
            function_lit(
                int_type, build_break_types(object_type({ "foo": any_type, "bar": any_type })),
                comma_op(
                    return_op(object_template_op({ "foo": literal_op(42), "bar": dereference_op(context_op(), literal_op("argument")) }))
                )
            ),
            argument=42,
            check_safe_exit=True
        )

        self.assertEquals(result.mode, "return")
        self.assertTrue(isinstance(result.value, RDHObject))
        get_manager(result.value).add_composite_type(DEFAULT_OBJECT_TYPE)
        self.assertEquals(result.value.foo, 42)
        self.assertEquals(result.value.bar, 42)

    def test_return_with_dereference5(self):
        with self.assertRaises(Exception):
            bootstrap_function(
                function_lit(
                    int_type, build_break_types(object_type({ "foo": any_type, "bar": unit_type(42) })),
                    return_op(object_template_op({ "foo": literal_op(42), "bar": dereference_op(context_op(), literal_op("argument")) }))
                ),
                argument=42,
                check_safe_exit=True
            )

    def test_return_rev_const_and_inferred(self):
        result = bootstrap_function(
            function_lit(
                no_value_type,
                comma_op(
                    return_op(object_template_op({ "foo": object_template_op({ "bar": literal_op(42) }) }))
                )
            ),
            check_safe_exit=True
        )

        self.assertEquals(result.mode, "return")
        self.assertTrue(isinstance(result.value, RDHObject))
        get_manager(result.value).add_composite_type(DEFAULT_OBJECT_TYPE)
        self.assertEquals(result.value.foo.bar, 42)

class TestLocals(TestCase):
    def test_initialization(self):
        result = bootstrap_function(
            function_lit(
                no_value_type, build_break_types(int_type), int_type, literal_op(42),
                comma_op(
                    return_op(dereference_op(context_op(), literal_op("local")))
                )
            ),
            check_safe_exit=True
        )

        self.assertEquals(result.mode, "return")
        self.assertEquals(result.value, 42)

    def test_initialization_from_argument(self):
        result = bootstrap_function(
            function_lit(
                int_type, build_break_types(int_type), int_type, dereference_op(context_op(), literal_op("argument")),
                comma_op(
                    return_op(dereference_op(context_op(), literal_op("local")))
                )
            ),
            argument=123,
            check_safe_exit=True
        )

        self.assertEquals(result.mode, "return")
        self.assertEquals(result.value, 123)

    def test_restart_into_local_initialization(self):
        context = RDHObject({})
        flow_manager = create_application_flow_manager()

        func = prepare(
            function_lit(
                no_value_type, build_break_types(any_type, yield_types={ "out": any_type, "in": int_type }),
                int_type, yield_op(literal_op("hello"), int_type),
                return_op(dereference_op(context_op(), literal_op("local")))
            ),
            context, create_no_escape_flow_manager()
        )

        yielder = flow_manager.capture("yield", { "out": AnyType(), "in": IntegerType() }, lambda new_fm: func.invoke(NO_VALUE, context, new_fm))

        self.assertEquals(yielder.result, "hello")

        returner = flow_manager.capture("return", { "out": AnyType() }, lambda new_fm: yielder.restart_continuation.invoke(32, context, new_fm))

        self.assertEquals(returner.result, 32)

    def test_restart_into_local_initialization_and_code(self):
        context = RDHObject({})
        flow_manager = create_application_flow_manager()

        func = prepare(
            function_lit(
                no_value_type, build_break_types(any_type, yield_types={ "out": any_type, "in": int_type }),
                int_type, yield_op(literal_op("first"), int_type),
                return_op(addition_op(dereference_op(context_op(), literal_op("local")), yield_op(literal_op("second"), int_type)))
            ),
            context, create_no_escape_flow_manager()
        )

        first_yielder = flow_manager.capture("yield", { "out": AnyType(), "in": IntegerType() }, lambda new_fm: func.invoke(NO_VALUE, context, new_fm))
        self.assertEquals(first_yielder.result, "first")
        second_yielder = flow_manager.capture("yield", { "out": AnyType(), "in": IntegerType() }, lambda new_fm: first_yielder.restart_continuation.invoke(40, context, new_fm))
        self.assertEquals(second_yielder.result, "second")

        returner = flow_manager.capture("return", { "out": AnyType() }, lambda new_fm: second_yielder.restart_continuation.invoke(2, context, new_fm))

        self.assertEquals(returner.result, 42)

class TestAssignment(TestCase):
    def test_assignment(self):
        result = bootstrap_function(
            function_lit(
                no_value_type, build_break_types(int_type), int_type, literal_op(0),
                comma_op(
                    assignment_op(context_op(), literal_op("local"), literal_op(42)),
                    return_op(dereference_op(context_op(), literal_op("local")))
                )
            ),
            check_safe_exit=True
        )

        self.assertEquals(result.mode, "return")
        self.assertEquals(result.value, 42)

    def test_assignment_from_argument(self):
        result = bootstrap_function(
            function_lit(
                int_type, build_break_types(int_type), int_type, literal_op(0),
                comma_op(
                    assignment_op(context_op(), literal_op("local"), dereference_op(context_op(), literal_op("argument"))),
                    return_op(dereference_op(context_op(), literal_op("local")))
                )
            ),
            argument=43,
            check_safe_exit=True
        )

        self.assertEquals(result.mode, "return")
        self.assertEquals(result.value, 43)

class TestArguments(TestCase):
    def test_simple_return_argument(self):
        func = function_lit(
            int_type, build_break_types(int_type),
            return_op(dereference_op(context_op(), literal_op("argument")))
        )

        result = bootstrap_function(func, argument=42, check_safe_exit=True)

        self.assertEquals(result.mode, "return")
        self.assertEquals(result.value, 42)

    def test_doubler(self):
        func = function_lit(
            int_type, build_break_types(int_type),
            return_op(addition_op(dereference_op(context_op(), literal_op("argument")), dereference_op(context_op(), literal_op("argument"))))
        )

        result = bootstrap_function(func, argument=21, check_safe_exit=True)

        self.assertEquals(result.mode, "return")
        self.assertEquals(result.value, 42)

class TestConditional(TestCase):
    def test_basic_truth(self):
        result = bootstrap_function(
            function_lit(
                no_value_type, build_break_types(int_type),
                return_op(condition_op(literal_op(True), literal_op(34), literal_op(53)))
            ), check_safe_exit=True
        )
        self.assertEquals(result.mode, "return")
        self.assertEquals(result.value, 34)

    def test_basic_false(self):
        result = bootstrap_function(
            function_lit(
                no_value_type, build_break_types(int_type),
                return_op(condition_op(literal_op(False), literal_op(34), literal_op(53)))
            ), check_safe_exit=True
        )
        self.assertEquals(result.mode, "return")
        self.assertEquals(result.value, 53)


class TestLoops(TestCase):
    def test_immediate_return(self):
        result = bootstrap_function(
            function_lit(
                no_value_type, build_break_types(int_type),
                loop_op(return_op(literal_op(42)))
            ), check_safe_exit=True
        )

        self.assertEquals(result.mode, "return")
        self.assertEquals(result.value, 42)

    def test_count_then_return(self):
        result = bootstrap_function(
            function_lit(
                no_value_type, build_break_types(int_type), int_type, literal_op(0),
                loop_op(
                    comma_op(
                        assignment_op(
                            context_op(), literal_op("local"),
                            addition_op(dereference_op(context_op(), literal_op("local")), literal_op(1))
                        ),
                        condition_op(equality_op(
                            dereference_op(context_op(), literal_op("local")), literal_op(42)
                        ), return_op(dereference_op(context_op(), literal_op("local"))), nop)
                    )
                )
            ), check_safe_exit=True
        )

        self.assertEquals(result.mode, "return")
        self.assertEquals(result.value, 42)

class TestInferredBreakTypes(TestCase):
    def test_basic_inferrence(self):
        result = bootstrap_function(
            function_lit(
                no_value_type, build_break_types(inferred_type),
                return_op(literal_op(42))
            ), check_safe_exit=True
        )

        self.assertEquals(result.mode, "return")
        self.assertEquals(result.value, 42)

    def test_infer_all(self):
        result = bootstrap_function(
            function_lit(
                no_value_type, infer_all(), return_op(literal_op(42))
            ), check_safe_exit=True
        )

        self.assertEquals(result.mode, "return")
        self.assertEquals(result.value, 42)

    def test_infer_exception(self):
        result = bootstrap_function(
            function_lit(
                no_value_type, infer_all(), addition_op(literal_op("hello"), literal_op(5))
            )
        )

        self.assertEquals(result.mode, "exception")
        self.assertEquals(result.value.type, "TypeError")

    def test_without_infer_exception_fails(self):
        with self.assertRaises(Exception):
            bootstrap_function(
                function_lit(
                    no_value_type, build_break_types(int_type), addition_op(literal_op("hello"), literal_op(5))
                )
            )

class TestFunctionPreparation(TestCase):
    def test_basic(self):
        result = bootstrap_function(
            function_lit(
                no_value_type, build_break_types(int_type),
                return_op(invoke_op(prepare_op(literal_op(function_lit(
                    no_value_type, build_break_types(int_type), return_op(literal_op(42))
                )))))
            )
        )

        self.assertEquals(result.mode, "return")
        self.assertEquals(result.value, 42)

class TestFunctionInvocation(TestCase):
    def test_basic(self):
        result = bootstrap_function(
            function_lit(
                no_value_type, build_break_types(int_type),
                function_type(no_value_type, build_break_types(int_type)),
                prepare_op(literal_op(function_lit(
                    no_value_type, build_break_types(int_type), return_op(literal_op(42))
                ))),
                return_op(invoke_op(dereference_op(context_op(), literal_op("local"))))
            ), check_safe_exit=True
        )

        self.assertEquals(result.mode, "return")
        self.assertEquals(result.value, 42)

    def test_basic_with_inferred_types(self):
        result = bootstrap_function(
            function_lit(
                no_value_type, infer_all(),
                function_type(no_value_type, build_break_types(int_type)),
                prepare_op(literal_op(function_lit(
                    no_value_type, infer_all(), return_op(literal_op(42))
                ))),
                return_op(invoke_op(dereference_op(context_op(), literal_op("local"))))
            ), check_safe_exit=True
        )

        self.assertEquals(result.mode, "return")
        self.assertEquals(result.value, 42)

    def test_basic_with_inferred_local_type(self):
        result = bootstrap_function(
            function_lit(
                no_value_type, infer_all(),
                inferred_type,
                prepare_op(literal_op(function_lit(
                    no_value_type, infer_all(), return_op(literal_op(42))
                ))),
                return_op(invoke_op(dereference_op(context_op(), literal_op("local"))))
            ), check_safe_exit=True
        )

        self.assertEquals(result.mode, "return")
        self.assertEquals(result.value, 42)

class TestUnboundReference(TestCase):
    def test_unbound_reference_to_arguments(self):
        result = bootstrap_function(
            function_lit(
                object_type({ "foo": int_type, "bar": int_type }), infer_all(),
                return_op(addition_op(
                    unbound_dereference("foo"), unbound_dereference("bar")
                ))
            ), check_safe_exit=True, argument=RDHObject({ "foo": 39, "bar": 3 })
        )

        self.assertEquals(result.mode, "return")
        self.assertEquals(result.value, 42)

    def test_unbound_reference_to_locals(self):
        result = bootstrap_function(
            function_lit(
                no_value_type, infer_all(),
                object_type({ "foo": int_type, "bar": int_type }),
                object_template_op({ "foo": literal_op(39), "bar": literal_op(3) }),
                return_op(addition_op(
                    unbound_dereference("foo"), unbound_dereference("bar")
                ))
            ), check_safe_exit=True
        )

        self.assertEquals(result.mode, "return")
        self.assertEquals(result.value, 42)

    def test_unbound_reference_to_locals_and_arguments(self):
        result = bootstrap_function(
            function_lit(
                object_type({ "foo": int_type }), infer_all(),
                object_type({ "bar": int_type }),
                object_template_op({ "bar": literal_op(3) }),
                return_op(addition_op(
                    unbound_dereference("foo"), unbound_dereference("bar")
                ))
            ), check_safe_exit=True, argument=RDHObject({ "foo": 39 })
        )

        self.assertEquals(result.mode, "return")
        self.assertEquals(result.value, 42)

class TestMatch(TestCase):
    def test_interesting(self):
        func = function_lit(
            any_type, infer_all(),
            match_op(
                dereference("argument"), [
                    prepared_function(
                        object_type({
                            "foo": int_type
                        }),
                        return_op(addition_op(dereference("argument.foo"), literal_op(3)))
                    ),
                    prepared_function(
                        any_type,
                        return_op(literal_op("invalid"))
                    )
                ]
            )
        )

        result = bootstrap_function(
            func, check_safe_exit=True, argument=RDHObject({ "foo": 39 })
        )

        self.assertEquals(result.mode, "return")
        self.assertEquals(result.value, 42)

        result = bootstrap_function(
            func, check_safe_exit=True, argument=RDHObject({ "foo": "hello" })
        )

        self.assertEquals(result.mode, "return")
        self.assertEquals(result.value, "invalid")

    def test_to_string_from_int(self):
        func = function_lit(
            any_type,
            return_op(
                match_op(
                    dereference("argument"), [
                        prepared_function(
                            unit_type(1),
                            literal_op("one")
                        ),
                        prepared_function(
                            unit_type(2),
                            literal_op("two")
                        ),
                        prepared_function(
                            unit_type(3),
                            literal_op("three")
                        ),
                        prepared_function(
                            unit_type(4),
                            literal_op("four")
                        ),
                        prepared_function(
                            any_type,
                            literal_op("invalid")
                        )
                    ]
                )
            )
        )

        result = bootstrap_function(func, check_safe_exit=True, argument=1)
        self.assertEquals(result.mode, "return")
        self.assertEquals(result.value, "one")
        result = bootstrap_function(func, check_safe_exit=True, argument=2)
        self.assertEquals(result.mode, "return")
        self.assertEquals(result.value, "two")
        result = bootstrap_function(func, check_safe_exit=True, argument=3)
        self.assertEquals(result.mode, "return")
        self.assertEquals(result.value, "three")
        result = bootstrap_function(func, check_safe_exit=True, argument=4)
        self.assertEquals(result.mode, "return")
        self.assertEquals(result.value, "four")
        result = bootstrap_function(func, check_safe_exit=True, argument=5)
        self.assertEquals(result.mode, "return")
        self.assertEquals(result.value, "invalid")


    def test_to_match_with_one_of_type_combo(self):
        func = function_lit(
            one_of_type([ string_type, int_type, bool_type ]),
            return_op(
                match_op(
                    dereference("argument"), [
                        prepared_function(
                            int_type,
                            literal_op("int is not a string")
                        ),
                        prepared_function(
                            bool_type,
                            literal_op("bool is not a string")
                        ),
                        prepared_function(
                            inferred_type,
                            dereference("argument")
                        )
                    ]
                )
            )
        )

        result = bootstrap_function(func, check_safe_exit=True, argument=2)
        self.assertEquals(result.mode, "return")
        self.assertEquals(result.value, "int is not a string")
        result = bootstrap_function(func, check_safe_exit=True, argument=True)
        self.assertEquals(result.mode, "return")
        self.assertEquals(result.value, "bool is not a string")
        result = bootstrap_function(func, check_safe_exit=True, argument="hello world")
        self.assertEquals(result.mode, "return")
        self.assertEquals(result.value, "hello world")

        prepared_func = prepare(func, RDHObject({}), create_no_escape_flow_manager())
        self.assertEquals(len(prepared_func.break_types), 1)
        self.assertTrue("return" in prepared_func.break_types)
        for return_break_type in prepared_func.break_types["return"]:
            self.assertTrue(StringType().is_copyable_from(return_break_type["out"]))

class TestTryCatch(TestCase):
    def test_slightly_strange_try_catch(self):
        # Function either throws the same string back at you, or returns an int +1
        func = function_lit(
            one_of_type([ string_type, int_type ]),
            try_catch_op(
                throw_op(dereference("argument")),
                prepared_function(int_type, return_op(addition_op(literal_op(1), dereference("argument")))),
                nop
            )
        )
        result = bootstrap_function(func, argument="hello world")
        self.assertEquals(result.mode, "exception")
        self.assertEquals(result.value, "hello world")
        result = bootstrap_function(func, argument=41)
        self.assertEquals(result.mode, "return")
        self.assertEquals(result.value, 42)

    def test_silly_tostring_casing(self):
        func = function_lit(
            any_type,
            try_catch_op(
                return_op(
                    match_op(
                        dereference("argument"), [
                            prepared_function(
                                unit_type(1),
                                literal_op("one")
                            ),
                            prepared_function(
                                unit_type(2),
                                literal_op("two")
                            ),
                            prepared_function(
                                int_type,
                                throw_op(object_template_op({
                                    "type": literal_op("UnknownInt")
                                }))
                            ),
                            prepared_function(
                                any_type,
                                throw_op(object_template_op({
                                    "type": literal_op("TypeError")
                                }))
                            )
                        ]
                    )
                ),
                prepared_function(
                    object_type({ "type": unit_type("UnknownInt") }),
                    return_op(literal_op("unknown"))
                )
            )
        )

        result = bootstrap_function(func, argument=1)
        self.assertEquals(result.mode, "return")
        self.assertEquals(result.value, "one")
        result = bootstrap_function(func, argument=2)
        self.assertEquals(result.mode, "return")
        self.assertEquals(result.value, "two")
        result = bootstrap_function(func, argument=3)
        self.assertEquals(result.mode, "return")
        self.assertEquals(result.value, "unknown")
        result = bootstrap_function(func, argument="hello")
        self.assertEquals(result.mode, "exception")
        self.assertIsInstance(result.value, RDHObject)
        self.assertEquals(result.value.type, "TypeError")


    def test_catch_real_exception(self):
        #  Function safely handles an internal exception
        func = function_lit(
            try_catch_op(
                dereference_op(context_op(), literal_op("foo")),
                prepared_function(
                    object_type({
                        "type": const_string_type(),
                        "message": const_string_type(),
                    }),
                    return_op(dereference("argument.message"))
                ),
                nop
            )
        )
        result = bootstrap_function(func, check_safe_exit=True)
        self.assertEquals(result.mode, "return")
        self.assertEquals(result.value, "DereferenceOpcode: invalid_dereference")


class TestUtilityMethods(TestCase):
    def test_misc1(self):
        result = bootstrap_function(
            function_lit(
                no_value_type, infer_all(),
                object_type({ "foo": int_type, "bar": int_type }),
                object_template_op({ "foo": literal_op(39), "bar": literal_op(3) }),
                return_op(addition_op(
                    dereference("local.foo"), dereference("local.bar")
                ))
            ), check_safe_exit=True
        )

        self.assertEquals(result.mode, "return")
        self.assertEquals(result.value, 42)

    def test_misc2(self):
        result = bootstrap_function(
            function_lit(
                no_value_type, infer_all(),
                inferred_type,
                prepared_function(
                    object_type({ "foo": int_type, "bar": int_type }),
                    return_op(addition_op(
                        dereference("argument.foo"), dereference("argument.bar")
                    ))
                ),
                return_op(invoke_op(
                    dereference("local"),
                    object_template_op({ "foo": literal_op(39), "bar": literal_op(3) }),
                ))
            ), check_safe_exit=True
        )

        self.assertEquals(result.mode, "return")
        self.assertEquals(result.value, 42)

    def test_fizzbuzz(self):
        pass

class TestContinuations(TestCase):
    def test_single_restart(self):
        context = RDHObject({})
        flow_manager = create_application_flow_manager()

        func = prepare(
            function_lit(
                no_value_type, build_break_types(any_type, yield_types={ "out": any_type, "in": int_type }),
                return_op(addition_op(yield_op(literal_op("hello"), int_type), literal_op(40)))
            ),
            context, create_no_escape_flow_manager()
        )

        yielder = flow_manager.capture("yield", { "out": AnyType(), "in": IntegerType() }, lambda new_fm: func.invoke(NO_VALUE, context, new_fm))

        self.assertEquals(yielder.result, "hello")

        returner = flow_manager.capture("return", { "out": AnyType() }, lambda new_fm: yielder.restart_continuation.invoke(2, context, new_fm))

        self.assertEquals(returner.result, 42)

    def test_repeated_restart(self):
        context = RDHObject({})
        flow_manager = create_application_flow_manager()

        func = prepare(
            function_lit(
                no_value_type, build_break_types(int_type, yield_types={ "out": any_type, "in": int_type }),
                return_op(addition_op(yield_op(literal_op("first"), int_type), yield_op(literal_op("second"), int_type)))
            ),
            context, create_no_escape_flow_manager()
        )

        first_yielder = flow_manager.capture("yield", { "out": AnyType(), "in": IntegerType() }, lambda new_fm: func.invoke(NO_VALUE, context, new_fm))
        self.assertEquals(first_yielder.result, "first")

        second_yielder = flow_manager.capture("yield", { "out": AnyType(), "in": IntegerType() }, lambda new_fm: first_yielder.restart_continuation.invoke(39, context, new_fm))
        self.assertEquals(second_yielder.result, "second")

        returner = flow_manager.capture("return", { "out": AnyType() }, lambda new_fm: second_yielder.restart_continuation.invoke(3, context, new_fm))

        self.assertEquals(returner.result, 42)

    def test_repeated_restart_with_outer_return_handling(self):
        context = RDHObject({})
        flow_manager = create_application_flow_manager()

        func = prepare(
            function_lit(
                no_value_type, build_break_types(int_type, yield_types={ "out": any_type, "in": int_type }),
                return_op(addition_op(yield_op(literal_op("first"), int_type), yield_op(literal_op("second"), int_type)))
            ),
            context, create_no_escape_flow_manager()
        )

        with flow_manager.capture("return", { "out": AnyType() }) as returner:
            first_yielder = returner.capture("yield", { "out": AnyType(), "in": IntegerType() }, lambda new_bm: func.invoke(NO_VALUE, context, new_bm))
            self.assertEquals(first_yielder.result, "first")

            second_yielder = returner.capture("yield", { "out": AnyType(), "in": IntegerType() }, lambda new_bm: first_yielder.restart_continuation.invoke(39, context, new_bm))
            self.assertEquals(second_yielder.result, "second")

            second_yielder.restart_continuation.invoke(3, context, returner)

        self.assertEquals(returner.result, 42)

    def test_repeated_restart_while_using_restart_values(self):
        context = RDHObject({})
        flow_manager = create_application_flow_manager()

        func = prepare(
            function_lit(
                no_value_type, build_break_types(any_type, yield_types={ "out": any_type, "in": int_type }),
                return_op(addition_op(yield_op(literal_op(30), int_type), yield_op(literal_op(10), int_type)))
            ),
            context, create_no_escape_flow_manager()
        )

        first_yielder = flow_manager.capture(
            "yield", { "out": AnyType(), "in": IntegerType() },
            lambda new_fm: func.invoke(NO_VALUE, context, new_fm)
        )
        second_yielder = flow_manager.capture(
            "yield", { "out": AnyType(), "in": IntegerType() },
            lambda new_fm: first_yielder.restart_continuation.invoke(first_yielder.result + 1, context, new_fm)
        )
        returner = flow_manager.capture(
            "return", { "out": AnyType() },
            lambda new_fm: second_yielder.restart_continuation.invoke(second_yielder.result + 1, context, new_fm)
        )

        self.assertEquals(returner.result, 42)

if __name__ == '__main__':
    main()
