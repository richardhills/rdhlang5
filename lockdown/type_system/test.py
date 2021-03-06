from unittest import main
from unittest.case import TestCase

from lockdown.type_system.composites import CompositeType, InferredType, \
    check_dangling_inferred_types, prepare_lhs_type
from lockdown.type_system.core_types import IntegerType, UnitType, StringType, \
    AnyType, Const, OneOfType, BooleanType, merge_types
from lockdown.type_system.default_composite_types import DEFAULT_OBJECT_TYPE, \
    rich_composite_type
from lockdown.type_system.dict_types import DictGetterType, \
    RDHDict
from lockdown.type_system.exceptions import CompositeTypeIncompatibleWithTarget, \
    CompositeTypeIsInconsistent, FatalError, DanglingInferredType
from lockdown.type_system.list_types import RDHListType, RDHList, SPARSE_ELEMENT, \
    ListGetterType, ListSetterType, ListInsertType, ListDeletterType
from lockdown.type_system.managers import get_manager, get_type_of_value
from lockdown.type_system.object_types import ObjectGetterType, ObjectSetterType, \
    ObjectDeletterType, RDHObjectType, PythonObjectType, RDHObject, \
    DefaultDictType, ObjectWildcardGetterType, ObjectWildcardSetterType
from lockdown.utils import set_debug


class TestObject(RDHObject):
    def __init__(self, initial_data, *args, **kwargs):
        for key, value in initial_data.items():
            self.__dict__[key] = value
        super(TestObject, self).__init__(*args, **kwargs)

class TestMicroOpMerging(TestCase):
    def test_merge_gets(self):
        first = ObjectGetterType("foo", IntegerType(), False, False)
        second = ObjectGetterType("foo", UnitType(5), False, False)

        combined = first.merge(second)
        self.assertTrue(isinstance(combined.value_type, UnitType))
        self.assertEqual(combined.value_type.value, 5)

    def test_merge_sets(self):
        first = ObjectSetterType("foo", IntegerType(), False, False)
        second = ObjectSetterType("foo", UnitType(5), False, False)

        combined = first.merge(second)
        self.assertTrue(isinstance(combined.value_type, IntegerType))


class TestBasicObject(TestCase):
    def test_add_micro_op_dictionary(self):
        obj = RDHDict({ "foo": "hello" })
        get_manager(obj).add_composite_type(CompositeType({
            ("get", "foo"): DictGetterType("foo", StringType(), False, False)
        }, name="test"))

    def test_add_micro_op_object(self):
        class Foo(TestObject):
            pass
        obj = Foo({ "foo": "hello" })
        get_manager(obj).add_composite_type(CompositeType({
            ("get", "foo"): ObjectGetterType("foo", StringType(), False, False)
        }, name="test"))

    def test_setup_read_write_property(self):
        obj = TestObject({ "foo": "hello" })
        get_manager(obj).add_composite_type(CompositeType({
            ("get", "foo"): ObjectGetterType("foo", StringType(), False, False),
            ("set", "foo"): ObjectSetterType("foo", StringType(), False, False)
        }, name="test"))

    def test_setup_broad_read_write_property(self):
        obj = TestObject({ "foo": "hello" })
        get_manager(obj).add_composite_type(CompositeType({
            ("get", "foo"): ObjectGetterType("foo", AnyType(), False, False),
            ("set", "foo"): ObjectSetterType("foo", AnyType(), False, False)
        }, name="test"))

    def test_setup_narrow_write_property(self):
        obj = TestObject({ "foo": "hello" })
        get_manager(obj).add_composite_type(CompositeType({
            ("get", "foo"): ObjectGetterType("foo", UnitType("hello"), False, False),
            ("set", "foo"): ObjectSetterType("foo", UnitType("hello"), False, False)
        }, name="test"))

    def test_setup_broad_reading_property(self):
        obj = TestObject({ "foo": "hello" })
        get_manager(obj).add_composite_type(CompositeType({
            ("get", "foo"): ObjectGetterType("foo", AnyType(), False, False),
            ("set", "foo"): ObjectSetterType("foo", StringType(), False, False)
        }, name="test"))

    def test_failed_setup_broad_writing_property(self):
        with self.assertRaises(CompositeTypeIsInconsistent):
            obj = TestObject({ "foo": "hello" })

            get_manager(obj).add_composite_type(CompositeType({
                ("get", "foo"): ObjectGetterType("foo", StringType(), False, False),
                ("set", "foo"): ObjectSetterType("foo", AnyType(), False, False)
            }, name="test"))

    def test_composite_object_dereference(self):
        obj = TestObject({ "foo": "hello" })

        get_manager(obj).add_composite_type(CompositeType({
            ("get", "foo"): ObjectGetterType("foo", StringType(), False, False),
            ("set", "foo"): ObjectSetterType("foo", StringType(), False, False)
        }, name="test"))

        self.assertEquals(obj.foo, "hello")

    def test_composite_object_broad_dereference(self):
        obj = TestObject({ "foo": "hello" })

        get_manager(obj).add_composite_type(CompositeType({
            ("get", "foo"): ObjectGetterType("foo", AnyType(), False, False),
            ("set", "foo"): ObjectSetterType("foo", AnyType(), False, False)
        }, name="test"))

        self.assertEquals(obj.foo, "hello")

    def test_composite_object_assignment(self):
        obj = TestObject({ "foo": "hello" })

        get_manager(obj).add_composite_type(CompositeType({
            ("get", "foo"): ObjectGetterType("foo", StringType(), False, False),
            ("set", "foo"): ObjectSetterType("foo", StringType(), False, False)
        }, name="test"))

        obj.foo = "what"

    def test_composite_object_invalid_assignment(self):
        obj = TestObject({ "foo": "hello" })

        get_manager(obj).add_composite_type(CompositeType({
            ("get", "foo"): ObjectGetterType("foo", StringType(), False, False),
            ("set", "foo"): ObjectSetterType("foo", StringType(), False, False)
        }, name="test"))

        with self.assertRaises(Exception):
            obj.foo = 5

    def test_python_like_object(self):
        obj = TestObject({ "foo": "hello" })

        get_manager(obj).add_composite_type(CompositeType({
            ("get", "foo"): ObjectGetterType("foo", AnyType(), False, False),
            ("set", "foo"): ObjectSetterType("foo", AnyType(), False, False)
        }, name="test"))

        self.assertEquals(obj.foo, "hello")
        obj.foo = "what"
        self.assertEquals(obj.foo, "what")

    def test_java_like_object(self):
        obj = TestObject({ "foo": "hello" })

        get_manager(obj).add_composite_type(CompositeType({
            ("get", "foo"): ObjectGetterType("foo", StringType(), False, False),
            ("set", "foo"): ObjectSetterType("foo", StringType(), False, False)
        }, name="test"))

        self.assertEquals(obj.foo, "hello")
        obj.foo = "what"
        self.assertEquals(obj.foo, "what")

        with self.assertRaises(Exception):
            obj.bar = "hello"

    def test_const_property(self):
        obj = TestObject({ "foo": "hello" })

        get_manager(obj).add_composite_type(CompositeType({
            ("get", "foo"): ObjectGetterType("foo", StringType(), False, False)
        }, name="test"))

        self.assertEquals(obj.foo, "hello")
        with self.assertRaises(Exception):
            obj.foo = "what"

    def test_invalid_initialization(self):
        obj = TestObject({})
        with self.assertRaises(Exception):
            get_manager(obj).add_micro_op_tag(None, ("get", "foo"), StringType(), False, False)

    def test_delete_property(self):
        obj = TestObject({ "foo": "hello" })

        get_manager(obj).add_composite_type(CompositeType({
            ("get", "foo"): ObjectGetterType("foo", StringType(), True, True),
            ("set", "foo"): ObjectSetterType("foo", StringType(), True, True),
            ("delete", "foo"): ObjectDeletterType("foo", True)
        }, name="test"))

        del obj.foo
        self.assertFalse(hasattr(obj, "foo"))


class TestRevConstType(TestCase):
    def test_rev_const_assigned_to_broad_type(self):
        rev_const_type = CompositeType({
            ("get", "foo"): ObjectGetterType("foo", StringType(), False, False),
            ("set", "foo"): ObjectSetterType("foo", AnyType(), False, False),
        }, name="test")

        normal_broad_type = CompositeType({
            ("get", "foo"): ObjectGetterType("foo", AnyType(), False, False),
            ("set", "foo"): ObjectSetterType("foo", AnyType(), False, False)
        }, name="test")

        self.assertTrue(normal_broad_type.is_copyable_from(rev_const_type))

    def test_rev_const_assigned_to_narrow_type(self):
        rev_const_type = CompositeType({
            ("get", "foo"): ObjectGetterType("foo", StringType(), False, False),
            ("set", "foo"): ObjectSetterType("foo", AnyType(), False, False)
        }, name="test")

        normal_broad_type = CompositeType({
            ("get", "foo"): ObjectGetterType("foo", StringType(), False, False),
            ("set", "foo"): ObjectSetterType("foo", StringType(), False, False)
        }, name="test")

        self.assertTrue(normal_broad_type.is_copyable_from(rev_const_type))

    def test_rev_const_can_not_be_added_to_object(self):
        rev_const_type = CompositeType({
            ("get", "foo"): ObjectGetterType("foo", StringType(), False, False),
            ("set", "foo"): ObjectSetterType("foo", AnyType(), False, False)
        }, name="test")

        obj = TestObject({ "foo": "hello" })
        with self.assertRaises(Exception):
            get_manager(obj).add_composite_type(rev_const_type)

    def test_rev_const_narrowing(self):
        rev_const_type = CompositeType({
            ("get", "foo"): ObjectGetterType("foo", StringType(), False, False),
            ("set", "foo"): ObjectSetterType("foo", AnyType(), False, False)
        }, name="test")

        normal_broad_type = CompositeType({
            ("get", "foo"): ObjectGetterType("foo", StringType(), False, False),
            ("set", "foo"): ObjectSetterType("foo", StringType(), False, False)
        }, name="test")

        rev_const_type = prepare_lhs_type(rev_const_type, None)

        self.assertTrue(isinstance(rev_const_type.micro_op_types[("set", "foo")].value_type, StringType))

        self.assertTrue(normal_broad_type.is_copyable_from(rev_const_type))

    def test_rev_const_wildcard(self):
        rev_const_type = CompositeType({
            ("get-wildcard", ): ObjectWildcardGetterType(StringType(), StringType(), False, False),
            ("set-wildcard", ): ObjectWildcardSetterType(StringType(), AnyType(), False, False)
        }, name="test")

        normal_broad_type = CompositeType({
            ("get", "foo"): ObjectWildcardGetterType(StringType(), StringType(), False, False),
            ("set", "foo"): ObjectWildcardSetterType(StringType(), StringType(), False, False)
        }, name="test")

        rev_const_type = prepare_lhs_type(rev_const_type, None)

        self.assertTrue(isinstance(rev_const_type.micro_op_types[("set-wildcard",)].value_type, StringType))

        self.assertTrue(normal_broad_type.is_copyable_from(rev_const_type))

    def test_rev_const_flatten_tuple(self):
        rev_const_type = CompositeType({
            ("get", 0): ListGetterType(0, StringType(), False, False),
            ("set", 0): ListSetterType(0, AnyType(), False, False)
        }, name="test")

        normal_broad_type = CompositeType({
            ("get", 0): ListGetterType(0, StringType(), False, False),
            ("set", 0): ListSetterType(0, StringType(), False, False)
        }, name="test")

        rev_const_type = prepare_lhs_type(rev_const_type, None)

        self.assertTrue(isinstance(rev_const_type.micro_op_types[("set", 0)].value_type, StringType))

        self.assertTrue(normal_broad_type.is_copyable_from(rev_const_type))

    def test_rev_const_flatten_list(self):
        rev_const_type = CompositeType({
            ("get", 0): ListGetterType(0, StringType(), False, False),
            ("set", 0): ListSetterType(0, AnyType(), False, False),
            ("insert", 0): ListInsertType(0, IntegerType(), False, False)
        }, name="test")

        normal_broad_type = CompositeType({
            ("get", 0): ListGetterType(0, OneOfType([ StringType(), IntegerType() ]), False, False),
            ("set", 0): ListSetterType(0, StringType(), False, False),
            ("insert", 0): ListInsertType(0, IntegerType(), False, False),
        }, name="test")

        rev_const_type = prepare_lhs_type(rev_const_type, None)

        self.assertTrue(rev_const_type.is_self_consistent())

        self.assertTrue(normal_broad_type.is_copyable_from(rev_const_type))

    def test_rev_const_merge_types_in_list(self):
        rev_const_type = CompositeType({
            ("get", 0): ListGetterType(0, StringType(), False, False),
            ("set", 0): ListSetterType(0, StringType(), False, False),
            ("get", 1): ListGetterType(1, IntegerType(), False, False),
            ("set", 1): ListSetterType(1, IntegerType(), False, False),
            ("get", 2): ListGetterType(2, AnyType(), False, False),
            ("set", 2): ListSetterType(2, AnyType(), False, False),
            ("insert", 0): ListInsertType(0, StringType(), False, False)
        }, name="test")

        normal_broad_type = CompositeType({
            ("get", 0): ListGetterType(0, StringType(), False, False),
            ("set", 0): ListSetterType(0, StringType(), False, False),
            ("get", 1): ListGetterType(1, OneOfType([ StringType(), IntegerType() ]), False, False),
            ("set", 1): ListSetterType(1, IntegerType(), False, False),
            ("get", 2): ListGetterType(2, AnyType(), False, False),
            ("set", 2): ListSetterType(2, AnyType(), False, False),
            ("insert", 0): ListInsertType(0, StringType(), False, False),
        }, name="test")

        rev_const_type = prepare_lhs_type(rev_const_type, None)

        self.assertTrue(rev_const_type.is_self_consistent())

        self.assertTrue(normal_broad_type.is_copyable_from(rev_const_type))

    def test_rev_const_merge_types_with_delete(self):
        rev_const_type = CompositeType({
            ("get", 0): ListGetterType(0, AnyType(), False, False),
            ("set", 0): ListSetterType(0, AnyType(), False, False),
            ("get", 1): ListGetterType(1, IntegerType(), False, False),
            ("set", 1): ListSetterType(1, IntegerType(), False, False),
            ("get", 2): ListGetterType(2, StringType(), False, False),
            ("set", 2): ListSetterType(2, StringType(), False, False),
            ("delete", 0): ListDeletterType(0, False)
        }, name="test")

        normal_broad_type = CompositeType({
            ("get", 0): ListGetterType(0, AnyType(), True, False),
            ("set", 0): ListSetterType(0, AnyType(), True, False),
            ("get", 1): ListGetterType(1, OneOfType([ StringType(), IntegerType() ]), True, False),
            ("set", 1): ListSetterType(1, IntegerType(), True, False),
            ("get", 2): ListGetterType(2, StringType(), True, False),
            ("set", 2): ListSetterType(2, StringType(), True, False),
            ("delete", 0): ListDeletterType(0, False),
        }, name="test")

        rev_const_type = prepare_lhs_type(rev_const_type, None)

        self.assertTrue(rev_const_type.is_self_consistent())

        self.assertTrue(normal_broad_type.is_copyable_from(rev_const_type))

class TestRDHObjectType(TestCase):
    def test_basic_class(self):
        T = RDHObjectType({
            "foo": IntegerType()
        })

        S = RDHObjectType({
            "foo": IntegerType(),
            "bar": StringType()
        })

        self.assertTrue(T.is_copyable_from(S))
        self.assertFalse(S.is_copyable_from(T))

    def test_const_allows_broader_types(self):
        T = RDHObjectType({
            "foo": Const(AnyType())
        })

        S = RDHObjectType({
            "foo": IntegerType()
        })

        self.assertTrue(T.is_copyable_from(S))
        self.assertFalse(S.is_copyable_from(T))

    def test_broad_type_assignments_blocked(self):
        T = RDHObjectType({
            "foo": AnyType()
        })

        S = RDHObjectType({
            "foo": IntegerType()
        })

        self.assertFalse(T.is_copyable_from(S))
        self.assertFalse(S.is_copyable_from(T))

    def test_simple_fields_are_required(self):
        T = RDHObjectType({
        })

        S = RDHObjectType({
            "foo": IntegerType()
        })

        self.assertTrue(T.is_copyable_from(S))
        self.assertFalse(S.is_copyable_from(T))

    def test_many_fields_are_required(self):
        T = RDHObjectType({
            "foo": IntegerType(),
            "bar": IntegerType(),
        })

        S = RDHObjectType({
            "foo": IntegerType(),
            "bar": IntegerType(),
            "baz": IntegerType()
        })

        self.assertTrue(T.is_copyable_from(S))
        self.assertFalse(S.is_copyable_from(T))

    def test_can_fail_micro_ops_are_enforced(self):
        foo = TestObject({
            "foo": 5,
            "bar": "hello"
        })

        get_manager(foo).add_composite_type(
            RDHObjectType({ "foo": Const(IntegerType()) })
        )

        with self.assertRaises(Exception):
            foo.foo = "hello"

    def test_const_is_enforced(self):
        return  # test doesn't work because the assignment uses the set-wildcard
        foo = {
            "foo": 5,
            "bar": "hello"
        }

        get_manager(foo).add_composite_type(
            RDHObjectType({ "foo": Const(IntegerType()) })
        )

        with self.assertRaises(Exception):
            foo.foo = 42

    def test_types_on_object_merged(self):
        foo = TestObject({
            "foo": 5,
            "bar": "hello"
        })
        get_manager(foo).add_composite_type(
            RDHObjectType({ "foo": IntegerType() })
        )
        get_manager(foo).add_composite_type(
            RDHObjectType({ "bar": StringType() })
        )

        object_type = get_manager(foo).get_effective_composite_type()

        RDHObjectType({
            "foo": IntegerType(),
            "bar": StringType()
        }).is_copyable_from(object_type)


class TestUnitTypes(TestCase):
    def test_basics(self):
        foo = TestObject({
            "bar": 42
        })
        get_manager(foo).add_composite_type(RDHObjectType({
            "bar": UnitType(42)
        }))
        self.assertEquals(foo.bar, 42)

    def test_broadening_blocked(self):
        foo = TestObject({
            "bar": 42
        })
        get_manager(foo).add_composite_type(RDHObjectType({
            "bar": UnitType(42)
        }))

        with self.assertRaises(Exception):
            get_manager(foo).add_composite_type(RDHObjectType({
                "bar": IntegerType()
            }))

    def test_narrowing_blocked(self):
        foo = TestObject({
            "bar": 42
        })
        get_manager(foo).add_composite_type(RDHObjectType({
            "bar": IntegerType()
        }))
        with self.assertRaises(Exception):
            get_manager(foo).add_composite_type(RDHObjectType({
                "bar": UnitType(42)
            }))

    def test_broadening_with_const_is_ok(self):
        foo = TestObject({
            "bar": 42
        })
        get_manager(foo).add_composite_type(RDHObjectType({
            "bar": UnitType(42)
        }))

        get_manager(foo).add_composite_type(RDHObjectType({
            "bar": Const(IntegerType())
        }))


class TestNestedRDHObjectTypes(TestCase):
    def test_basic_assignment(self):
        Bar = RDHObjectType({
            "baz": IntegerType()
        })
        foo = TestObject({
            "bar": TestObject({
                "baz": 42
            })
        })

        get_manager(foo).add_composite_type(
            RDHObjectType({
                "bar": Bar
            })
        )

        foo.bar = TestObject({ "baz": 42 }, bind=Bar)

        self.assertEquals(foo.bar.baz, 42)

    def test_blocked_basic_assignment(self):
        foo = TestObject({
            "bar": TestObject({
                "baz": 42
            })
        })

        get_manager(foo).add_composite_type(
            RDHObjectType({
                "bar": RDHObjectType({
                    "baz": IntegerType()
                })
            })
        )

        with self.assertRaises(Exception):
            foo.bar = TestObject({ "baz": "hello" })

    def test_deletion_blocked(self):
        foo = TestObject({
            "bar": TestObject({
                "baz": 42
            })
        })

        get_manager(foo).add_composite_type(
            RDHObjectType({
                "bar": RDHObjectType({
                    "baz": IntegerType()
                })
            })
        )

        with self.assertRaises(Exception):
            del foo.bar

    def test_broad_assignment(self):
        foo = TestObject({
            "bar": TestObject({
                "baz": 42
            })
        })

        Bar = RDHObjectType({
            "baz": AnyType()
        })

        get_manager(foo).add_composite_type(
            RDHObjectType({
                "bar": Bar
            })
        )

        foo.bar = TestObject({ "baz": "hello" }, bind=Bar)

        self.assertEquals(foo.bar.baz, "hello")

    def test_double_deep_assignment(self):
        foo = TestObject({
            "bar": TestObject({
                "baz": TestObject({
                    "bam": 10
                })
            })
        })

        Baz = RDHObjectType({
            "bam": IntegerType()
        })

        Bar = RDHObjectType({
            "baz": Baz
        })

        get_manager(foo).add_composite_type(
            RDHObjectType({
                "bar": Bar
            })
        )

        self.assertEquals(foo.bar.baz.bam, 10)

        foo.bar = TestObject({ "baz": TestObject({ "bam": 42 }) }, bind=Bar)

        self.assertEquals(foo.bar.baz.bam, 42)

    def test_conflicting_types(self):
        foo = TestObject({
            "bar": TestObject({
                "baz": 42
            })
        })

        get_manager(foo).add_composite_type(
            RDHObjectType({
                "bar": RDHObjectType({
                    "baz": IntegerType()
                })
            })
        )

        with self.assertRaises(Exception):
            get_manager(foo).add_composite_type(
                RDHObjectType({
                    "bar": RDHObjectType({
                        "baz": AnyType()
                    })
                })
            )

    def test_changes_blocked_without_micro_ops(self):
        foo = TestObject({
            "bar": TestObject({
                "baz": 42
            })
        })

        get_manager(foo)

        with self.assertRaises(Exception):
            foo.bar = "hello"

    def test_very_broad_assignment(self):
        foo = TestObject({
            "bar": TestObject({
                "baz": 42
            })
        })

        get_manager(foo).add_composite_type(
            RDHObjectType({ "bar": AnyType() })
        )

        foo.bar = "hello"
        self.assertEquals(foo.bar, "hello")


class TestNestedPythonTypes(TestCase):
    def test_python_like_type(self):
        foo = TestObject({
            "bar": TestObject({
                "baz": 42
            })
        })

        get_manager(foo).add_composite_type(PythonObjectType(name="test"))

        foo.bar.baz = 22

        foo.bar = "hello"
        self.assertEquals(foo.bar, "hello")

    def test_python_object_with_reference_can_be_modified(self):
        bar = TestObject({
            "baz": 42
        })
        foo = TestObject({
            "bar": bar
        })

        get_manager(bar).add_composite_type(RDHObjectType({ "baz": IntegerType() }))
        get_manager(foo).add_composite_type(PythonObjectType(name="test"))

        self.assertEqual(foo.bar.baz, 42)
        foo.bar.baz = 5
        self.assertEqual(foo.bar.baz, 5)

    def test_python_object_with_reference_types_are_enforced(self):
        bar = TestObject({
            "baz": 42
        })
        foo = TestObject({
            "bar": bar
        })

        get_manager(bar).add_composite_type(RDHObjectType({ "baz": IntegerType() }))
        get_manager(foo).add_composite_type(PythonObjectType(name="test"))

        with self.assertRaises(Exception):
            foo.bar.baz = "hello"

    def test_python_object_with_reference_can_be_replaced(self):
        bar = TestObject({
            "baz": 42
        })
        foo = TestObject({
            "bar": bar
        })

        get_manager(bar).add_composite_type(RDHObjectType({ "baz": IntegerType() }))
        get_manager(foo).add_composite_type(PythonObjectType(name="test"))

        foo.bar = TestObject({
            "baz": 123
        })

        self.assertEqual(foo.bar.baz, 123)
        foo.bar.baz = "what"
        self.assertEqual(foo.bar.baz, "what")

    def test_that_python_constraints_dont_spread_to_constrained_children(self):
        bar = TestObject({
            "baz": 42
        })
        foo = TestObject({
            "bar": bar
        })

        # The first, stronger, type prevents the PythonObjectType spreading from foo to bar
        get_manager(bar).add_composite_type(RDHObjectType({ "baz": IntegerType() }))
        get_manager(foo).add_composite_type(PythonObjectType(name="test"))

        self.assertIs(foo.bar, bar)

        self.assertEquals(len(get_manager(foo).attached_types), 1)
        self.assertEquals(len(get_manager(foo.bar).attached_types), 1)

        # ... but when bar is replaced with a new object without constraints, the PythonObjectType
        # spreads to the new object
        foo.bar = TestObject({
            "baz": 123
        })

        self.assertIsNot(foo.bar, bar)

        self.assertEquals(len(get_manager(foo.bar).attached_types), 1)

        # Now that the new object has the PythonObjectType constraint, we can't bind a stronger
        # constraint
        with self.assertRaises(CompositeTypeIncompatibleWithTarget):
            get_manager(foo.bar).add_composite_type(RDHObjectType({ "baz": IntegerType() }))

    def test_python_delete_works(self):
        foo = TestObject({
            "bar": TestObject({
                "baz": 42
            })
        })

        get_manager(foo).add_composite_type(PythonObjectType(name="test"))

        del foo.bar
        self.assertFalse(hasattr(foo, "bar"))

    def test_python_replacing_object_works(self):
        foo = TestObject({
            "bar": TestObject({
                "baz": 42
            })
        })

        get_manager(foo).add_composite_type(PythonObjectType(name="test"))

        foo.bar = TestObject({ "baz": 123 })

        self.assertEquals(foo.bar.baz, 123)

    def test_python_random_read_fails_nicely(self):
        foo = TestObject({
            "bar": TestObject({
                "baz": 42
            })
        })

        get_manager(foo).add_composite_type(PythonObjectType(name="test"))

        with self.assertRaises(AttributeError):
            foo.bop


class TestDefaultDict(TestCase):
    def test_default_dict_is_consistent_type(self):
        type = DefaultDictType(StringType(), name="test")
        self.assertTrue(type.is_self_consistent())

    def test_default_dict(self):
        def default_factory(target, key):
            return "{}-123".format(key)

        foo = RDHObject({
            "bar": "forty-two"
        }, default_factory=default_factory)

        get_manager(foo).add_composite_type(DefaultDictType(StringType(), name="test"))

        self.assertEquals(foo.bar, "forty-two")
        self.assertEquals(foo.bam, "bam-123")

class TestListObjects(TestCase):
    def test_basic_list_of_ints(self):
        foo = RDHList([ 1, 2, 3 ])

        get_manager(foo).add_composite_type(RDHListType([], IntegerType()))

        foo[0] = 42
        self.assertEqual(foo[0], 42)

    def test_basic_tuple_of_ints(self):
        foo = RDHList([ 1, 2, 3 ])

        get_manager(foo).add_composite_type(RDHListType([ IntegerType(), IntegerType(), IntegerType() ], None))

        foo[0] = 42
        self.assertEqual(foo[0], 42)

    def test_bounds_enforced(self):
        foo = RDHList([ 1, 2 ])

        with self.assertRaises(Exception):
            get_manager(foo).add_composite_type(RDHListType([ IntegerType(), IntegerType(), IntegerType() ], None))


class TestTypeSystemMisc(TestCase):
    # Tests for random things that were broken
    def test_misc1(self):
        # Came up testing lockdown local variable binding
        RDHObject({
            "local": RDHList([ 39, 3 ]),
            "types": RDHObject()
        }, bind=RDHObjectType({
            "local": RDHListType([ IntegerType(), IntegerType() ], None),
            "types": DEFAULT_OBJECT_TYPE
        }, wildcard_value_type=rich_composite_type))

    def test_misc2(self):
        # Came up writing test_misc1
        RDHObject({
            "local": RDHList([ 39, 3 ])
        }, bind=RDHObjectType({
            "local": RDHListType([ IntegerType(), IntegerType() ], None)
        }, wildcard_value_type=rich_composite_type))


class TestRDHListType(TestCase):
    def test_simple_list_assignment(self):
        foo = RDHListType([], IntegerType())
        bar = RDHListType([], IntegerType())

        self.assertTrue(foo.is_copyable_from(bar))

    def test_simple_tuple_assignment(self):
        foo = RDHListType([ IntegerType(), IntegerType() ], None)
        bar = RDHListType([ IntegerType(), IntegerType() ], None)

        self.assertTrue(foo.is_copyable_from(bar))

    def test_broadening_tuple_assignment_blocked(self):
        foo = RDHListType([ AnyType(), AnyType() ], None)
        bar = RDHListType([ IntegerType(), IntegerType() ], None)

        self.assertFalse(foo.is_copyable_from(bar))

    def test_narrowing_tuple_assignment_blocked(self):
        foo = RDHListType([ IntegerType(), IntegerType() ], None)
        bar = RDHListType([ AnyType(), AnyType() ], None)

        self.assertFalse(foo.is_copyable_from(bar))

    def test_broadening_tuple_assignment_allowed_with_const(self):
        foo = RDHListType([ Const(AnyType()), Const(AnyType()) ], None)
        bar = RDHListType([ IntegerType(), IntegerType() ], None)

        self.assertTrue(foo.is_copyable_from(bar))

    def test_truncated_tuple_slice_assignment(self):
        foo = RDHListType([ IntegerType() ], None)
        bar = RDHListType([ IntegerType(), IntegerType() ], None)

        self.assertTrue(foo.is_copyable_from(bar))

    def test_expanded_tuple_slice_assignment_blocked(self):
        foo = RDHListType([ IntegerType(), IntegerType() ], None)
        bar = RDHListType([ IntegerType() ], None)

        self.assertFalse(foo.is_copyable_from(bar))
  
# This is blocked - you can't have wildcard access to a list derived from a tuple without it
# A strongly opcode to link the two would be an iterator, which both could support
#     def test_convert_tuple_to_list(self):
#         foo = RDHListType([ ], IntegerType(), allow_delete=False, allow_wildcard_insert=False, allow_push=False)
#         bar = RDHListType([ IntegerType(), IntegerType() ], None)
# 
#         self.assertTrue(foo.is_copyable_from(bar))

    def test_const_covariant_array_assignment_allowed(self):
        foo = RDHListType([ ], Const(AnyType()), allow_push=False, allow_wildcard_insert=False)
        bar = RDHListType([ ], IntegerType())

        self.assertTrue(foo.is_copyable_from(bar))

    def test_convert_tuple_to_list_with_deletes_blocked(self):
        foo = RDHListType([ ], IntegerType())
        bar = RDHListType([ IntegerType(), IntegerType() ], None)

        self.assertFalse(foo.is_copyable_from(bar))

#     def test_pushing_into_short_tuple(self):
#         foo = RDHListType([ IntegerType() ], IntegerType(), allow_delete=False)
#         bar = RDHListType([ IntegerType() ], IntegerType(), allow_delete=False, allow_wildcard_insert=False)
# 
#         self.assertTrue(foo.is_copyable_from(bar))

# I'm not sure why I thought this was ok. You can't "invent" a new operation, wildcard insert
# on an object that doesn't support it already, just because it doesn't conflict with
# other operations that you happen to know about.
#     def test_pushing_into_long_tuple(self):
#         foo = RDHListType([ IntegerType(), IntegerType() ], IntegerType(), allow_delete=False)
#         bar = RDHListType([ IntegerType(), IntegerType() ], IntegerType(), allow_delete=False, allow_wildcard_insert=False)
# 
#         self.assertTrue(foo.is_copyable_from(bar))

    def test_same_type_array_assignment(self):
        foo = RDHListType([ ], IntegerType())
        bar = RDHListType([ ], IntegerType())

        self.assertTrue(foo.is_copyable_from(bar))

    def test_covariant_array_assignment_blocked(self):
        foo = RDHListType([ ], AnyType())
        bar = RDHListType([ ], IntegerType())

        self.assertFalse(foo.is_copyable_from(bar))

    def test_narrowing_assignment_blocked(self):
        foo = RDHListType([], IntegerType(), allow_push=False, allow_wildcard_insert=False, allow_delete=False, is_sparse=True)
        bar = RDHListType([], Const(rich_composite_type), allow_push=False, allow_wildcard_insert=False, allow_delete=False, is_sparse=True)

        self.assertTrue(bar.is_copyable_from(foo))
        self.assertFalse(foo.is_copyable_from(bar))

    def test_extreme_type1_contains_conflicts(self):
        foo = RDHListType([ IntegerType() ], StringType())
        self.assertFalse(foo.is_self_consistent())

    def test_reified_extreme_type_contains_no_conflicts(self):
        foo = prepare_lhs_type(RDHListType([ IntegerType() ], IntegerType()), None)
        self.assertTrue(foo.is_self_consistent())

    def test_simple_type1_has_no_conflicts(self):
        foo = RDHListType([], IntegerType())
        self.assertTrue(foo.is_self_consistent())

    def test_simple_type2_has_no_conflicts(self):
        foo = RDHListType([ IntegerType() ], None)
        self.assertTrue(foo.is_self_consistent())

    def test_extreme_type_tamed1_has_no_conflicts(self):
        foo = RDHListType([ IntegerType() ], IntegerType())
        self.assertTrue(foo.is_self_consistent())

    def test_extreme_type_tamed2_contains_conflicts(self):
        foo = RDHListType([ IntegerType() ], AnyType(), allow_push=False, allow_wildcard_insert=False, allow_delete=False)
        self.assertTrue(foo.is_self_consistent())

class TestList(TestCase):
    def test_simple_list_assignment(self):
        foo = RDHList([ 4, 6, 8 ])
        get_manager(foo).add_composite_type(RDHListType([], IntegerType()))

    def test_list_modification_wrong_type_blocked(self):
        foo = RDHList([ 4, 6, 8 ])
        get_manager(foo).add_composite_type(RDHListType([], IntegerType()))

        with self.assertRaises(TypeError):
            foo.append("hello")

    def test_list_modification_right_type_ok(self):
        foo = RDHList([ 4, 6, 8 ])
        get_manager(foo).add_composite_type(RDHListType([], IntegerType()))

        foo.append(10)

    def test_list_appending_blocked(self):
        foo = RDHList([ 4, 6, 8 ])
        get_manager(foo).add_composite_type(RDHListType([], None))

        with self.assertRaises(IndexError):
            foo.append(10)

    def test_mixed_type_tuple(self):
        foo = RDHList([ 4, 6, 8 ])
        get_manager(foo).add_composite_type(RDHListType([ IntegerType(), AnyType() ], None))

        with self.assertRaises(TypeError):
            foo[0] = "hello"

        self.assertEqual(foo[0], 4)

        foo[1] = "what"
        self.assertEqual(foo[1], "what")

    def test_outside_tuple_access_blocked(self):
        foo = RDHList([ 4, 6, 8 ])
        get_manager(foo).add_composite_type(RDHListType([ IntegerType(), AnyType() ], None))

        with self.assertRaises(IndexError):
            foo[2]
        with self.assertRaises(IndexError):
            foo[2] = "hello"

    def test_outside_tuple_access_allowed(self):
        foo = RDHList([ 4, 6, 8 ])
        get_manager(foo).add_composite_type(RDHListType([ ], AnyType(), allow_push=False, allow_delete=False, allow_wildcard_insert=False))

        self.assertEqual(foo[2], 8)
        foo[2] = "hello"
        self.assertEqual(foo[2], "hello")

    def test_combined_const_list_and_tuple(self):
        foo = RDHList([ 4, 6, 8 ])
        get_manager(foo).add_composite_type(RDHListType([ IntegerType(), AnyType() ], Const(AnyType()), allow_push=False, allow_delete=False, allow_wildcard_insert=False))

        self.assertEqual(foo[2], 8)

    def test_insert_at_start(self):
        foo = RDHList([ 4, 6, 8 ])
        get_manager(foo).add_composite_type(RDHListType([ ], IntegerType()))

        foo.insert(0, 2)
        self.assertEqual(list(foo), [ 2, 4, 6, 8 ])

    def test_insert_with_wrong_type_blocked(self):
        foo = RDHList([ 4, 6, 8 ])
        get_manager(foo).add_composite_type(RDHListType([ ], IntegerType()))

        with self.assertRaises(Exception):
            foo.insert(0, "hello")

    def test_list_type_is_consistent(self):
        type = RDHListType(
            [ IntegerType(), IntegerType() ],
            IntegerType(),
            allow_push=True,
            allow_delete=False,
            allow_wildcard_insert=False
        )
        self.assertTrue(type.is_self_consistent())

    def test_insert_on_short_tuple(self):
        foo = RDHList([ 4, 6, 8 ])
        get_manager(foo).add_composite_type(RDHListType([ IntegerType() ], IntegerType(), allow_push=True, allow_delete=False, allow_wildcard_insert=False))

        foo.insert(0, 2)
        self.assertEqual(list(foo), [ 2, 4, 6, 8 ])

    def test_insert_on_long_tuple(self):
        foo = RDHList([ 4, 6, 8 ])
        get_manager(foo).add_composite_type(
            RDHListType(
                [ IntegerType(), IntegerType() ],
                IntegerType(),
                allow_push=True,
                allow_delete=False,
                allow_wildcard_insert=False
            )
        )

        foo.insert(0, 2)
        self.assertEqual(list(foo), [ 2, 4, 6, 8 ])

    def test_insert_on_very_long_tuple(self):
        foo = RDHList([ 4, 6, 8, 10, 12, 14 ])
        get_manager(foo).add_composite_type(RDHListType([ IntegerType(), IntegerType(), IntegerType(), IntegerType(), IntegerType(), IntegerType() ], IntegerType(), allow_push=True, allow_delete=False, allow_wildcard_insert=False))

        foo.insert(0, 2)
        self.assertEqual(list(foo), [ 2, 4, 6, 8, 10, 12, 14 ])

    def test_sparse_list_setting(self):
        foo = RDHList([ 4, 6, 8 ], is_sparse=True)
        get_manager(foo).add_composite_type(RDHListType([ ], IntegerType(), is_sparse=True))

        foo[4] = 12
        self.assertEqual(list(foo), [ 4, 6, 8, SPARSE_ELEMENT, 12 ])

    def test_sparse_list_inserting(self):
        foo = RDHList([ 4, 6, 8 ], is_sparse=True)
        get_manager(foo).add_composite_type(RDHListType([ ], IntegerType(), is_sparse=True))

        foo.insert(4, 12)
        self.assertEqual(list(foo), [ 4, 6, 8, SPARSE_ELEMENT, 12 ])

    def test_set_on_non_sparse_blocked(self):
        foo = RDHList([ 4, 6, 8 ])
        get_manager(foo).add_composite_type(RDHListType([ ], IntegerType(), is_sparse=False))

        with self.assertRaises(IndexError):
            foo[4] = 12

    def test_incorrect_type_blocked(self):
        foo = RDHList([ 4, 6, 8 ])

        with self.assertRaises(Exception):
            get_manager(foo).add_composite_type(RDHListType([ ], StringType()))


class TestInferredTypes(TestCase):
    def test_basic(self):
        foo = InferredType()
        foo = prepare_lhs_type(foo, IntegerType())
        self.assertIsInstance(foo, IntegerType)

    def test_basic_object(self):
        foo = RDHObjectType({
            "bar": InferredType()
        })
        foo = prepare_lhs_type(foo, RDHObjectType({
            "bar": IntegerType()
        }))
        self.assertIsInstance(foo.micro_op_types[("get", "bar")].value_type, IntegerType)

    def test_basic_ignored(self):
        foo = RDHObjectType({
            "bar": StringType()
        })
        foo = prepare_lhs_type(foo, RDHObjectType({
            "bar": IntegerType()
        }))
        self.assertIsInstance(foo.micro_op_types[("get", "bar")].value_type, StringType)

    def test_basic_ignored2(self):
        foo = RDHObjectType({
            "bar": InferredType()
        })
        foo = prepare_lhs_type(foo, RDHObjectType({
            "bar": IntegerType(),
            "bam": StringType()
        }))
        self.assertIsInstance(foo.micro_op_types[("get", "bar")].value_type, IntegerType)

    def test_dangling_error(self):
        foo = RDHObjectType({
            "bar": InferredType()
        })
        with self.assertRaises(DanglingInferredType):
            foo = prepare_lhs_type(foo, RDHObjectType({
                "bam": StringType()
            }))
        check_dangling_inferred_types(foo)

    def test_double_nested(self):
        foo = RDHObjectType({
            "bar": RDHObjectType({
                "bam": InferredType()
            })
        })
        foo = prepare_lhs_type(foo, RDHObjectType({
            "bar": RDHObjectType({
                "bam": IntegerType()
            })
        }))
        self.assertIsInstance(foo.micro_op_types[("get", "bar")].value_type.micro_op_types[("get", "bam")].value_type, IntegerType)

    def test_composite_types_inferred(self):
        foo = RDHObjectType({
            "bar": InferredType()
        })
        foo = prepare_lhs_type(foo, RDHObjectType({
            "bar": RDHObjectType({
                "bam": IntegerType()
            })
        }))
        self.assertIsInstance(foo.micro_op_types[("get", "bar")].value_type.micro_op_types[("get", "bam")].value_type, IntegerType)


class TestOneOfTypes(TestCase):
    def test_basic(self):
        self.assertTrue(OneOfType([IntegerType(), StringType()]).is_copyable_from(IntegerType()))
        self.assertTrue(OneOfType([IntegerType(), StringType()]).is_copyable_from(StringType()))
        self.assertFalse(StringType().is_copyable_from(OneOfType([IntegerType(), StringType()])))

    def test_nested(self):
        self.assertTrue(
            RDHObjectType({
                "foo": OneOfType([ IntegerType(), StringType() ])
            }).is_copyable_from(RDHObjectType({
                "foo": OneOfType([ IntegerType(), StringType() ])
            }))
        )

        # Blocked because the receiver could set obj.foo = "hello", breaking the sender
        self.assertFalse(
            RDHObjectType({
                "foo": OneOfType([ IntegerType(), StringType() ])
            }).is_copyable_from(RDHObjectType({
                "foo": IntegerType()
            }))
        )

        self.assertTrue(
            RDHObjectType({
                "foo": Const(OneOfType([ IntegerType(), StringType() ]))
            }).is_copyable_from(RDHObjectType({
                "foo": IntegerType()
            }))
        )

    def test_runtime(self):
        obj = RDHObject({
            "foo": 5
        })
        get_manager(obj).add_composite_type(
            RDHObjectType({
                "foo": OneOfType([ IntegerType(), StringType() ])
            })
        )

class TestRuntime(TestCase):
    def test_adding_and_removing(self):
        A = RDHObject({
            "foo": 5
        })
        B = RDHObject({
            "bar": A
        })

        At = RDHObjectType({
            "foo": IntegerType()
        })

        Bt = RDHObjectType({
            "bar": At
        })

        get_manager(A).add_composite_type(At)
        self.assertEquals(len(get_manager(A).attached_types), 1)
        self.assertEquals(get_manager(A).attached_type_counts[id(At)], 1)
        get_manager(B).add_composite_type(Bt)
        self.assertEquals(len(get_manager(A).attached_types), 1)
        self.assertEquals(get_manager(A).attached_type_counts[id(At)], 2)
        get_manager(B).remove_composite_type(Bt)
        self.assertEquals(len(get_manager(A).attached_types), 1)
        self.assertEquals(get_manager(A).attached_type_counts[id(At)], 1)


    def test_modifying(self):
        At = RDHObjectType({
            "foo": IntegerType()
        })

        Bt = RDHObjectType({
            "bar": At
        })

        A = RDHObject({
            "foo": 5
        })
        B = RDHObject({
            "bar": A
        }, bind=Bt)

        self.assertEquals(len(get_manager(A).attached_types), 1)
        self.assertEquals(get_manager(A).attached_type_counts[id(At)], 1)

        B.bar = RDHObject({
            "foo": 42
        }, bind=At)
        
        self.assertEquals(len(get_manager(A).attached_types), 0)
        self.assertEquals(get_manager(A).attached_type_counts[id(At)], 0)

class TestRDHInstances(TestCase):
    def test_object_set_and_get(self):
        foo = RDHObject({})
        foo._set("foo", 42)

        self.assertEqual(foo._get("foo"), 42)

    def test_list_set_and_get(self):
        foo = RDHList([ 123 ])
        foo._set(0, 42)

        self.assertEqual(foo._get(0), 42)

    def test_list_insert(self):
        foo = RDHList([ 123 ])
        foo._insert(0, 42)

        self.assertEqual(foo._to_list(), [ 42, 123 ])
        

class TestCoreTypes(TestCase):
    def test_ints_and_bools(self):
        self.assertTrue(IntegerType().is_copyable_from(IntegerType()))
        self.assertTrue(BooleanType().is_copyable_from(BooleanType()))
        self.assertFalse(BooleanType().is_copyable_from(IntegerType()))
        self.assertFalse(IntegerType().is_copyable_from(BooleanType()))
        self.assertTrue(BooleanType().is_copyable_from(UnitType(True)))
        self.assertTrue(IntegerType().is_copyable_from(UnitType(5)))
        self.assertFalse(BooleanType().is_copyable_from(UnitType(5)))
        self.assertFalse(IntegerType().is_copyable_from(UnitType(True)))

    def test_merge_singleton_basic_types(self):
        self.assertTrue(isinstance(merge_types([ IntegerType() ], "super"), IntegerType))
        self.assertTrue(isinstance(merge_types([ IntegerType() ], "sub"), IntegerType))
        self.assertTrue(isinstance(merge_types([ IntegerType() ], "exact"), IntegerType))

    def test_merge_pairwise_parent_and_child_types(self):
        self.assertTrue(isinstance(merge_types([ AnyType(), IntegerType() ], "super"), AnyType))
        self.assertTrue(isinstance(merge_types([ AnyType(), IntegerType() ], "sub"), IntegerType))
        self.assertTrue(isinstance(merge_types([ AnyType(), IntegerType() ], "exact"), OneOfType))
        self.assertTrue(len(merge_types([ AnyType(), IntegerType() ], "exact").types) == 2)

    def test_merge_pairwise_unrelated_types(self):
        self.assertTrue(isinstance(merge_types([ StringType(), IntegerType() ], "super"), OneOfType))
        self.assertTrue(len(merge_types([ StringType(), IntegerType() ], "super").types) == 2)
        self.assertTrue(isinstance(merge_types([ StringType(), IntegerType() ], "sub"), OneOfType))
        self.assertTrue(len(merge_types([ StringType(), IntegerType() ], "sub").types) == 2)
        self.assertTrue(isinstance(merge_types([ StringType(), IntegerType() ], "exact"), OneOfType))
        self.assertTrue(len(merge_types([ StringType(), IntegerType() ], "exact").types) == 2)

    def test_merge_irrelevant_types(self):
        self.assertTrue(isinstance(merge_types([ StringType(), StringType(), IntegerType() ], "super"), OneOfType))
        self.assertTrue(len(merge_types([ StringType(), StringType(), IntegerType() ], "super").types) == 2)
        self.assertTrue(isinstance(merge_types([ StringType(), StringType(), IntegerType() ], "sub"), OneOfType))
        self.assertTrue(len(merge_types([ StringType(), StringType(), IntegerType() ], "sub").types) == 2)
        self.assertTrue(isinstance(merge_types([ StringType(), StringType(), IntegerType() ], "exact"), OneOfType))
        self.assertTrue(len(merge_types([ StringType(), IntegerType() ], "exact").types) == 2)
