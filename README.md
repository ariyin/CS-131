# CS 131 Fall 2024: Project Starter

Hey there! This is a template repository that contains the necessary boilerplate for [CS 131](https://ucla-cs-131.github.io/fall-24-website/)'s quarter-long project: making an interpreter. The project specs are as follows:

1. [Project 1 Spec](https://docs.google.com/document/d/1npomXM55cXg9Af7BUXEj3_bFpj1sy2Jty2Nwi6Kp64E/edit?usp=sharing)

There are four stages to the project; students are currently at the first. Thus, this folder contains the necessary bootstrapping code:

- `ply/lex.py`, `ply/yacc.py`, `brewlex.py`, `brewparse.py`, responsible for taking in a string representing a Brewin program and outputting an AST (parser logic)
- `elements.py`, defines the return type of the parser
- `intbase.py`, the base class and enum definitions for the interpreter

Some notes on your submission (for Project 1)

1. You **must have a top-level, versioned `interpreterv1.py` file** that **exports the `Interpreter` class**. If not, **your code will not run on our autograder**.
2. You may also submit one or more additional `.py` modules that your interpreter uses, if you decide to break up your solution into multiple `.py` files.
3. You **should not modify/submit** ***any*** of the source files that are present in this base template, which includes:
* `ply/lex.py`
* `ply/yacc.py`
* `brewlex.py`
* `brewparse.py`
* `element.py`
* `intbase.py`

You can find out more about our autograder, including how to run it, in [the accompanying repo](https://github.com/UCLA-CS-131/fall-24-autograder)

## Licensing and Attribution

This is an unlicensed repository; even though the source code is public, it is **not** governed by an open-source license.

This code was primarily written by [Carey Nachenberg](http://careynachenberg.weebly.com/), with support from his TAs for the [Fall 2024 iteration of CS 131](https://ucla-cs-131.github.io/fall-24-website/).
