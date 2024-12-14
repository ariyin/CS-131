from intbase import InterpreterBase, ErrorType
from brewparse import parse_program
from env_v2 import EnvironmentManager
from type_valuev2 import Type, Value, create_value, get_printable


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
        self.run_function(main_func_node)

    def run_function(self, func_node, args=None):
        self.variables.push_scope("function")
        temp_args = func_node.dict["args"]

        # instantiate args with the right values
        for i in range(len(temp_args)):
            self.variables.create(temp_args[i].dict["name"], args[i])

        for statement_node in func_node.dict["statements"]:
            res = self.run_statement(statement_node)
            # if statement_node is a return, return that value
            if res:
                self.variables.pop_scope()
                return res

        # otherwise return NIL
        self.variables.pop_scope()
        return Value(Type.NIL)

    def run_statement(self, statement_node):
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
                if not self.variables.set(name, self.evaluate_expression(node)):
                    super().error(
                        ErrorType.NAME_ERROR,
                        f"Equal: Variable {name} has not been defined",
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
                    else Value(Type.NIL)
                )

    def evaluate_expression(self, expression_node):
        # binary operations
        if expression_node.elem_type in Interpreter.binary_operators:
            op1 = self.evaluate_expression(expression_node.dict["op1"])
            op2 = self.evaluate_expression(expression_node.dict["op2"])

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
                    if op1.type() != op2.type():
                        return Value(Type.BOOL, False)
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
                    if op1.type() != op2.type():
                        return Value(Type.BOOL, True)
                    return Value(Type.BOOL, op1.value() != op2.value())
                case "&&":
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
                    result = self.variables.get(name)
                    if result is None:
                        super().error(
                            ErrorType.NAME_ERROR,
                            f"EE Var: Variable {name} has not been defined",
                        )
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
                    res += get_printable(self.evaluate_expression(arg))

                super().output(res)
                return Value(Type.NIL)
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
                        # return NIL if no return value
                        return res if res else Value(Type.NIL)

                super().error(
                    ErrorType.NAME_ERROR,
                    f"Function {name} has not been defined",
                )


if __name__ == "__main__":
    program = """
    func main() {
    print(true + false);
    }
    """

    interpreter = Interpreter()
    interpreter.run(program)
