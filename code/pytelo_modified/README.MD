This code is derived from the Explainable Robotics Lab (ERL) project:
https://github.com/erl-lehigh/PyTeLo

The original file(s) are included under the BSD 3-Clause License (see LICENSE in this folder).
Copyright (c) 2023, Explainable Robotics Lab (ERL). The original code has been modified as follows:

1- Changes to the stl.g4 grammar to include atomic variables (e.g., p) as valid formulas, in addition to predicates (e.g., x > 5).
2- Updates to the parser to handle infinite temporal intervals (e.g., G[0, inf] p).
3- Changed parser logic to flatten nested associative operators (e.g., a && (b && c) is treated the same as (a && b) && c).
4- Implementation of a hashing method for STLFormula objects that is independent of operand order for commutative operators.
5- Addition of a __lt__ method to STLFormula for deterministic sorting of formulas.
6- Simplification of the Positive Normal Form (pnf) transformation logic.
