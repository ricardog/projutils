#!/usr/bin/env python

from pyparsing import ParseException

import rparser

if __name__ == "__main__":
    tests = [
        "sin( 1 + 2 * x ) + tan( 2.123 * x )",
        "poly(log(cropland + 1), 3)",
        "poly(log(cropland + 1), 3)2",
        "factor(unSub)143:poly(log(cropland + 1), 3)2",
        "factor(unSub)143:poly(log(cropland + 1), 3)3:poly(log(hpd + 1), 3)2",
    ]
    results = [
        "[[['sin', [[1, '+', [2, '*', 'x']]]], '+', ['tan', [[2.123, '*', 'x']]]]]",
        "[['poly', [['log', [['cropland', '+', 1]]], 3]]]",
        "[['poly', [['log', [['cropland', '+', 1]]], 3], 2]]",
        "[[['factor', ['unSub'], 143], ':', ['poly', [['log', [['cropland', '+', 1]]], 3], 2]]]",
        "[[['factor', ['unSub'], 143], ':', ['poly', [['log', [['cropland', '+', 1]]], 3], 3], ':', ['poly', [['log', [['hpd', '+', 1]]], 3], 2]]]", # noqa E501
    ]
    for i, t in enumerate(tests):
        result = rparser.PARSER.parseString(t)
        assert str(result) == results[i]
        print(result)
        nodes = rparser.parse(t)
        print(nodes)

    r1 = rparser.parse(tests[2])
    r2 = rparser.parse(tests[3])
    assert r1 == r2.args[1], "expected trees to be equal %s != %s" % (
        repr(r1),
        repr(r2.args[1]),
    )
    assert r1 != r2, "expected trees to not be equal %s == %s" % (repr(r1), repr(r2))

    # Try parsing model terms
    import glm as glm
    import rpy2.robjects as robjects

    models = robjects.r(
        'models <- readRDS("out/_d5ed9724c6cb2c78b59707f69b3044e6/cropland.rds")'
    )
    mod = glm.GLM(models[0])
    for t in mod.coefficients().itertuples():
        factor = t[0]
        print(
            factor + " -> ",
        )
        try:
            print(rparser.parse(factor))
        except ParseException as e:
            print(e)
            pass
