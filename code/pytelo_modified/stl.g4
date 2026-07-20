grammar stl;

@header {
'''
 Copyright (C) 2015-2020 Cristian Ioan Vasile <cvasile@lehigh.edu>
 Hybrid and Networked Systems (HyNeSs) Group, BU Robotics Lab, Boston University
 Explainable Robotics Lab, Lehigh University
 See license.txt file for license information.
'''
}


stlProperty:
          '(' child=stlProperty ')' #parprop
    |     booleanExpr #booleanPred
    |     op=NOT child=stlProperty #formula
    |     op=EVENT ('[' low=timeValue ',' high=timeValue ']')? child=stlProperty #formula
    |     op=ALWAYS ('[' low=timeValue ',' high=timeValue ']')? child=stlProperty #formula
    |     left=stlProperty op=IMPLIES right=stlProperty #formula
    |     left=stlProperty op=AND right=stlProperty #formula
    |     left=stlProperty op=OR right=stlProperty #formula
    |     left=stlProperty op=UNTIL ('[' low=timeValue ',' high=timeValue ']')? right=stlProperty #formula
    ;

timeValue:
      RATIONAL
    | INF
    ;

expr:
          ( '-(' | '(' ) expr ')'
    |    <assoc=right>     expr '^' expr
    |     VARIABLE '(' expr ')'
    |     expr ( '*' | '/' ) expr
    |     expr ( '+' | '-' ) expr
    |     RATIONAL
    |     VARIABLE
    ;

booleanExpr:
          left=expr op=( '<' | '<=' | '=' | '>=' | '>' ) right=expr
    |     op=BOOLEAN
    |     variable=VARIABLE
    ;

AND : '&' | '&&' | '/\\' ;
OR : '|' | '||' | '\\/' ;
IMPLIES : '=>' ;
NOT : '!' | '~' ;
EVENT : 'F' | '<>' ;
ALWAYS : 'G' | '[]' ;
UNTIL : 'U' ;
BOOLEAN : 'true' | 'True' | 'false' | 'False' ;

INF : 'inf' ;

VARIABLE : ( [a-z] | [A-Z] )( [a-z] | [A-Z] | [0-9] | '_' | '.' )* ;
RATIONAL : ('-')? [0-9]* ('.')? [0-9]+ ( 'E' | 'E-' )? [0-9]* ;
WS : ( ' ' | '\t' | '\r' | '\n' )+ -> skip ;
