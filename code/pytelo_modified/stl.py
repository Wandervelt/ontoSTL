'''
 Copyright (C) 2015-2020 Cristian Ioan Vasile <cvasile@lehigh.edu>
 Hybrid and Networked Systems (HyNeSs) Group, BU Robotics Lab, Boston University
 Explainable Robotics Lab, Lehigh University
 See license.txt file for license information.
'''

import itertools as it

import numpy as np
from scipy.interpolate import interp1d
from antlr4 import InputStream, CommonTokenStream

from .stlLexer import stlLexer
from .stlParser import stlParser
from .stlVisitor import stlVisitor


class Operation(object):
    '''STL operations'''
    NOP, NOT, OR, AND, IMPLIES, UNTIL, EVENT, ALWAYS, PRED, BOOL, VAR = range(11)
    opnames = [None, '!', '||', '&&', '=>', 'U', 'F', 'G', 'predicate', 'bool', 'variable']
    opcodes = {'!': NOT, '&&': AND, '||' : OR, '=>': IMPLIES,
               'U': UNTIL, 'F': EVENT, 'G': ALWAYS}
    opstrnames = [None, 'not', 'or', 'and', 'imply', 'until', 'event', 'always',
                  'predicate', 'bool', 'variable']
    # negation closure of operations
    negop = (NOP, NOP, AND, OR, AND, NOP, ALWAYS, EVENT, PRED, BOOL, VAR)

    @classmethod
    def getCode(cls, text):
        ''' Gets the code corresponding to the string representation.'''
        return cls.opcodes.get(text, cls.NOP)

    @classmethod
    def getString(cls, op):
        '''Gets custom string representation for each operation.'''
        return cls.opnames[op]

    @classmethod
    def getName(cls, op):
        '''Gets custom long string name for each operation.'''
        return cls.opstrnames[op]


class RelOperation(object):
    '''Predicate relationship operations'''
    NOP, LT, LE, GT, GE, EQ, NQ = range(7)
    opnames = [None, '<', '<=', '>', '>=', '=', '!=']
    opcodes = {'<': LT, '<=': LE, '>' : GT, '>=': GE, '=': EQ, '!=': NQ}
    # negation closure of operations
    negop = (NOP, GE, GT, LE, LT, NQ, EQ)
    invop = (NOP, GT, GE, LT, LE, EQ, NQ)

    @classmethod
    def getCode(cls, text):
        ''' Gets the code corresponding to the string representation.'''
        return cls.opcodes.get(text, cls.NOP)

    @classmethod
    def getString(cls, rop):
        '''Gets custom string representation for each operation.'''
        return cls.opnames[rop]


class STLFormula(object):
    '''Abstract Syntax Tree representation of an STL formula'''

    def __init__(self, operation, **kwargs):
        '''Constructor'''
        self.op = operation

        if self.op == Operation.BOOL:
            self.value = kwargs['value']
        elif self.op == Operation.VAR:
            self.variable = kwargs['variable']
        elif self.op == Operation.PRED:
            self.relation = kwargs['relation']
            self.variable = kwargs['variable']
            self.threshold = kwargs['threshold']
        elif self.op in (Operation.AND, Operation.OR):
            self.children = kwargs['children']
        elif self.op == Operation.IMPLIES:
            self.left = kwargs['left']
            self.right = kwargs['right']
        elif self.op == Operation.NOT:
            self.child = kwargs['child']
        elif self.op in(Operation.ALWAYS, Operation.EVENT):
            self.low = kwargs['low']
            self.high = kwargs['high']
            self.child = kwargs['child']
        elif self.op == Operation.UNTIL:
            self.low = kwargs['low']
            self.high = kwargs['high']
            self.left = kwargs['left']
            self.right = kwargs['right']

        self.__string = None
        self.__hash = None

    def robustness(self, s, t, max_robustness=1):
        '''Computes the robustness of the STL formula.'''
        no_signals = s.number_signals()
        if self.op == Operation.BOOL:
            ret = np.array([max_robustness] * no_signals)
            if self.value:
                return ret
            else:
                return -ret
        elif self.op == Operation.VAR:
             return s.value(self.variable, t)
        elif self.op == Operation.PRED:
            value = s.value(self.variable, t)
            if self.relation in (RelOperation.GE, RelOperation.GT):
                return  value - self.threshold
            elif self.relation in (RelOperation.LE, RelOperation.LT):
                return self.threshold - value
            elif self.relation == RelOperation.EQ:
                return -np.abs(value - self.threshold)
            elif self.relation == RelOperation.NQ:
                return np.abs(value - self.threshold)
        elif self.op == Operation.AND:
            res = np.array([child.robustness(s, t, max_robustness)
                                        for child in self.children])
            return np.amin(res, axis=0)
        elif self.op == Operation.OR:
            res = np.array([child.robustness(s, t, max_robustness)
                                        for child in self.children])
            return np.amax(res, axis=0)
        elif self.op == Operation.IMPLIES:
            return np.maximum(-self.left.robustness(s, t, max_robustness),
                              self.right.robustness(s, t, max_robustness))
        elif self.op == Operation.NOT:
            return -self.child.robustness(s, t, max_robustness)
        elif self.op == Operation.UNTIL:
            res = np.array([self.left.robustness(s, t+tau, max_robustness)
                                              for tau in np.arange(self.low+1)])
            r_acc = np.amin(res, axis = 0)
            rleft = (self.left.robustness(s, t+tau, max_robustness)
                                    for tau in np.arange(self.low, self.high+1))
            rright = (self.right.robustness(s, t+tau, max_robustness)
                                    for tau in np.arange(self.low, self.high+1))
            value = -np.array([max_robustness] * no_signals)
            for rl, rr in zip(rleft, rright):
                r_acc = np.minimum(r_acc, rl)
                r_conj = np.minimum(r_acc, rr)
                value = np.maximum(value, r_conj)
            return value
        elif self.op == Operation.ALWAYS:
            res = np.array([self.child.robustness(s, t+tau, max_robustness)
                                for tau in np.arange(self.low, self.high+1)])
            return np.amin(res, axis=0)
        elif self.op == Operation.EVENT:
            res = np.array([self.child.robustness(s, t+tau, max_robustness)
                                for tau in np.arange(self.low, self.high+1)])
            return np.amax(res, axis=0)

    def negate(self):
        '''Computes the negation of the STL formula by propagating the negation
        towards predicates.
        '''
        self.__string = None
        if self.op == Operation.BOOL:
            self.value = not self.value
        elif self.op == Operation.VAR:
            return STLFormula(Operation.NOT, child=self)
        elif self.op == Operation.PRED:
            self.relation = RelOperation.negop[self.relation]
        elif self.op in (Operation.AND, Operation.OR):
            [child.negate() for child in self.children]
        elif self.op == Operation.IMPLIES:
            self.right = self.right.negate()
        elif self.op == Operation.NOT:
            return self.child
        elif self.op == Operation.UNTIL:
            raise NotImplementedError
        elif self.op in (Operation.ALWAYS, Operation.EVENT):
            self.child = self.child.negate()
        self.op = Operation.negop[self.op]
        return self

    def pnf(self, insert_inverse_variables=False):
        '''Computes the Positive Normal Form of the STL formula.'''
        self.__string = None
        flag = insert_inverse_variables
        if self.op in (Operation.VAR, Operation.BOOL, Operation.PRED):
             return self
        elif self.op in (Operation.AND, Operation.OR):
            self.children = [child.pnf(flag) for child in self.children]
        elif self.op == Operation.IMPLIES:
            self.left = self.left.negate().pnf(flag)
            self.right = self.right.pnf(flag)
            self.op = Operation.OR
        elif self.op == Operation.NOT:
            return self.child.negate().pnf(flag)
        elif self.op == Operation.UNTIL:
            self.left = self.left.pnf(flag)
            self.right = self.right.pnf(flag)
        elif self.op in (Operation.ALWAYS, Operation.EVENT):
            self.child = self.child.pnf(flag)
        return self


    def bound(self):
        '''Computes the bound of the STL formula.'''
        if self.op in (Operation.BOOL, Operation.PRED, Operation.VAR):
            return 0
        elif self.op in (Operation.AND, Operation.OR):
            return max([ch.bound() for ch in self.children])
        elif self.op == Operation.IMPLIES:
            return max(self.left.bound(), self.right.bound())
        elif self.op == Operation.NOT:
            return self.child.bound()
        elif self.op == Operation.UNTIL:
            return self.high + max(self.left.bound(), self.right.bound())
        elif self.op in (Operation.ALWAYS, Operation.EVENT):
            return self.high + self.child.bound()

    def variables(self):
        '''Computes the set of variables involved in the STL formula.'''
        if self.op == Operation.BOOL:
            return set()
        elif self.op in (Operation.PRED, Operation.VAR):
            return {self.variable}
        elif self.op in (Operation.AND, Operation.OR):
            return set.union(*[child.variables() for child in self.children])
        elif self.op in (Operation.IMPLIES, Operation.UNTIL):
            return self.left.variables() | self.right.variables()
        elif self.op in (Operation.NOT, Operation.ALWAYS, Operation.EVENT):
            return self.child.variables()

    def identifier(self):
        h = hash(self)
        if h < 0:
            h = hex(ord('-'))[2:] + hex(-h)[1:]
        else:
            h = hex(ord('+'))[2:] + hex(h)[1:]
        return h

    def __hash__(self):
        """
        Provides a canonical, content-based hash for the formula.
        This is required to put formula objects into a set for uniqueness.
        """
        if self.op in (Operation.AND, Operation.OR):
            # For AND/OR, the hash is order-independent
            children_hashes = frozenset(hash(c) for c in self.children)
            return hash((self.op, children_hashes))

        # For other operators, the hash depends on their specific content
        if self.op == Operation.BOOL:
            return hash((self.op, self.value))
        elif self.op == Operation.VAR:
            return hash((self.op, self.variable))
        elif self.op == Operation.PRED:
            return hash((self.op, self.relation, self.variable, self.threshold))
        elif self.op in (Operation.ALWAYS, Operation.EVENT):
            return hash((self.op, self.low, self.high, hash(self.child)))
        elif self.op == Operation.NOT:
            return hash((self.op, hash(self.child)))
        elif self.op == Operation.IMPLIES:
            return hash((self.op, hash(self.left), hash(self.right)))
        elif self.op == Operation.UNTIL:
            return hash((self.op, self.low, self.high, hash(self.left), hash(self.right)))
        
        # Fallback for any other case
        return hash(str(self))


    def __lt__(self, other):
            """
            Defines a consistent, deterministic "less than" ordering for sorting nodes.
            """
            if not isinstance(other, STLFormula):
                return NotImplemented
            
            if self.op != other.op:
                return self.op < other.op
                
            return str(self) < str(other)

    def __eq__(self, other):
        return str(self) == str(other)

    def __ne__(self, other):
        return not self.__eq__(other)

    def __str__(self):
        if self.__string is not None:
            return self.__string

        opname = Operation.getString(self.op)
        if self.op == Operation.BOOL:
            s = '{value}'.format(value=self.value)
        elif self.op == Operation.VAR:
            s = self.variable
        elif self.op == Operation.PRED:
            s = '({v} {rel} {th})'.format(v=self.variable, th=self.threshold,
                                    rel=RelOperation.getString(self.relation))
        elif self.op == Operation.IMPLIES:
            s = '{left} {op} {right}'.format(left=self.left, op=opname,
                                             right=self.right)
        elif self.op in (Operation.AND, Operation.OR):
            children = [str(child) for child in self.children]
            s = '(' + ' {op} '.format(op=opname).join(children) + ')'
        elif self.op == Operation.NOT:
            s = '{op} {child}'.format(op=opname, child=self.child)
        elif self.op == Operation.UNTIL:
            s = '({left} {op}[{low}, {high}] {right})'.format(op=opname,
                 left=self.left, right=self.right, low=self.low, high=self.high)
        elif self.op in (Operation.ALWAYS, Operation.EVENT):
            s = '({op}[{low}, {high}] {child})'.format(op=opname,
                                 low=self.low, high=self.high, child=self.child)
        self.__string = s
        return self.__string


class STLAbstractSyntaxTreeExtractor(stlVisitor):
    '''Parse Tree visitor that constructs the AST of an STL formula'''

    @staticmethod
    def _extract_time_bounds(ctx, default_low=0.0, default_high=float('inf')):
        """Extract [low, high] bounds from temporal operator contexts.

        If bounds are omitted in the input, default to [0, inf].
        """
        if ctx.low is None or ctx.high is None:
            return default_low, default_high

        low_text = ctx.low.getText().lower()
        high_text = ctx.high.getText().lower()
        low = float('inf') if low_text == 'inf' else float(low_text)
        high = float('inf') if high_text == 'inf' else float(high_text)
        return low, high

    def visitFormula(self, ctx):
        op = Operation.getCode(ctx.op.text)
        ret = None
        if op in (Operation.AND, Operation.OR):
            left = self.visit(ctx.left)
            right = self.visit(ctx.right)
            
            children = []
            
            # Correctly flatten the left child
            if left.op == op:
                children.extend(left.children)
            else:
                children.append(left)
                
            # Correctly flatten the right child
            if right.op == op:
                children.extend(right.children)
            else:
                children.append(right)
                
            ret = STLFormula(op, children=children)


        elif op == Operation.IMPLIES:
            ret = STLFormula(op, left=self.visit(ctx.left),
                             right=self.visit(ctx.right))
        elif op == Operation.NOT:
            ret = STLFormula(op, child=self.visit(ctx.child))
        elif op == Operation.UNTIL:
            low, high = self._extract_time_bounds(ctx)
            
            ret = STLFormula(op, left=self.visit(ctx.left),
                             right=self.visit(ctx.right), low=low, high=high)
        elif op in (Operation.ALWAYS, Operation.EVENT):
            low, high = self._extract_time_bounds(ctx)

            ret = STLFormula(op, child=self.visit(ctx.child),
                             low=low, high=high)
        else:
            print('Error: unknown operation!')
        return ret

    def visitBooleanPred(self, ctx):
        return self.visit(ctx.getChild(0))

    def visitBooleanExpr(self, ctx):
        # Case 1: A standalone atomic proposition like 'p1'
        if hasattr(ctx, 'variable') and ctx.variable:
            return STLFormula(Operation.VAR, variable=ctx.variable.text)
        
        # Case 2: A boolean constant 'true' or 'false'
        elif hasattr(ctx, 'op') and ctx.op.type == stlParser.BOOLEAN:
            value = ctx.op.text.lower() == 'true'
            return STLFormula(Operation.BOOL, value=value)
        
        # Case 3: A full comparison predicate
        else:
            right_text = ctx.right.getText()
            try:
                threshold_value = float(right_text)
            except ValueError:
                print(f"\n--- PARSING ERROR ---")
                print(f"Comparison with a non-numeric value ('{right_text}') is not supported.")
                print("The right-hand side of a comparison must be a number.")
                return None
            
            return STLFormula(Operation.PRED,
                relation=RelOperation.getCode(ctx.op.text),
                variable=ctx.left.getText(), 
                threshold=threshold_value)
        

    def visitParprop(self, ctx):
        return self.visit(ctx.child)


class Trace(object):
    '''Representation of a system trace.'''

    def __init__(self, variables, timePoints, data, kind='nearest'):
        '''Constructor'''
        self.data = {variable : interp1d(timePoints, var_data, kind=kind)
                            for variable, var_data in zip(variables, data)}

    def value(self, variable, t):
        '''Returns value of the given signal component at time t.'''
        return self.data[variable](t)

    def values(self, variable, timepoints):
        '''Returns value of the given signal component at desired timepoint.'''
        return self.data[variable](np.asarray(timepoints))

    def number_signals(self):
        return 1

    def __str__(self):
        raise NotImplementedError


class TraceBatch(object):
    '''Representation of a system trace.'''

    def __init__(self, variables, timePoints, data, kind='nearest'):
        '''Constructor

        variables (iterable of strings)
        timepoints (iterable of common time points)
        data (iterable of multi-dimensional signals)
        kind (type of interpolation)
        '''
        self.no_signals = len(data)
        self.data = dict()
        for k, variable in enumerate(variables):
            var_data = np.array([d[k] for d in data])
            self.data[variable] = interp1d(timePoints, var_data, kind=kind)

    def value(self, variable, t):
        '''Returns value of the given signal component at time t.'''
        return self.data[variable](t)

    def values(self, variable, timepoints):
        '''Returns value of the given signal component at desired timepoint.'''
        return self.data[variable](np.asarray(timepoints))

    def number_signals(self):
        return self.no_signals

    def __str__(self):
        raise NotImplementedError

def to_ast(formula):
    '''Transforms a formula string to an Abstract Syntax Tree.'''
    lexer = stlLexer(InputStream(formula))
    tokens = CommonTokenStream(lexer)
    parser = stlParser(tokens)
    t = parser.stlProperty()
    ast = STLAbstractSyntaxTreeExtractor().visit(t)
    return ast

if __name__ == '__main__':
    
    formula = ("!(x > 10) && F[0, 2] y > 2 && G[1, 3] z<=8")

    ast = to_ast(formula)
    print('AST:', str(ast))

    varnames = ['x', 'y', 'z']
    data = [[8, 8, 11, 11, 11], [2, 3, 1, 2, 2], [3, 9, 8, 9, 9]]
    timepoints = [0, 1, 2, 3, 4]
    s = Trace(varnames, timepoints, data)

    print('r:', ast.robustness(s, 0, 20))

    varnames = ['x', 'y', 'z']
    data = [[[8, 8, 11, 11, 11], [2, 3, 1, 2, 2], [3, 9, 8, 9, 9]],
            [[10, 9, 11, 11, 11], [2, 3, 1, 2, 2], [3, 9, 8, 9, 9]],
            [[8, 8, 11, 11, 11], [2, 3, 1, 2, 2], [3, 5, 8, 7, 9]]
           ]
    timepoints = [0, 1, 2, 3, 4]
    s = TraceBatch(varnames, timepoints, data)

    print('r batch:', ast.robustness(s, 0, 20))

    pnf = ast.pnf()
    print(pnf)
