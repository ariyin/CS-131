from enum import Enum
from intbase import InterpreterBase, ErrorType
from brewparse import parse_program
from env_v4 import EnvironmentManager
from type_valuev4 import Type, Value, LazyValue, create_value, get_printable


class ExecStatus(Enum):
    CONTINUE = 1
    RETURN = 2
    RAISE = 3


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

    def __init__(self, console_output=True, inp=None, trace_output=False):
        # call InterpreterBase's constructor
        super().__init__(console_output, inp)
        self.functions = []

    def run(self, program):
        ast = parse_program(program)
        self.variables = EnvironmentManager()
        main_func_node = None
        for function in ast.dict["functions"]:
            if function.dict["name"] == "main":
                main_func_node = function
            else:
                self.functions.append(function)

        if not main_func_node:
            super().error(
                ErrorType.NAME_ERROR,
                "No main() function was found",
            )
        status, _ = self.run_function(main_func_node)
        if status == ExecStatus.RAISE:
            super().error(
                ErrorType.FAULT_ERROR,
                "Uncaught raise",
            )

    def run_function(self, func_node, args=None, env=None):
        if not env:
            env = self.variables

        self.variables.push_scope("function")
        temp_args = func_node.dict["args"]

        # instantiate args with the right values
        for i in range(len(temp_args)):
            self.variables.create(temp_args[i].dict["name"], LazyValue(args[i], env))

        for statement_node in func_node.dict["statements"]:
            status, res = self.run_statement(statement_node, env)
            # if statement_node is a return, return that value
            if status == ExecStatus.RETURN or status == ExecStatus.RAISE:
                self.variables.pop_scope()
                return (status, res)

        # otherwise return NIL
        self.variables.pop_scope()
        return (ExecStatus.CONTINUE, Value(Type.NIL))

    def run_statement(self, statement_node, env=None):
        if not env:
            env = self.variables

        match statement_node.elem_type:
            # variable definition
            case "vardef":
                name = statement_node.dict["name"]
                if not self.variables.create(name, Value(Type.NIL)):
                    super().error(
                        ErrorType.NAME_ERROR,
                        f"Vardef: Variable {name} defined more than once",
                    )
            # assignment
            case "=":
                name = statement_node.dict["name"]
                node = statement_node.dict["expression"]
                lazy = LazyValue(node, self.variables.copy())
                if not self.variables.set(name, lazy):
                    super().error(
                        ErrorType.NAME_ERROR,
                        f"Equal: Variable {name} has not been defined",
                    )
            # function call
            case "fcall":
                status, res = self.run_function_call(statement_node)
                return (status, res)
            # if statement
            case "if":
                self.variables.push_scope("if")

                condition = statement_node.dict["condition"]
                statements = statement_node.dict["statements"]
                else_statements = statement_node.dict["else_statements"]

                # test if statement
                status, cond = self.evaluate_expression_and_lazy(condition)
                if status == ExecStatus.RAISE:
                    return (status, cond)
                if cond.type() != Type.BOOL:
                    super().error(
                        ErrorType.TYPE_ERROR,
                        "Invalid if condition",
                    )

                if cond.value():
                    for statement in statements:
                        status, res = self.run_statement(statement)
                        if status == ExecStatus.RETURN or status == ExecStatus.RAISE:
                            self.variables.pop_scope()
                            return (status, res)
                # if if statement fails, test else statement
                else:
                    if else_statements:
                        for statement in else_statements:
                            status, res = self.run_statement(statement)
                            if (
                                status == ExecStatus.RETURN
                                or status == ExecStatus.RAISE
                            ):
                                self.variables.pop_scope()
                                return (status, res)

                self.variables.pop_scope()
            # for loop
            case "for":
                # assignment statement
                init = statement_node.dict["init"]
                condition = statement_node.dict["condition"]
                statements = statement_node.dict["statements"]

                status, res = self.run_statement(init)
                if status == ExecStatus.RAISE:
                    return (status, res)

                # condition must be true
                status, cond = self.evaluate_expression_and_lazy(condition)
                if status == ExecStatus.RAISE:
                    return (status, cond)
                if cond.type() != Type.BOOL:
                    super().error(
                        ErrorType.TYPE_ERROR,
                        "Invalid for condition",
                    )

                while cond.value():
                    self.variables.push_scope("for")
                    for statement in statements:
                        status, res = self.run_statement(statement)
                        if status == ExecStatus.RETURN or status == ExecStatus.RAISE:
                            self.variables.pop_scope()
                            return (status, res)
                    self.variables.pop_scope()

                    update = statement_node.dict["update"]
                    status, res = self.run_statement(update)
                    if status == ExecStatus.RAISE:
                        return (status, res)
                    status, cond = self.evaluate_expression_and_lazy(condition)
                    if status == ExecStatus.RAISE:
                        return (status, cond)
            # return
            case "return":
                expression = statement_node.dict["expression"]
                if expression is None:
                    return (ExecStatus.RETURN, Value(Type.NIL))

                return (ExecStatus.RETURN, LazyValue(expression, self.variables.copy()))
            # try
            case "try":
                statements = statement_node.dict["statements"]
                catchers = statement_node.dict["catchers"]

                self.variables.push_scope("try")

                for statement in statements:
                    status, res = self.run_statement(statement)
                    if status == ExecStatus.RETURN:
                        self.variables.pop_scope()
                        return (status, res)
                    elif status == ExecStatus.RAISE:
                        self.variables.pop_scope()
                        for catch in catchers:
                            catch_type, catch_statements = self.run_statement(catch)
                            # matching raise / catch
                            # execute catch block
                            if catch_type == res.value():
                                self.variables.push_scope("catch")
                                for statement in catch_statements:
                                    status, res = self.run_statement(statement)
                                    if (
                                        status == ExecStatus.RETURN
                                        or status == ExecStatus.RAISE
                                    ):
                                        self.variables.pop_scope()
                                        return (status, res)
                                self.variables.pop_scope()
                                return (ExecStatus.CONTINUE, None)
                        # no match
                        return (ExecStatus.RAISE, res)

                # try block finishes normally
                self.variables.pop_scope()
                return (ExecStatus.CONTINUE, None)
            # catch
            case "catch":
                type = statement_node.dict["exception_type"]
                statements = statement_node.dict["statements"]
                return (type, statements)
            # raise
            case "raise":
                type = statement_node.dict["exception_type"]
                _, value = self.evaluate_expression(type)
                if isinstance(value, LazyValue):
                    _, value = self.evaluate_lazy(value)
                if value.type() != Type.STRING:
                    super().error(
                        ErrorType.TYPE_ERROR,
                        "Raise type not a string",
                    )

                # return what we're raising
                return (ExecStatus.RAISE, value)

        return (ExecStatus.CONTINUE, None)

    def evaluate_expression(self, expression_node, env=None):
        if not env:
            env = self.variables
        # binary operations
        if expression_node.elem_type in Interpreter.binary_operators:
            match expression_node.elem_type:
                case "+":
                    status, op1, op2 = self.get_ops(expression_node, env)
                    if status == ExecStatus.RAISE:
                        return (ExecStatus.RAISE, op1 or op2)
                    if (op1.type() == Type.INT and op2.type() == Type.INT) or (
                        op1.type() == Type.STRING and op2.type() == Type.STRING
                    ):
                        return (
                            ExecStatus.CONTINUE,
                            create_value(op1.value() + op2.value()),
                        )

                    super().error(
                        ErrorType.TYPE_ERROR,
                        "Illegal usage of arithmetic operation on non-integer types",
                    )
                case "-":
                    status, op1, op2 = self.get_ops(expression_node, env)
                    if status == ExecStatus.RAISE:
                        return (ExecStatus.RAISE, op1 or op2)
                    if op1.type() != Type.INT or op2.type() != Type.INT:
                        super().error(
                            ErrorType.TYPE_ERROR,
                            "Illegal usage of arithmetic operation on non-integer types",
                        )
                    return (
                        ExecStatus.CONTINUE,
                        Value(Type.INT, op1.value() - op2.value()),
                    )
                case "*":
                    status, op1, op2 = self.get_ops(expression_node, env)
                    if status == ExecStatus.RAISE:
                        return (ExecStatus.RAISE, op1 or op2)
                    if op1.type() != Type.INT or op2.type() != Type.INT:
                        super().error(
                            ErrorType.TYPE_ERROR,
                            "Illegal usage of arithmetic operation on non-integer types",
                        )
                    return (
                        ExecStatus.CONTINUE,
                        Value(Type.INT, op1.value() * op2.value()),
                    )
                case "/":
                    status, op1, op2 = self.get_ops(expression_node, env)
                    if status == ExecStatus.RAISE:
                        return (ExecStatus.RAISE, op1 or op2)
                    # divide by 0
                    if op2.value() == 0:
                        return (ExecStatus.RAISE, Value(Type.STRING, "div0"))
                    if op1.type() != Type.INT or op2.type() != Type.INT:
                        super().error(
                            ErrorType.TYPE_ERROR,
                            "Illegal usage of arithmetic operation on non-integer types",
                        )
                    return (
                        ExecStatus.CONTINUE,
                        Value(Type.INT, op1.value() // op2.value()),
                    )
                case "==":
                    status, op1, op2 = self.get_ops(expression_node, env)
                    if status == ExecStatus.RAISE:
                        return (ExecStatus.RAISE, op1 or op2)
                    if op1.type() != op2.type():
                        return (ExecStatus.CONTINUE, Value(Type.BOOL, False))
                    return (
                        ExecStatus.CONTINUE,
                        Value(Type.BOOL, op1.value() == op2.value()),
                    )
                case "<":
                    status, op1, op2 = self.get_ops(expression_node, env)
                    if status == ExecStatus.RAISE:
                        return (ExecStatus.RAISE, op1 or op2)
                    if op1.type() != Type.INT or op2.type() != Type.INT:
                        super().error(
                            ErrorType.TYPE_ERROR,
                            "Incompatible types for comparison <",
                        )
                    return (
                        ExecStatus.CONTINUE,
                        Value(Type.BOOL, op1.value() < op2.value()),
                    )
                case "<=":
                    status, op1, op2 = self.get_ops(expression_node, env)
                    if status == ExecStatus.RAISE:
                        return (ExecStatus.RAISE, op1 or op2)
                    if op1.type() != Type.INT or op2.type() != Type.INT:
                        super().error(
                            ErrorType.TYPE_ERROR,
                            "Incompatible types for comparison <=",
                        )
                    return (
                        ExecStatus.CONTINUE,
                        Value(Type.BOOL, op1.value() <= op2.value()),
                    )
                case ">":
                    status, op1, op2 = self.get_ops(expression_node, env)
                    if status == ExecStatus.RAISE:
                        return (ExecStatus.RAISE, op1 or op2)
                    if op1.type() != Type.INT or op2.type() != Type.INT:
                        super().error(
                            ErrorType.TYPE_ERROR,
                            "Incompatible types for comparison >",
                        )
                    return (
                        ExecStatus.CONTINUE,
                        Value(Type.BOOL, op1.value() > op2.value()),
                    )
                case ">=":
                    status, op1, op2 = self.get_ops(expression_node, env)
                    if status == ExecStatus.RAISE:
                        return (ExecStatus.RAISE, op1 or op2)
                    if op1.type() != Type.INT or op2.type() != Type.INT:
                        super().error(
                            ErrorType.TYPE_ERROR,
                            "Incompatible types for comparison >=",
                        )
                    return (
                        ExecStatus.CONTINUE,
                        Value(Type.BOOL, op1.value() >= op2.value()),
                    )
                case "!=":
                    status, op1, op2 = self.get_ops(expression_node, env)
                    if status == ExecStatus.RAISE:
                        return (ExecStatus.RAISE, op1 or op2)
                    if op1.type() != op2.type():
                        return (ExecStatus.CONTINUE, Value(Type.BOOL, True))
                    return (
                        ExecStatus.CONTINUE,
                        Value(Type.BOOL, op1.value() != op2.value()),
                    )
                case "&&":
                    status, op1 = self.evaluate_expression_and_lazy(
                        expression_node.dict["op1"], env
                    )
                    if status == ExecStatus.RAISE:
                        return (status, op1)
                    if op1.type() != Type.BOOL:
                        super().error(
                            ErrorType.TYPE_ERROR,
                            "Incompatible types for comparison &&",
                        )
                    if not op1.value():
                        return (ExecStatus.CONTINUE, Value(Type.BOOL, False))

                    status, op2 = self.evaluate_expression_and_lazy(
                        expression_node.dict["op2"], env
                    )
                    if status == ExecStatus.RAISE:
                        return (status, op2)
                    if op2.type() != Type.BOOL:
                        super().error(
                            ErrorType.TYPE_ERROR,
                            "Incompatible types for comparison &&",
                        )
                    return (ExecStatus.CONTINUE, Value(Type.BOOL, op2.value()))
                case "||":
                    status, op1 = self.evaluate_expression_and_lazy(
                        expression_node.dict["op1"], env
                    )
                    if status == ExecStatus.RAISE:
                        return (status, op1)
                    if op1.type() != Type.BOOL:
                        super().error(
                            ErrorType.TYPE_ERROR,
                            "Incompatible types for comparison ||",
                        )
                    if op1.value():
                        return (ExecStatus.CONTINUE, Value(Type.BOOL, True))

                    status, op2 = self.evaluate_expression_and_lazy(
                        expression_node.dict["op2"], env
                    )
                    if status == ExecStatus.RAISE:
                        return (status, op2)
                    if op2.type() != Type.BOOL:
                        super().error(
                            ErrorType.TYPE_ERROR,
                            "Incompatible types for comparison &&",
                        )
                    return (ExecStatus.CONTINUE, Value(Type.BOOL, op2.value()))
        else:
            match expression_node.elem_type:
                # value node
                case "int" | "string" | "bool":
                    return (
                        ExecStatus.CONTINUE,
                        create_value(expression_node.dict["val"]),
                    )
                case "nil":
                    return (ExecStatus.CONTINUE, Value(Type.NIL))
                # variable node
                case "var":
                    name = expression_node.dict["name"]
                    result = env.get(name)
                    if result is None:
                        super().error(
                            ErrorType.NAME_ERROR,
                            f"EE Var: Variable {name} has not been defined",
                        )
                    return (ExecStatus.CONTINUE, result)
                # unary operations
                case "neg":
                    status, op1 = self.evaluate_expression_and_lazy(
                        expression_node.dict["op1"], env
                    )
                    if status == ExecStatus.RAISE:
                        return (status, op1)
                    if op1.type() != Type.INT and op1.type() != Type.STRING:
                        super().error(
                            ErrorType.TYPE_ERROR,
                            "Invalid negation type",
                        )
                    return (ExecStatus.CONTINUE, Value(Type.INT, -op1.value()))
                case "!":
                    status, op1 = self.evaluate_expression_and_lazy(
                        expression_node.dict["op1"], env
                    )
                    if status == ExecStatus.RAISE:
                        return (status, op1)
                    if op1.type() != Type.BOOL:
                        super().error(
                            ErrorType.TYPE_ERROR,
                            "Illegal usage of not operation on non-boolean type",
                        )
                    return (
                        (ExecStatus.CONTINUE, Value(Type.BOOL, True))
                        if op1.value() is False
                        else (ExecStatus.CONTINUE, Value(Type.BOOL, False))
                    )
                # function call
                case "fcall":
                    status, res = self.run_function_call(expression_node, env)
                    return (status, res)

    def run_function_call(self, function_call, env=None):
        if not env:
            env = self.variables

        name = function_call.dict["name"]
        arg_nodes = function_call.dict["args"]
        match name:
            case "print":
                res = ""
                for arg in function_call.dict["args"]:
                    status, output = self.evaluate_expression_and_lazy(arg, env)
                    if status == ExecStatus.RAISE:
                        return (status, output)
                    res += get_printable(output)

                super().output(res)
                return (ExecStatus.CONTINUE, Value(Type.NIL))
            case "inputi":
                if len(function_call.dict["args"]) > 1:
                    super().error(
                        ErrorType.NAME_ERROR,
                        "No inputi() function found that takes > 1 parameter",
                    )
                elif len(function_call.dict["args"]) == 1:
                    status, output = self.evaluate_expression_and_lazy(
                        function_call.dict["args"][0], env
                    )
                    if status == ExecStatus.RAISE:
                        return (status, output)
                    super().output(output.value())

                return (ExecStatus.CONTINUE, Value(Type.INT, int(super().get_input())))
            case "inputs":
                if len(function_call.dict["args"]) > 1:
                    super().error(
                        ErrorType.NAME_ERROR,
                        "No inputs() function found that takes > 1 parameter",
                    )
                elif len(function_call.dict["args"]) == 1:
                    status, output = self.evaluate_expression_and_lazy(
                        function_call.dict["args"][0], env
                    )
                    if status == ExecStatus.RAISE:
                        return (status, output)
                    super().output(output.value())

                return (ExecStatus.CONTINUE, Value(Type.STRING, super().get_input()))
            case _:
                for function in self.functions:
                    # if same name and same amount of args
                    if function.dict["name"] == name and len(arg_nodes) == len(
                        function.dict["args"]
                    ):
                        status, res = self.run_function(function, arg_nodes, env.copy())
                        if status == ExecStatus.RETURN:
                            return (ExecStatus.CONTINUE, res)
                        elif status == ExecStatus.RAISE:
                            return (status, res)
                        # return NIL if no return value
                        return (ExecStatus.CONTINUE, Value(Type.NIL))

                super().error(
                    ErrorType.NAME_ERROR,
                    f"Function {name} has not been defined",
                )

    def evaluate_lazy(self, val):
        if not val.evaluated():
            status, res = self.evaluate_expression(val.ast(), val.env())
            if status == ExecStatus.RAISE:
                return (status, res)
            while isinstance(res, LazyValue):
                status, res = self.evaluate_lazy(res)
                if status == ExecStatus.RAISE:
                    return (status, res)
            val.set_value(res)
            val.set_eval()

        # should return a fully evaluated Value
        return (ExecStatus.CONTINUE, val.value())

    def evaluate_expression_and_lazy(self, exp, env=None):
        status, output = self.evaluate_expression(exp, env)
        if status == ExecStatus.RAISE:
            return (status, output)
        if isinstance(output, LazyValue):
            status, output = self.evaluate_lazy(output)
            if status == ExecStatus.RAISE:
                return (status, output)

        return (status, output)

    # gets op1 and op2 when evaluating an expression
    def get_ops(self, expression_node, env):
        status1, op1 = self.evaluate_expression_and_lazy(
            expression_node.dict["op1"], env
        )
        if status1 == ExecStatus.RAISE:
            return (status1, op1, None)
        status2, op2 = self.evaluate_expression_and_lazy(
            expression_node.dict["op2"], env
        )
        if status2 == ExecStatus.RAISE:
            return (status2, None, op2)

        return (ExecStatus.CONTINUE, op1, op2)


if __name__ == "__main__":
    #     program = """func main() {
    #   var a;
    #   foo("entered function");
    # }

    # func foo(a) {
    #   print(a);
    #   var a;
    # }
    # """

    program = """func foo(x) {
  var y;
  y = 5;
  print(x);
}

func main() {
  var y;
  y = 10;
  foo(y);
}

/*
*OUT*
10
*OUT*
*/
"""

    interpreter = Interpreter()
    interpreter.run(program)
