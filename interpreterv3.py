from intbase import InterpreterBase, ErrorType
from brewparse import parse_program
from env_v3 import EnvironmentManager
from type_valuev3 import Type, Value, create_value, get_printable


class Interpreter(InterpreterBase):
    binary_operators = {
        "+",
        "-",
        "*",
        "/",
        "==",
        "<",
        "<=",
        ">",
        ">=",
        "!=",
        "&&",
        "||",
    }
    default_types = {"bool": False, "int": 0, "string": "", "void": None}

    def __init__(self, console_output=True, inp=None, trace_output=False):
        # call InterpreterBase's constructor
        super().__init__(console_output, inp)
        self.functions = []
        self.structs = {}

    def run(self, program):
        ast = parse_program(program)
        self.variables = EnvironmentManager()

        for struct in ast.dict["structs"]:
            self.structs[struct.dict["name"]] = struct

        main_func_node = None
        for function in ast.dict["functions"]:
            name = function.dict["name"]
            # check invalid args
            for arg in function.dict["args"]:
                if (
                    arg.dict["var_type"] not in Interpreter.default_types
                    and arg.dict["var_type"] not in self.structs
                ):
                    super().error(
                        ErrorType.TYPE_ERROR,
                        f"Invalid argument type for {name}",
                    )
            # check invalid returns
            if (
                function.dict["return_type"] not in Interpreter.default_types
                and function.dict["return_type"] not in self.structs
            ):
                super().error(
                    ErrorType.TYPE_ERROR,
                    f"Invalid return type for {name}",
                )
            if name == "main":
                main_func_node = function
            else:
                self.functions.append(function)

        if not main_func_node:
            super().error(
                ErrorType.NAME_ERROR,
                "No main() function was found",
            )
        self.run_function(main_func_node)

    def run_function(self, func_node, args=None):
        self.variables.push_scope("function")
        # temp_args is the args within the function
        # args is the information that's being passed into the function
        temp_args = func_node.dict["args"]
        return_type = func_node.dict["return_type"]

        # instantiate args with the right values
        for i in range(len(temp_args)):
            name = temp_args[i].dict["name"]
            type = temp_args[i].dict["var_type"]

            # assigning an int to a bool
            if type == Type.BOOL and args[i].type() == Type.INT:
                args[i] = self.check_bool(args[i])
            if type not in self.structs and args[i].type() != type:
                super().error(
                    ErrorType.TYPE_ERROR,
                    f"{args[i].type()} cannot be assigned to a {type}",
                )
            if (
                type in self.structs
                and args[i].type() in self.structs
                and type != args[i].type()
            ):
                super().error(
                    ErrorType.TYPE_ERROR,
                    f"Struct type {args[i].type()} cannot be assigned to struct type {type}",
                )
            if args[i].type() == Type.NIL and type in self.structs:
                self.variables.create(name, Value(type))
            else:
                self.variables.create(name, args[i])

        for statement_node in func_node.dict["statements"]:
            res = self.run_statement(statement_node)

            # if statement_node is a return, return that value
            if res:
                self.variables.pop_scope()
                if res.type() == Type.VOID:
                    return self.return_default(return_type)
                self.check_return(return_type, res)
                return res

        # otherwise, return the default return value
        self.variables.pop_scope()
        return self.return_default(return_type)

    def run_statement(self, statement_node):
        match statement_node.elem_type:
            # variable definition
            case "vardef":
                name = statement_node.dict["name"]
                type = statement_node.dict["var_type"]
                self.type_to_variable(name, type)
            # assignment
            case "=":
                name = statement_node.dict["name"]
                node = statement_node.dict["expression"]
                value = self.evaluate_expression(node)

                # if struct variable
                if "." in name:
                    self.set_nested_variable(name, value)
                else:
                    if not self.variables.get(name):
                        super().error(
                            ErrorType.NAME_ERROR,
                            f"Assign: Variable {name} has not been defined",
                        )

                    type = self.variables.get(name).type()
                    self.check_return(type, value)

                    # setting the variable
                    if type in self.structs and value.type() == Type.NIL:
                        res = self.variables.set(name, Value(type))
                    else:
                        if value.type() == Type.NIL:
                            super().error(
                                ErrorType.TYPE_ERROR,
                                f"Assign: Assigning {name} with a nil type",
                            )
                        res = self.variables.set(name, value)
                        if not res:
                            super().error(
                                ErrorType.NAME_ERROR,
                                f"Assign: Unable to set {name}",
                            )
            # function call
            case "fcall":
                self.run_function_call(statement_node)
            # if statement
            case "if":
                self.variables.push_scope("if")

                condition = statement_node.dict["condition"]
                statements = statement_node.dict["statements"]
                else_statements = statement_node.dict["else_statements"]

                # test if statement
                cond = self.evaluate_expression(condition)
                # coercion if int
                cond = self.check_bool(cond)

                if cond.type() != Type.BOOL:
                    super().error(
                        ErrorType.TYPE_ERROR,
                        "Invalid if condition",
                    )

                if cond.value():
                    for statement in statements:
                        res = self.run_statement(statement)
                        if res:
                            self.variables.pop_scope()
                            return res
                # if if statement fails, test else statement
                else:
                    if else_statements:
                        for statement in else_statements:
                            res = self.run_statement(statement)
                            if res:
                                self.variables.pop_scope()
                                return res

                self.variables.pop_scope()
            # for loop
            case "for":
                # assignment statement
                init = statement_node.dict["init"]
                condition = statement_node.dict["condition"]
                statements = statement_node.dict["statements"]

                self.run_statement(init)

                # condition must be true
                cond = self.evaluate_expression(condition)
                # coercion if int
                cond = self.check_bool(cond)

                if cond.type() != Type.BOOL:
                    super().error(
                        ErrorType.TYPE_ERROR,
                        "Invalid for condition",
                    )

                while cond.value():
                    self.variables.push_scope("for")
                    for statement in statements:
                        res = self.run_statement(statement)
                        if res:
                            self.variables.pop_scope()
                            return res
                    self.variables.pop_scope()

                    update = statement_node.dict["update"]
                    self.run_statement(update)
                    cond = self.evaluate_expression(condition)
            # return
            case "return":
                expression = statement_node.dict["expression"]
                return (
                    self.evaluate_expression(expression)
                    if expression
                    else Value(Type.VOID)
                )

    def evaluate_expression(self, expression_node):
        # binary operations
        if expression_node.elem_type in Interpreter.binary_operators:
            op1 = self.evaluate_expression(expression_node.dict["op1"])
            op2 = self.evaluate_expression(expression_node.dict["op2"])

            # print("op1", op1.type(), op1.value())
            # print("op2", op2.type(), op2.value())

            match expression_node.elem_type:
                case "+":
                    if (op1.type() == Type.INT and op2.type() == Type.INT) or (
                        op1.type() == Type.STRING and op2.type() == Type.STRING
                    ):
                        return create_value(op1.value() + op2.value())
                    super().error(
                        ErrorType.TYPE_ERROR,
                        "Illegal usage of arithmetic operation on non-integer types",
                    )
                case "-":
                    if op1.type() != Type.INT or op2.type() != Type.INT:
                        super().error(
                            ErrorType.TYPE_ERROR,
                            "Illegal usage of arithmetic operation on non-integer types",
                        )
                    return Value(Type.INT, op1.value() - op2.value())
                case "*":
                    if op1.type() != Type.INT or op2.type() != Type.INT:
                        super().error(
                            ErrorType.TYPE_ERROR,
                            "Illegal usage of arithmetic operation on non-integer types",
                        )
                    return Value(Type.INT, op1.value() * op2.value())
                case "/":
                    if op1.type() != Type.INT or op2.type() != Type.INT:
                        super().error(
                            ErrorType.TYPE_ERROR,
                            "Illegal usage of arithmetic operation on non-integer types",
                        )
                    return Value(Type.INT, op1.value() // op2.value())
                case "==":
                    if op1.type() == Type.VOID or op2.type() == Type.VOID:
                        super().error(
                            ErrorType.TYPE_ERROR,
                            "Comparing with a void value",
                        )
                    if (
                        op1.type() in self.structs or op2.type() in self.structs
                    ) and not (
                        op1.type() == op2.type()
                        or op1.type() == Type.NIL
                        or op2.type() == Type.NIL
                    ):
                        super().error(
                            ErrorType.TYPE_ERROR,
                            "Comparing a struct type to a different type",
                        )
                    if op1.value() is None and op2.value() is None:
                        return Value(Type.BOOL, True)
                    if op1.type() == Type.BOOL or op2.type() == Type.BOOL:
                        op1 = self.check_bool(op1)
                        op2 = self.check_bool(op2)
                    if (
                        op1.type() in Interpreter.default_types
                        or op2.type() in Interpreter.default_types
                    ) and op1.type() != op2.type():
                        super().error(
                            ErrorType.TYPE_ERROR,
                            "Comparing different primitive types",
                        )
                    return Value(Type.BOOL, op1.value() == op2.value())
                case "<":
                    if op1.type() != Type.INT or op2.type() != Type.INT:
                        super().error(
                            ErrorType.TYPE_ERROR,
                            "Incompatible types for comparison <",
                        )
                    return Value(Type.BOOL, op1.value() < op2.value())
                case "<=":
                    if op1.type() != Type.INT or op2.type() != Type.INT:
                        super().error(
                            ErrorType.TYPE_ERROR,
                            "Incompatible types for comparison <=",
                        )
                    return Value(Type.BOOL, op1.value() <= op2.value())
                case ">":
                    if op1.type() != Type.INT or op2.type() != Type.INT:
                        super().error(
                            ErrorType.TYPE_ERROR,
                            "Incompatible types for comparison >",
                        )
                    return Value(Type.BOOL, op1.value() > op2.value())
                case ">=":
                    if op1.type() != Type.INT or op2.type() != Type.INT:
                        super().error(
                            ErrorType.TYPE_ERROR,
                            "Incompatible types for comparison >=",
                        )
                    return Value(Type.BOOL, op1.value() >= op2.value())
                case "!=":
                    if op1.type() == Type.VOID or op2.type() == Type.VOID:
                        super().error(
                            ErrorType.TYPE_ERROR,
                            "Comparing with a void value",
                        )
                    if (
                        op1.type() in self.structs or op2.type() in self.structs
                    ) and not (
                        op1.type() == op2.type()
                        or op1.type() == Type.NIL
                        or op2.type() == Type.NIL
                    ):
                        super().error(
                            ErrorType.TYPE_ERROR,
                            "Comparing a struct type to a different type",
                        )
                    if op1.value() is None and op2.value() is None:
                        return Value(Type.BOOL, False)
                    if op1.type() == Type.BOOL or op2.type() == Type.BOOL:
                        op1 = self.check_bool(op1)
                        op2 = self.check_bool(op2)
                    if (
                        op1.type() in Interpreter.default_types
                        or op2.type() in Interpreter.default_types
                    ) and op1.type() != op2.type():
                        super().error(
                            ErrorType.TYPE_ERROR,
                            "Comparing different primitive types",
                        )
                    return Value(Type.BOOL, op1.value() != op2.value())
                case "&&":
                    op1 = self.check_bool(op1)
                    op2 = self.check_bool(op2)
                    if op1.type() != Type.BOOL or op2.type() != Type.BOOL:
                        super().error(
                            ErrorType.TYPE_ERROR,
                            "Incompatible types for comparison &&",
                        )
                    left, right = op1.value(), op2.value()
                    if left is True and right is True:
                        return Value(Type.BOOL, True)
                    else:
                        return Value(Type.BOOL, False)
                case "||":
                    op1 = self.check_bool(op1)
                    op2 = self.check_bool(op2)
                    if op1.type() != Type.BOOL or op2.type() != Type.BOOL:
                        super().error(
                            ErrorType.TYPE_ERROR,
                            "Incompatible types for comparison ||",
                        )
                    left, right = op1.value(), op2.value()
                    if left is True or right is True:
                        return Value(Type.BOOL, True)
                    else:
                        return Value(Type.BOOL, False)
        else:
            match expression_node.elem_type:
                # value node
                case "int" | "string" | "bool":
                    return create_value(expression_node.dict["val"])
                case "nil":
                    return Value(Type.NIL)
                # variable node
                case "var":
                    name = expression_node.dict["name"]
                    result = self.get_nested_variable(name)
                    return result
                # unary operations
                case "neg":
                    op1 = self.evaluate_expression(expression_node.dict["op1"])
                    if op1.type() != Type.INT and op1.type() != Type.STRING:
                        super().error(
                            ErrorType.TYPE_ERROR,
                            "Invalid negation type",
                        )
                    return Value(Type.INT, -op1.value())
                case "!":
                    op1 = self.evaluate_expression(expression_node.dict["op1"])
                    op1 = self.check_bool(op1)
                    if op1.type() != Type.BOOL:
                        super().error(
                            ErrorType.TYPE_ERROR,
                            "Illegal usage of not operation on non-boolean type",
                        )
                    return (
                        Value(Type.BOOL, True)
                        if op1.value() is False
                        else Value(Type.BOOL, False)
                    )
                # new instance
                case "new":
                    var_type = expression_node.dict["var_type"]
                    if var_type not in self.structs:
                        super().error(
                            ErrorType.TYPE_ERROR,
                            "Invalid struct type",
                        )
                    # create variables for all the struct-specific variables
                    struct = self.structs[var_type]
                    variables = {}
                    for var in struct.dict["fields"]:
                        name = var.dict["name"]
                        type = var.dict["var_type"]
                        if type in Interpreter.default_types:
                            variables[name] = Value(
                                type, Interpreter.default_types[type]
                            )
                        else:
                            if type not in self.structs:
                                super().error(
                                    ErrorType.TYPE_ERROR,
                                    "Unrecognized type for variable in struct",
                                )
                            variables[name] = Value(type)

                    # return a reference to the struct
                    return Value(var_type, variables)
                # function call
                case "fcall":
                    return self.run_function_call(expression_node)

    def run_function_call(self, function_call):
        name = function_call.dict["name"]
        arg_nodes = function_call.dict["args"]
        match name:
            case "print":
                res = ""
                for arg in function_call.dict["args"]:
                    output = self.evaluate_expression(arg)
                    if output.type() == Type.VOID:
                        super().error(
                            ErrorType.TYPE_ERROR,
                            "Using void in print",
                        )
                    res += get_printable(output)

                super().output(res)
                # self.variables.print()
                return Value(Type.VOID)
            case "inputi":
                if len(function_call.dict["args"]) > 1:
                    super().error(
                        ErrorType.NAME_ERROR,
                        "No inputi() function found that takes > 1 parameter",
                    )
                elif len(function_call.dict["args"]) == 1:
                    super().output(function_call.dict["args"][0].dict["val"])

                return Value(Type.INT, int(super().get_input()))
            case "inputs":
                if len(function_call.dict["args"]) > 1:
                    super().error(
                        ErrorType.NAME_ERROR,
                        "No inputs() function found that takes > 1 parameter",
                    )
                elif len(function_call.dict["args"]) == 1:
                    super().output(function_call.dict["args"][0].dict["val"])

                return Value(Type.STRING, super().get_input())
            case _:
                for function in self.functions:
                    # if same name and same amount of args
                    if function.dict["name"] == name and len(arg_nodes) == len(
                        function.dict["args"]
                    ):
                        args = []
                        for arg in arg_nodes:
                            args.append(self.evaluate_expression(arg))
                        res = self.run_function(function, args)
                        return res if res else Value(Type.VOID)

                super().error(
                    ErrorType.NAME_ERROR,
                    f"Function {name} has not been defined",
                )

    def check_return(self, return_type, return_value):
        # return_type is the return type of the function
        # return_value is the value we're returning from the function

        # print(
        #     "return_type",
        #     return_type,
        #     "return_value",
        #     return_value.value(),
        #     return_value.type(),
        # )

        # void function returning something
        if return_type == Type.VOID and return_value.value():
            super().error(
                ErrorType.TYPE_ERROR,
                "Returning a value from a void function",
            )
        # not a struct variable and assigning nil
        if (
            return_type not in self.structs
            and return_type != Type.NIL
            and return_value.type() == Type.NIL
        ):
            super().error(
                ErrorType.TYPE_ERROR,
                f"nil cannot be assigned to a {return_type} (1)",
            )
        # mismatched struct types
        if (
            return_type in self.structs
            and return_value.type() != return_type
            and return_value.type() != Type.NIL
        ):
            super().error(
                ErrorType.TYPE_ERROR,
                "Incorrect struct type return",
            )
        # if return type is bool and return value is int (coercion)
        if return_type == Type.BOOL and return_value.type() == Type.INT:
            self.convert_to_bool(return_value)
        # mismatched primitive types
        if (
            return_type in Interpreter.default_types
            and return_type != return_value.type()
        ):
            super().error(
                ErrorType.TYPE_ERROR,
                f"{return_value.type()} cannot be assigned to a {return_type} (2)",
            )

    def check_field_access(self, obj, var):
        # variable to the left of a dot is nil
        if obj is None:
            super().error(
                ErrorType.FAULT_ERROR,
                "CFA: Variable to the left of a dot is nil",
            )
        # variable to the left of a dot is not a struct
        if not isinstance(obj, dict):
            super().error(
                ErrorType.TYPE_ERROR,
                "CFA: Variable to the left of a dot is not a struct",
            )
        # invalid field name
        if var not in obj:
            super().error(
                ErrorType.NAME_ERROR,
                f"CFA: {var} does not exist",
            )

    # checks and returns the bool equiv of an int
    def check_bool(self, val):
        if val.type() != Type.INT:
            return val
        else:
            if val.value() == 0:
                return Value(Type.BOOL, False)
            else:
                return Value(Type.BOOL, True)

    # converts a value from int to bool
    def convert_to_bool(self, val):
        if val.type() == Type.INT:
            if val.value() == 0:
                val.set(Type.BOOL, False)
            else:
                val.set(Type.BOOL, True)

    def type_to_variable(self, name, type):
        match type:
            case "bool":
                res = self.variables.create(name, Value(Type.BOOL, False))
            case "int":
                res = self.variables.create(name, Value(Type.INT, 0))
            case "string":
                res = self.variables.create(name, Value(Type.STRING, ""))
            case _:
                # if type is a struct
                if type in self.structs:
                    # create a variable for the one representing the struct
                    res = self.variables.create(name, Value(type))
                else:
                    # no matching types
                    super().error(
                        ErrorType.TYPE_ERROR,
                        "Not a valid type for a variable",
                    )
        if not res:
            super().error(
                ErrorType.NAME_ERROR,
                f"TTV: Variable {name} defined more than once",
            )

    def return_default(self, type):
        match type:
            case "bool":
                return Value(Type.BOOL, False)
            case "int":
                return Value(Type.INT, 0)
            case "string":
                return Value(Type.STRING, "")
            case "void":
                return Value(Type.VOID)
            case _:
                return Value(Type.NIL)

    def get_nested_variable(self, name):
        parts = name.split(".")
        current = self.variables.get(parts[0])

        if not current:
            super().error(
                ErrorType.NAME_ERROR,
                f"GNV: Variable {name} has not been defined",
            )

        for part in parts[1:]:
            current = current.value()
            self.check_field_access(current, part)
            current = current[part]

        return current

    def set_nested_variable(self, name, value):
        parts = name.split(".")
        current = self.variables.get(parts[0])

        if not current:
            super().error(
                ErrorType.NAME_ERROR,
                f"SNV: Variable {name} has not been defined",
            )

        # traverse until the second-to-last part
        for part in parts[1:-1]:
            current = current.value()
            self.check_field_access(current, part)
            current = current[part]

        # set the final part to the new value
        last_part = parts[-1]
        current = current.value()

        self.check_field_access(current, last_part)
        self.check_return(current[last_part].type(), value)

        current[last_part] = value


if __name__ == "__main__":
    program = """

    struct list {
    val: int;
    next: list;
    }

func merge(l1: list, l2: list) : list {
    if (l1 == nil) {
        return l2;
    }
    if (l2 == nil) {
        return l1;
    }

    if (l1.val <= l2.val) {
        l1.next = merge(l1.next, l2);
        return l1;
    } else {
        l2.next = merge(l1, l2.next);
        return l2;
    }
}


func print_list(l: list): void {
    var x: list;
    var n: int;
    for (x = l; x != nil; x = x.next) {
        print(x.val);
        n = n + 1;
    }
    print("N=", n);
}

func cons(val: int, l: list) : list {
    var h: list;
    h = new list;
    h.val = val;
    h.next = l;
    return h;
}

func main() : void {
    var l1: list;
    var l2: list;
    var result: list;
    var n: int;
    var i: int;

    n = inputi();
    for (i = 0; i < n; i = i + 1) {
        var v: int;
        v = inputi();
        l1 = cons(v, l1);
    }

    n = inputi();
    for (i = 0; i < n; i = i + 1) {
        var v: int;
        v = inputi();
        l2 = cons(v, l2);
    }

    result = merge(l1, l2);
    print_list(result);
}
"""
    interpreter = Interpreter()
    interpreter.run(program)
