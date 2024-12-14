# enumerated type for our different language data types
class Type:
    INT = "int"
    BOOL = "bool"
    STRING = "string"
    NIL = "nil"
    VOID = "void"


# represents a value, which has a type and its value
class Value:
    def __init__(self, type, value=None):
        self.t = type
        self.v = value

    def value(self):
        return self.v

    def type(self):
        return self.t

    def set(self, type, value):
        self.t = type
        self.v = value


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
    if val.type() == Type.VOID:
        return "void"
    return "nil"
