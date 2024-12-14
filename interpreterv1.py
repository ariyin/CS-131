from intbase import InterpreterBase, ErrorType
from brewparse import parse_program


class Interpreter(InterpreterBase):
    def __init__(self, console_output=True, inp=None, trace_output=False):
        # call InterpreterBase's constructor
        super().__init__(console_output, inp)

    def run(self, program):
        ast = parse_program(program)
        self.variables = {}  # variable name : value
        main_func_node = ast.dict["functions"][0]
        if main_func_node.dict["name"] != "main":
            super().error(
                ErrorType.NAME_ERROR,
                "No main() function was found",
            )
        self.run_function(main_func_node)

    def run_function(self, func_node):
        for statement_node in func_node.dict["statements"]:
            self.run_statement(statement_node)

    def run_statement(self, statement_node):
        # variable definition
        if statement_node.elem_type == "vardef":
            name = statement_node.dict["name"]
            if name in self.variables:
                super().error(
                    ErrorType.NAME_ERROR,
                    f"Variable {name} defined more than once",
                )
            self.variables[name] = 0
        elif statement_node.elem_type == "=":
            # maps to either an expression node, variable node, or value node
            name = statement_node.dict["name"]
            node = statement_node.dict["expression"]
            if name not in self.variables:
                super().error(
                    ErrorType.NAME_ERROR,
                    f"Undefined variable {name}",
                )
            self.variables[name] = self.evaluate_expression(node)
        # function call
        elif statement_node.elem_type == "fcall":
            self.run_function_call(statement_node)

    def evaluate_expression(self, expression_node):
        # value node
        if expression_node.elem_type == "int" or expression_node.elem_type == "string":
            return expression_node.dict["val"]
        # variable node
        elif expression_node.elem_type == "var":
            var_name = expression_node.dict["name"]
            if var_name not in self.variables:
                super().error(
                    ErrorType.NAME_ERROR,
                    f"Variable {var_name} has not been defined",
                )
            return self.variables[var_name]
        # binary operation
        elif expression_node.elem_type == "+":
            op1, op2 = self.check_operation(expression_node)
            return self.evaluate_expression(op1) + self.evaluate_expression(op2)
        elif expression_node.elem_type == "-":
            op1, op2 = self.check_operation(expression_node)
            return self.evaluate_expression(op1) - self.evaluate_expression(op2)
        # function call
        elif expression_node.elem_type == "fcall":
            return self.run_function_call(expression_node)

    def evaluate_value(self, expression_node):
        # value node
        if expression_node.elem_type == "int" or expression_node.elem_type == "string":
            return expression_node.dict["val"]
        # variable node
        elif expression_node.elem_type == "var":
            var_name = expression_node.dict["name"]
            if var_name not in self.variables:
                super().error(
                    ErrorType.NAME_ERROR,
                    f"Variable {var_name} has not been defined",
                )
            return self.variables[var_name]

    def run_function_call(self, function_call):
        func_name = function_call.dict["name"]
        if func_name == "print":
            res = ""
            for arg in function_call.dict["args"]:
                res += str(self.evaluate_expression(arg))
            super().output(res)
        elif func_name == "inputi":
            if len(function_call.dict["args"]) > 1:
                super().error(
                    ErrorType.NAME_ERROR,
                    "No inputi() function found that takes > 1 parameter",
                )
            elif len(function_call.dict["args"]) == 1:
                super().output(function_call.dict["args"][0].dict["val"])

            return int(super().get_input())
        else:
            super().error(
                ErrorType.NAME_ERROR,
                f"Function {func_name} has not been defined",
            )

    def check_operation(self, expression_node):
        op1 = expression_node.dict["op1"]
        op2 = expression_node.dict["op2"]

        if (
            isinstance(self.evaluate_value(op1), int)
            and isinstance(self.evaluate_value(op2), str)
        ) or (
            isinstance(self.evaluate_value(op1), str)
            and isinstance(self.evaluate_value(op2), int)
        ):
            super().error(
                ErrorType.TYPE_ERROR,
                "Incompatible types for arithmetic operation",
            )

        return op1, op2


if __name__ == "__main__":
    # program = """func main() {
    # var x;
    # x = 4 + inputi("enter a number: ");
    # print(x);
    # }
    # """

    program = """func main() {
    var x;
    x = 3 - (3 + (2 + inputi()));
    print(x);
    }
    """

    # program = """func main() {
    # var x;
    # x = inputi("enter a number: ");
    # print(x);
    # }"""

    interpreter = Interpreter()
    interpreter.run(program)
