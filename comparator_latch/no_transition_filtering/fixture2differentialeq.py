#========================================================================
#
#   fixture2differentialeq.py
#   Functions which take parameters from fixture and output a differential
#   equation which describes the sytstem
#
#   -w
#
#========================================================================

import yaml
from math import pi
from pathlib import Path

import numpy as np
from sympy.integrals import inverse_laplace_transform
import sympy as sym
from sympy.abc import s,t,x,y,z
import cmath

#Laplace and time domain dictionary... add more as needed - can probably chatGPT this
laplace_time_dict = {
    1 : "x",
    s : "x'",
    s**2 : "x''"
}

def read_yaml( f ):
    with open(f, 'r') as stream:
        return yaml.safe_load(stream)



def polarparam_to_coeff_dict( params_yaml, VREG, VREF ):
        

    # read the two yaml files

    params  = read_yaml( params_yaml )

    #This lambda indexes into the different parameters of the analog block
    a = params.items()
    paramdict_comp = {}
    for i , ( k , e ) in enumerate(a):
        paramdict_comp[k] = VREF * e['VREF_to_' + k]['const_1'] + VREG * e['VREG_to_' + k]['const_1'] + e['const_' + k]['const_1']

    print(paramdict_comp)
    G = 1

    for param, value in paramdict_comp.items():
        if 'p' in param:
            G = G / (s - value)
        else:
            G = G * (s - value)



    #Initialize the transfer function, need to manually enter this for the time being.

    #Simplify G, just in case
    G = sym.simplify(G)
    # G = Y(s)/U(s). Isolate both sides
    Numer, Denom = sym.fraction(G)

    #Expand Factors
    Numer = sym.expand_mul(Numer)
    Denom = sym.expand_mul(Denom)

    #create dictionary of coefficients
    Numer_dict = Numer.as_coefficients_dict(s)
    Denom_dict = Denom.as_coefficients_dict(s)

    #return for further processing by other means.
    return (Numer_dict, Denom_dict)

def polarparam_to_diff_dict( params_yaml, vargen, VREG, VREF):
    Numer_dict, Denom_dict= polarparam_to_coeff_dict( params_yaml, VREG, VREF)
    u = vargen.definevar("u")
    y = vargen.definevar("y")

    order = {s:1, 1:0, s**2:2, s**3:3, s**4:4, s**5:5, s**6:6}
    print("--- transfer function coefficiencts ---")
    print(" numerator: %s" % str(Numer_dict))
    print(" denominator: %s" % str(Denom_dict))
    terms = []

    for v,coeff in Denom_dict.items():
        terms.append(coeff*vargen.deriv(y,order[v]))
    Yexpr = sum(terms)

    terms = []
    for v,coeff in Numer_dict.items():
        terms.append(coeff*vargen.deriv(u,order[v]))
    Uexpr = sum(terms)

    # Y/U = N/D
    # Y*D = N*U
    # 0 = N*U-Y*D
    print("--- transfer function expressions (U = Y)---")
    print(" U expr: %s" % Uexpr)
    print(" Y expr: %s" % Yexpr)
    Expr = sym.Eq(Uexpr, Yexpr)
    print("Implicit differential equation: %s" % Expr)

    # difficult to solve implicit differential equations. 
    # transform into an explicit differential equation.
    print("----- transform to explicit n-th order ODE ----")
    lhs = vargen.highest_order("y")
    print(" [separating out variable %s from %s]" % (lhs, Expr))
    rhs, = sym.solveset(Expr,lhs)
    explicit_ode = sym.Eq(lhs, rhs)
    print(" Explicit Differential Equation: %s" % explicit_ode)

    print("---- transform into first-order ordinary differential equations ----")
    print("-> replace higher order derivatives with variables")
    repl_dict = {}
    for order,var,deriv in vargen.derivatives():
        newvar = vargen.definevar("d%s_d%d" % (var,order))
        repl_dict[deriv] = newvar

    print("-> create first-order explicit ODEs")
    ho_y = vargen.highest_order("y")
    ho_u = vargen.highest_order("u")
    vargen.add_ode(y,repl_dict[sym.Derivative(y,t)])
    vargen.add_ode(u,repl_dict[sym.Derivative(u,t)])
    for ddt, var in repl_dict.items():
        deriv_ddt = sym.Derivative(ddt,t)
        if ddt != ho_y and ddt != ho_u:
            vargen.add_ode(var,repl_dict[deriv_ddt])
        elif ddt == ho_y:
            fo_rhs = rhs.subs(repl_dict)
            vargen.add_ode(repl_dict[lhs], fo_rhs)


    return explicit_ode

def polarparam_to_sympyeq( params_yaml ):
        

    # read the two yaml files
    params  = read_yaml( params_yaml )

    #This lambda indexes into the different parameters of the analog block
    read_param = lambda name: params[name]['const_{}'.format(name)]['const_1']
    a = params.items()

    paramdict = dict(map(lambda p:(p[0],p[1]['const_{}'.format(p[0])]['const_1']), params.items()))
    #Take the poles from the file
    #the msdsl demo uses some sort of timestep-based solver, here I just
    #solve the entire thing using sympy
    print(paramdict)
    params = ['pi', 'pr', 'zi', 'zr']
    params_separated = {}
    for pr in params:
        params_separated[pr] =[]
        for prv in paramdict.keys():
            if(pr in prv):
                params_separated[pr].append(prv)
    
    paramdict_comp = {}
    for p in ['pr','zr']:
        for i, param in enumerate(params_separated[p]):
            paramdict_comp[p[0] + str(i)] = complex(paramdict[param], paramdict[param.replace('r','i')])
    
    print(paramdict_comp)
    G = 1 / (s)

    for param, value in paramdict_comp.items():
        if 'p' in param:
            G = G / (s - value)
        else:
            G = G * (s - value)

    return G