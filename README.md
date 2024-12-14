# CS 131 Fall 2024: Brewin

Hey there! This repository contains the quarter-long project for [CS 131](https://ucla-cs-131.github.io/fall-24-website/): an interpreter.

Other than the main files defined in the projects' description below, the other files are necessary bootstrapping code written by Carey Nachenberg and the Fall 2024 TA team:

- `ply/lex.py`, `ply/yacc.py`, `brewlex.py`, `brewparse.py`, responsible for taking in a string representing a Brewin program and outputting an AST (parser logic)
- `elements.py`, defines the return type of the parser
- `intbase.py`, the base class and enum definitions for the interpreter

## Project 1

### Overview

- [Project 1 Spec](https://docs.google.com/document/d/1npomXM55cXg9Af7BUXEj3_bFpj1sy2Jty2Nwi6Kp64E/edit?usp=sharing)
- File: `interpreterv1.py`
- Setting up the basis

### Features

- Statements
- Expressions
- Variables
- Values

### Example

```
func main() {  /* a function that computes the sum of two numbers */
  var first;
  var second;
  first = inputi("Enter a first #: ");
  second = inputi("Enter a second #: ");
  var sum;
  sum = (first + second);   
  print("The sum is ", sum, "!");
}
```

## Project 2

### Overview

- [Project 2 Spec](https://docs.google.com/document/d/1M4e3mkNhUKC0d7dJZSetbR4M3ceq8y8BiGDJ4fMAK6I/edit?usp=sharing)
- Files: `interpreterv2.py`, `env_v2.py`, `type_valuev2.py`

### Features

- Functions
- If statements
- For statements
- Return statements
- More expressions (mostly comparisons)
- Scoping

### Examples

```
func main() {
  print(fact(5));
}

func fact(n) {
  if (n <= 1) { return 1; }
  return n * fact(n-1);
}
```

```
func main() {
 var i;
 for (i = 3; i > 0; i = i - 1) {
  print(i);
 }
}
```

## Project 3

### Overview

- [Project 3 Spec](https://docs.google.com/document/d/1seLyYfAJs9xj_XgE8mB23KHuAGQOCnfYmRAwW4P8u1k/edit?usp=sharing)
- Files: `interpreterv3.py`, `env_v3.py`, `type_valuev3.py`
- Builds off of Project 2

### Features

- Static typing
- Default return values
- Coercion
- Structures

### Examples

```
func main() : void {
  var n : int;
  n = inputi("Enter a number: ");
  print(fact(n));
}

func fact(n : int) : int {
  if (n <= 1) { return 1; }
  return n * fact(n-1);
}
```

```
func main() : void {
  print(foo());
  print(bar());
}

func foo() : int {
  return; /* returns 0 */
}

func bar() : bool {
  print("bar");
}  /* returns false*/
```

```
func main() : void {
  print(5 || false);
  var a:int;
  a = 1;
  if (a) {
    print("if works on integers now!");
  }
  foo(a-1);
}

func foo(b : bool) : void {
  print(b);
}
```

```
struct Person {
  name: string;
  age: int;
  student: bool;
}

func main() : void {
  var p: Person;
  p = new Person;
  p.name = "Carey";
  p.age = 21;
  p.student = false;
  foo(p);
}

func foo(p : Person) : void {
  print(p.name, " is ", p.age, " years old.");
}
```

## Project 4

### Overview

- [Project 4 Spec](https://docs.google.com/document/d/1vUSQwrq8ePh-pmc2hia8GmapXXOSEEpu7xw2tgTbgII/edit?usp=sharing)
- Files: `interpreterv4.py`, `env_v4.py`, `type_valuev4.py`
- Builds off of Project 2

### Features

- Need semantics and lazy evaluation
- Exception handling
- Short circuiting

### Examples

```
func main() {
  var result;
  result = f(3) + 10;
  print("done with call!");
  print(result);  /* evaluation of result happens here */
  print("about to print result again");
  print(result);
}

func f(x) {
  print("f is running");
  var y;
  y = 2 * x;
  return y;
}
```

```
func foo() {
  print("F1");
  raise "except1";
  print("F3");
}

func bar() {
 try {
   print("B1");
   foo();
   print("B2");
 }
 catch "except2" {
   print("B3");
 }
 print("B4");
}

func main() {
 try {
   print("M1");
   bar();
   print("M2");
 }
 catch "except1" {
   print("M3");
 }
 catch "except3" {
   print("M4");
 }
 print("M5");
}
```

```
func foo() {
 print("foo");
 return true;
}

func bar() {
 print("bar");
 return false;
}

func main() {
  print(foo() || bar() || foo() || bar());
  print("done");
}
```