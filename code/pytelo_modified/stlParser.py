# Generated from stl.g4 by ANTLR 4.13.0
# encoding: utf-8
from antlr4 import *
from io import StringIO
import sys
if sys.version_info[1] > 5:
	from typing import TextIO
else:
	from typing.io import TextIO


'''
 Copyright (C) 2015-2020 Cristian Ioan Vasile <cvasile@lehigh.edu>
 Hybrid and Networked Systems (HyNeSs) Group, BU Robotics Lab, Boston University
 Explainable Robotics Lab, Lehigh University
 See license.txt file for license information.
'''

def serializedATN():
    return [
        4,1,28,96,2,0,7,0,2,1,7,1,2,2,7,2,2,3,7,3,1,0,1,0,1,0,1,0,1,0,1,
        0,1,0,1,0,1,0,1,0,1,0,1,0,1,0,1,0,1,0,1,0,1,0,1,0,1,0,1,0,1,0,1,
        0,1,0,1,0,3,0,33,8,0,1,0,1,0,1,0,1,0,1,0,1,0,1,0,1,0,1,0,1,0,1,0,
        1,0,1,0,1,0,1,0,1,0,1,0,1,0,5,0,53,8,0,10,0,12,0,56,9,0,1,1,1,1,
        1,2,1,2,1,2,1,2,1,2,1,2,1,2,1,2,1,2,1,2,1,2,1,2,3,2,72,8,2,1,2,1,
        2,1,2,1,2,1,2,1,2,1,2,1,2,1,2,5,2,83,8,2,10,2,12,2,86,9,2,1,3,1,
        3,1,3,1,3,1,3,1,3,3,3,94,8,3,1,3,0,2,0,4,4,0,2,4,6,0,5,2,0,25,25,
        27,27,2,0,1,1,6,6,1,0,8,9,1,0,10,11,1,0,12,16,107,0,32,1,0,0,0,2,
        57,1,0,0,0,4,71,1,0,0,0,6,93,1,0,0,0,8,9,6,0,-1,0,9,10,5,1,0,0,10,
        11,3,0,0,0,11,12,5,2,0,0,12,33,1,0,0,0,13,33,3,6,3,0,14,15,5,20,
        0,0,15,33,3,0,0,7,16,17,5,21,0,0,17,18,5,3,0,0,18,19,3,2,1,0,19,
        20,5,4,0,0,20,21,3,2,1,0,21,22,5,5,0,0,22,23,3,0,0,6,23,33,1,0,0,
        0,24,25,5,22,0,0,25,26,5,3,0,0,26,27,3,2,1,0,27,28,5,4,0,0,28,29,
        3,2,1,0,29,30,5,5,0,0,30,31,3,0,0,5,31,33,1,0,0,0,32,8,1,0,0,0,32,
        13,1,0,0,0,32,14,1,0,0,0,32,16,1,0,0,0,32,24,1,0,0,0,33,54,1,0,0,
        0,34,35,10,4,0,0,35,36,5,19,0,0,36,53,3,0,0,5,37,38,10,3,0,0,38,
        39,5,17,0,0,39,53,3,0,0,4,40,41,10,2,0,0,41,42,5,18,0,0,42,53,3,
        0,0,3,43,44,10,1,0,0,44,45,5,23,0,0,45,46,5,3,0,0,46,47,3,2,1,0,
        47,48,5,4,0,0,48,49,3,2,1,0,49,50,5,5,0,0,50,51,3,0,0,2,51,53,1,
        0,0,0,52,34,1,0,0,0,52,37,1,0,0,0,52,40,1,0,0,0,52,43,1,0,0,0,53,
        56,1,0,0,0,54,52,1,0,0,0,54,55,1,0,0,0,55,1,1,0,0,0,56,54,1,0,0,
        0,57,58,7,0,0,0,58,3,1,0,0,0,59,60,6,2,-1,0,60,61,7,1,0,0,61,62,
        3,4,2,0,62,63,5,2,0,0,63,72,1,0,0,0,64,65,5,26,0,0,65,66,5,1,0,0,
        66,67,3,4,2,0,67,68,5,2,0,0,68,72,1,0,0,0,69,72,5,27,0,0,70,72,5,
        26,0,0,71,59,1,0,0,0,71,64,1,0,0,0,71,69,1,0,0,0,71,70,1,0,0,0,72,
        84,1,0,0,0,73,74,10,6,0,0,74,75,5,7,0,0,75,83,3,4,2,6,76,77,10,4,
        0,0,77,78,7,2,0,0,78,83,3,4,2,5,79,80,10,3,0,0,80,81,7,3,0,0,81,
        83,3,4,2,4,82,73,1,0,0,0,82,76,1,0,0,0,82,79,1,0,0,0,83,86,1,0,0,
        0,84,82,1,0,0,0,84,85,1,0,0,0,85,5,1,0,0,0,86,84,1,0,0,0,87,88,3,
        4,2,0,88,89,7,4,0,0,89,90,3,4,2,0,90,94,1,0,0,0,91,94,5,24,0,0,92,
        94,5,26,0,0,93,87,1,0,0,0,93,91,1,0,0,0,93,92,1,0,0,0,94,7,1,0,0,
        0,7,32,52,54,71,82,84,93
    ]

class stlParser ( Parser ):

    grammarFileName = "stl.g4"

    atn = ATNDeserializer().deserialize(serializedATN())

    decisionsToDFA = [ DFA(ds, i) for i, ds in enumerate(atn.decisionToState) ]

    sharedContextCache = PredictionContextCache()

    literalNames = [ "<INVALID>", "'('", "')'", "'['", "','", "']'", "'-('", 
                     "'^'", "'*'", "'/'", "'+'", "'-'", "'<'", "'<='", "'='", 
                     "'>='", "'>'", "<INVALID>", "<INVALID>", "'=>'", "<INVALID>", 
                     "<INVALID>", "<INVALID>", "'U'", "<INVALID>", "'inf'" ]

    symbolicNames = [ "<INVALID>", "<INVALID>", "<INVALID>", "<INVALID>", 
                      "<INVALID>", "<INVALID>", "<INVALID>", "<INVALID>", 
                      "<INVALID>", "<INVALID>", "<INVALID>", "<INVALID>", 
                      "<INVALID>", "<INVALID>", "<INVALID>", "<INVALID>", 
                      "<INVALID>", "AND", "OR", "IMPLIES", "NOT", "EVENT", 
                      "ALWAYS", "UNTIL", "BOOLEAN", "INF", "VARIABLE", "RATIONAL", 
                      "WS" ]

    RULE_stlProperty = 0
    RULE_timeValue = 1
    RULE_expr = 2
    RULE_booleanExpr = 3

    ruleNames =  [ "stlProperty", "timeValue", "expr", "booleanExpr" ]

    EOF = Token.EOF
    T__0=1
    T__1=2
    T__2=3
    T__3=4
    T__4=5
    T__5=6
    T__6=7
    T__7=8
    T__8=9
    T__9=10
    T__10=11
    T__11=12
    T__12=13
    T__13=14
    T__14=15
    T__15=16
    AND=17
    OR=18
    IMPLIES=19
    NOT=20
    EVENT=21
    ALWAYS=22
    UNTIL=23
    BOOLEAN=24
    INF=25
    VARIABLE=26
    RATIONAL=27
    WS=28

    def __init__(self, input:TokenStream, output:TextIO = sys.stdout):
        super().__init__(input, output)
        self.checkVersion("4.13.0")
        self._interp = ParserATNSimulator(self, self.atn, self.decisionsToDFA, self.sharedContextCache)
        self._predicates = None




    class StlPropertyContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser


        def getRuleIndex(self):
            return stlParser.RULE_stlProperty

     
        def copyFrom(self, ctx:ParserRuleContext):
            super().copyFrom(ctx)


    class BooleanPredContext(StlPropertyContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a stlParser.StlPropertyContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def booleanExpr(self):
            return self.getTypedRuleContext(stlParser.BooleanExprContext,0)


        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterBooleanPred" ):
                listener.enterBooleanPred(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitBooleanPred" ):
                listener.exitBooleanPred(self)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitBooleanPred" ):
                return visitor.visitBooleanPred(self)
            else:
                return visitor.visitChildren(self)


    class FormulaContext(StlPropertyContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a stlParser.StlPropertyContext
            super().__init__(parser)
            self.left = None # StlPropertyContext
            self.op = None # Token
            self.child = None # StlPropertyContext
            self.low = None # TimeValueContext
            self.high = None # TimeValueContext
            self.right = None # StlPropertyContext
            self.copyFrom(ctx)

        def NOT(self):
            return self.getToken(stlParser.NOT, 0)
        def stlProperty(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(stlParser.StlPropertyContext)
            else:
                return self.getTypedRuleContext(stlParser.StlPropertyContext,i)

        def EVENT(self):
            return self.getToken(stlParser.EVENT, 0)
        def timeValue(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(stlParser.TimeValueContext)
            else:
                return self.getTypedRuleContext(stlParser.TimeValueContext,i)

        def ALWAYS(self):
            return self.getToken(stlParser.ALWAYS, 0)
        def IMPLIES(self):
            return self.getToken(stlParser.IMPLIES, 0)
        def AND(self):
            return self.getToken(stlParser.AND, 0)
        def OR(self):
            return self.getToken(stlParser.OR, 0)
        def UNTIL(self):
            return self.getToken(stlParser.UNTIL, 0)

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterFormula" ):
                listener.enterFormula(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitFormula" ):
                listener.exitFormula(self)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitFormula" ):
                return visitor.visitFormula(self)
            else:
                return visitor.visitChildren(self)


    class ParpropContext(StlPropertyContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a stlParser.StlPropertyContext
            super().__init__(parser)
            self.child = None # StlPropertyContext
            self.copyFrom(ctx)

        def stlProperty(self):
            return self.getTypedRuleContext(stlParser.StlPropertyContext,0)


        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterParprop" ):
                listener.enterParprop(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitParprop" ):
                listener.exitParprop(self)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitParprop" ):
                return visitor.visitParprop(self)
            else:
                return visitor.visitChildren(self)



    def stlProperty(self, _p:int=0):
        _parentctx = self._ctx
        _parentState = self.state
        localctx = stlParser.StlPropertyContext(self, self._ctx, _parentState)
        _prevctx = localctx
        _startState = 0
        self.enterRecursionRule(localctx, 0, self.RULE_stlProperty, _p)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 32
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input,0,self._ctx)
            if la_ == 1:
                localctx = stlParser.ParpropContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx

                self.state = 9
                self.match(stlParser.T__0)
                self.state = 10
                localctx.child = self.stlProperty(0)
                self.state = 11
                self.match(stlParser.T__1)
                pass

            elif la_ == 2:
                localctx = stlParser.BooleanPredContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 13
                self.booleanExpr()
                pass

            elif la_ == 3:
                localctx = stlParser.FormulaContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 14
                localctx.op = self.match(stlParser.NOT)
                self.state = 15
                localctx.child = self.stlProperty(7)
                pass

            elif la_ == 4:
                localctx = stlParser.FormulaContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 16
                localctx.op = self.match(stlParser.EVENT)
                self.state = 23
                self._errHandler.sync(self)
                if self._input.LA(1) == stlParser.T__2:
                    self.state = 17
                    self.match(stlParser.T__2)
                    self.state = 18
                    localctx.low = self.timeValue()
                    self.state = 19
                    self.match(stlParser.T__3)
                    self.state = 20
                    localctx.high = self.timeValue()
                    self.state = 21
                    self.match(stlParser.T__4)
                    pass

                self.state = 24
                localctx.child = self.stlProperty(6)
                pass

            elif la_ == 5:
                localctx = stlParser.FormulaContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 26
                localctx.op = self.match(stlParser.ALWAYS)
                self.state = 33
                self._errHandler.sync(self)
                if self._input.LA(1) == stlParser.T__2:
                    self.state = 27
                    self.match(stlParser.T__2)
                    self.state = 28
                    localctx.low = self.timeValue()
                    self.state = 29
                    self.match(stlParser.T__3)
                    self.state = 30
                    localctx.high = self.timeValue()
                    self.state = 31
                    self.match(stlParser.T__4)
                    pass

                self.state = 34
                localctx.child = self.stlProperty(5)
                pass


            self._ctx.stop = self._input.LT(-1)
            self.state = 54
            self._errHandler.sync(self)
            _alt = self._interp.adaptivePredict(self._input,2,self._ctx)
            while _alt!=2 and _alt!=ATN.INVALID_ALT_NUMBER:
                if _alt==1:
                    if self._parseListeners is not None:
                        self.triggerExitRuleEvent()
                    _prevctx = localctx
                    self.state = 52
                    self._errHandler.sync(self)
                    la_ = self._interp.adaptivePredict(self._input,1,self._ctx)
                    if la_ == 1:
                        localctx = stlParser.FormulaContext(self, stlParser.StlPropertyContext(self, _parentctx, _parentState))
                        localctx.left = _prevctx
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_stlProperty)
                        self.state = 34
                        if not self.precpred(self._ctx, 4):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 4)")
                        self.state = 35
                        localctx.op = self.match(stlParser.IMPLIES)
                        self.state = 36
                        localctx.right = self.stlProperty(5)
                        pass

                    elif la_ == 2:
                        localctx = stlParser.FormulaContext(self, stlParser.StlPropertyContext(self, _parentctx, _parentState))
                        localctx.left = _prevctx
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_stlProperty)
                        self.state = 37
                        if not self.precpred(self._ctx, 3):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 3)")
                        self.state = 38
                        localctx.op = self.match(stlParser.AND)
                        self.state = 39
                        localctx.right = self.stlProperty(4)
                        pass

                    elif la_ == 3:
                        localctx = stlParser.FormulaContext(self, stlParser.StlPropertyContext(self, _parentctx, _parentState))
                        localctx.left = _prevctx
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_stlProperty)
                        self.state = 40
                        if not self.precpred(self._ctx, 2):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 2)")
                        self.state = 41
                        localctx.op = self.match(stlParser.OR)
                        self.state = 42
                        localctx.right = self.stlProperty(3)
                        pass

                    elif la_ == 4:
                        localctx = stlParser.FormulaContext(self, stlParser.StlPropertyContext(self, _parentctx, _parentState))
                        localctx.left = _prevctx
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_stlProperty)
                        self.state = 47
                        if not self.precpred(self._ctx, 1):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 1)")
                        self.state = 48
                        localctx.op = self.match(stlParser.UNTIL)
                        self.state = 56
                        self._errHandler.sync(self)
                        if self._input.LA(1) == stlParser.T__2:
                            self.state = 49
                            self.match(stlParser.T__2)
                            self.state = 50
                            localctx.low = self.timeValue()
                            self.state = 51
                            self.match(stlParser.T__3)
                            self.state = 52
                            localctx.high = self.timeValue()
                            self.state = 53
                            self.match(stlParser.T__4)
                            pass

                        self.state = 57
                        localctx.right = self.stlProperty(2)
                        pass

             
                self.state = 56
                self._errHandler.sync(self)
                _alt = self._interp.adaptivePredict(self._input,2,self._ctx)

        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.unrollRecursionContexts(_parentctx)
        return localctx


    class TimeValueContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def RATIONAL(self):
            return self.getToken(stlParser.RATIONAL, 0)

        def INF(self):
            return self.getToken(stlParser.INF, 0)

        def getRuleIndex(self):
            return stlParser.RULE_timeValue

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterTimeValue" ):
                listener.enterTimeValue(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitTimeValue" ):
                listener.exitTimeValue(self)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitTimeValue" ):
                return visitor.visitTimeValue(self)
            else:
                return visitor.visitChildren(self)




    def timeValue(self):

        localctx = stlParser.TimeValueContext(self, self._ctx, self.state)
        self.enterRule(localctx, 2, self.RULE_timeValue)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 57
            _la = self._input.LA(1)
            if not(_la==25 or _la==27):
                self._errHandler.recoverInline(self)
            else:
                self._errHandler.reportMatch(self)
                self.consume()
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class ExprContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def expr(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(stlParser.ExprContext)
            else:
                return self.getTypedRuleContext(stlParser.ExprContext,i)


        def VARIABLE(self):
            return self.getToken(stlParser.VARIABLE, 0)

        def RATIONAL(self):
            return self.getToken(stlParser.RATIONAL, 0)

        def getRuleIndex(self):
            return stlParser.RULE_expr

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterExpr" ):
                listener.enterExpr(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitExpr" ):
                listener.exitExpr(self)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitExpr" ):
                return visitor.visitExpr(self)
            else:
                return visitor.visitChildren(self)



    def expr(self, _p:int=0):
        _parentctx = self._ctx
        _parentState = self.state
        localctx = stlParser.ExprContext(self, self._ctx, _parentState)
        _prevctx = localctx
        _startState = 4
        self.enterRecursionRule(localctx, 4, self.RULE_expr, _p)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 71
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input,3,self._ctx)
            if la_ == 1:
                self.state = 60
                _la = self._input.LA(1)
                if not(_la==1 or _la==6):
                    self._errHandler.recoverInline(self)
                else:
                    self._errHandler.reportMatch(self)
                    self.consume()
                self.state = 61
                self.expr(0)
                self.state = 62
                self.match(stlParser.T__1)
                pass

            elif la_ == 2:
                self.state = 64
                self.match(stlParser.VARIABLE)
                self.state = 65
                self.match(stlParser.T__0)
                self.state = 66
                self.expr(0)
                self.state = 67
                self.match(stlParser.T__1)
                pass

            elif la_ == 3:
                self.state = 69
                self.match(stlParser.RATIONAL)
                pass

            elif la_ == 4:
                self.state = 70
                self.match(stlParser.VARIABLE)
                pass


            self._ctx.stop = self._input.LT(-1)
            self.state = 84
            self._errHandler.sync(self)
            _alt = self._interp.adaptivePredict(self._input,5,self._ctx)
            while _alt!=2 and _alt!=ATN.INVALID_ALT_NUMBER:
                if _alt==1:
                    if self._parseListeners is not None:
                        self.triggerExitRuleEvent()
                    _prevctx = localctx
                    self.state = 82
                    self._errHandler.sync(self)
                    la_ = self._interp.adaptivePredict(self._input,4,self._ctx)
                    if la_ == 1:
                        localctx = stlParser.ExprContext(self, _parentctx, _parentState)
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_expr)
                        self.state = 73
                        if not self.precpred(self._ctx, 6):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 6)")
                        self.state = 74
                        self.match(stlParser.T__6)
                        self.state = 75
                        self.expr(6)
                        pass

                    elif la_ == 2:
                        localctx = stlParser.ExprContext(self, _parentctx, _parentState)
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_expr)
                        self.state = 76
                        if not self.precpred(self._ctx, 4):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 4)")
                        self.state = 77
                        _la = self._input.LA(1)
                        if not(_la==8 or _la==9):
                            self._errHandler.recoverInline(self)
                        else:
                            self._errHandler.reportMatch(self)
                            self.consume()
                        self.state = 78
                        self.expr(5)
                        pass

                    elif la_ == 3:
                        localctx = stlParser.ExprContext(self, _parentctx, _parentState)
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_expr)
                        self.state = 79
                        if not self.precpred(self._ctx, 3):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 3)")
                        self.state = 80
                        _la = self._input.LA(1)
                        if not(_la==10 or _la==11):
                            self._errHandler.recoverInline(self)
                        else:
                            self._errHandler.reportMatch(self)
                            self.consume()
                        self.state = 81
                        self.expr(4)
                        pass

             
                self.state = 86
                self._errHandler.sync(self)
                _alt = self._interp.adaptivePredict(self._input,5,self._ctx)

        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.unrollRecursionContexts(_parentctx)
        return localctx


    class BooleanExprContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser
            self.left = None # ExprContext
            self.op = None # Token
            self.right = None # ExprContext
            self.variable = None # Token

        def expr(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(stlParser.ExprContext)
            else:
                return self.getTypedRuleContext(stlParser.ExprContext,i)


        def BOOLEAN(self):
            return self.getToken(stlParser.BOOLEAN, 0)

        def VARIABLE(self):
            return self.getToken(stlParser.VARIABLE, 0)

        def getRuleIndex(self):
            return stlParser.RULE_booleanExpr

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterBooleanExpr" ):
                listener.enterBooleanExpr(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitBooleanExpr" ):
                listener.exitBooleanExpr(self)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitBooleanExpr" ):
                return visitor.visitBooleanExpr(self)
            else:
                return visitor.visitChildren(self)




    def booleanExpr(self):

        localctx = stlParser.BooleanExprContext(self, self._ctx, self.state)
        self.enterRule(localctx, 6, self.RULE_booleanExpr)
        self._la = 0 # Token type
        try:
            self.state = 93
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input,6,self._ctx)
            if la_ == 1:
                self.enterOuterAlt(localctx, 1)
                self.state = 87
                localctx.left = self.expr(0)
                self.state = 88
                localctx.op = self._input.LT(1)
                _la = self._input.LA(1)
                if not((((_la) & ~0x3f) == 0 and ((1 << _la) & 126976) != 0)):
                    localctx.op = self._errHandler.recoverInline(self)
                else:
                    self._errHandler.reportMatch(self)
                    self.consume()
                self.state = 89
                localctx.right = self.expr(0)
                pass

            elif la_ == 2:
                self.enterOuterAlt(localctx, 2)
                self.state = 91
                localctx.op = self.match(stlParser.BOOLEAN)
                pass

            elif la_ == 3:
                self.enterOuterAlt(localctx, 3)
                self.state = 92
                localctx.variable = self.match(stlParser.VARIABLE)
                pass


        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx



    def sempred(self, localctx:RuleContext, ruleIndex:int, predIndex:int):
        if self._predicates == None:
            self._predicates = dict()
        self._predicates[0] = self.stlProperty_sempred
        self._predicates[2] = self.expr_sempred
        pred = self._predicates.get(ruleIndex, None)
        if pred is None:
            raise Exception("No predicate with index:" + str(ruleIndex))
        else:
            return pred(localctx, predIndex)

    def stlProperty_sempred(self, localctx:StlPropertyContext, predIndex:int):
            if predIndex == 0:
                return self.precpred(self._ctx, 4)
         

            if predIndex == 1:
                return self.precpred(self._ctx, 3)
         

            if predIndex == 2:
                return self.precpred(self._ctx, 2)
         

            if predIndex == 3:
                return self.precpred(self._ctx, 1)
         

    def expr_sempred(self, localctx:ExprContext, predIndex:int):
            if predIndex == 4:
                return self.precpred(self._ctx, 6)
         

            if predIndex == 5:
                return self.precpred(self._ctx, 4)
         

            if predIndex == 6:
                return self.precpred(self._ctx, 3)
         



