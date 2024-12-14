# the EnvironmentManager class keeps a mapping between each variable (aka symbol) in a
# brewin program and the value of that variable - the value that's passed in can be anything you like
# in our implementation we pass in a Value object which holds a type and a value


class EnvironmentManager:
    def __init__(self):
        # stack of environments, where each environment is a dictionary
        # the bottom-most dictionary is the global scope
        self.scopes = [{"type": "function", "variables": {}}]

    # looks for a symbol starting from the current (top-most) scope down to the global scope
    def get(self, symbol):
        for scope in reversed(self.scopes):
            # if you find the variable
            # and you're not in a function looking at a different function's scope
            if symbol in scope["variables"] and not (
                scope["type"] == "function"
                and scope != self.scopes[-1]
                and self.scopes[-1]["type"] == "function"
            ):
                return scope["variables"][symbol]
        return None

    # search all scopes to find where the symbol is defined and update it there
    def set(self, symbol, value):
        for scope in reversed(self.scopes):
            # TODO: may need to update this with the same logic as get
            # but this works for now
            if symbol in scope["variables"]:
                scope["variables"][symbol] = value
                return True
        return False

    # adds a new symbol to the current (top-most) scope, initializing it with `start_val`
    def create(self, symbol, start_val):
        if symbol not in self.scopes[-1]["variables"]:
            self.scopes[-1]["variables"][symbol] = start_val
            return True
        return False

    def copy(self):
        copied_manager = EnvironmentManager()

        copied_manager.scopes = []
        for scope in self.scopes:
            variables = {}
            for name, variable in scope["variables"].items():
                variables[name] = variable

            copied_scope = {
                "type": scope["type"],
                "variables": variables,
            }
            copied_manager.scopes.append(copied_scope)

        return copied_manager

    # enters a new scope by adding a new dictionary to the scopes stack
    def push_scope(self, type):
        self.scopes.append({"type": type, "variables": {}, "evaluated": {}})

    # exits the current scope by removing the top-most dictionary from the stack
    def pop_scope(self):
        if len(self.scopes) > 1:
            self.scopes.pop()
        else:
            raise Exception("Cannot pop global scope")

    # prints all scopes for debugging purposes
    def print(self):
        for i, scope in enumerate(reversed(self.scopes)):
            print(f"Scope {len(self.scopes) - i - 1}")
            for key, value in scope["variables"].items():
                type = scope["type"]
                print(
                    f"Scope {len(self.scopes) - i - 1} | {type} | {key}: {value.print()}"
                )
        print()
