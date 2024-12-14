# enumerated type for our different language data types
class Type:
    INT = "int"
    BOOL = "bool"
    STRING = "string"
    NIL = "nil"


# represents a value, which has a type and its value
class Value:
    def __init__(self, type, value=None):
        self.t = type
        self.v = value

    def value(self):
        return self.v

    def type(self):
        return self.t

    def print(self):
        return f"{self.v}"


class LazyValue:
    def __init__(self, ast, env):
        self.eval = False
        self.v = None  # Value
        self.a = ast
        self.e = env

    def evaluated(self):
        return self.eval

    def set_eval(self):
        self.eval = True

    def value(self):
        return self.v

    def set_value(self, value):
        self.v = value

    def ast(self):
        return self.a

    def env(self):
        return self.e

    def print(self):
        value = None
        type = None
        if self.v:
            value = self.v.value()
            type = self.v.type()

        return f"eval: {self.eval} | value: {value} | type: {type} | ast: {self.a} | env: {self.e.print()}"


# creates a value based on the given value
def create_value(val):
    if val is True:
        return Value(Type.BOOL, True)
    if val is False:
        return Value(Type.BOOL, False)
    elif isinstance(val, str):
        return Value(Type.STRING, val)
    elif isinstance(val, int):
        return Value(Type.INT, val)
    else:
        raise ValueError("Unknown value type")


# outputs the printable version of the value
def get_printable(val):
    if val.type() == Type.INT:
        return str(val.value())
    if val.type() == Type.STRING:
        return val.value()
    if val.type() == Type.BOOL:
        if val.value() is True:
            return "true"
        return "false"
    return None
