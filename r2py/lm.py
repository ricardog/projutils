from rpy2.robjects import Formula
from rpy2.robjects import pandas2ri
from rpy2.robjects.packages import importr


class LM(object):
    """Class for fitting (simple) linear models using rpy2.  When extracting
    the coefficients for a model (lmerMod or glmerMod) that uses orthogonal
    polynomials (poly in R syntax), it is necessary to fit a linear model
    that maps from the original data to the fitted polynomial.  The mermod
    class uses this class to fir such linear models.

    """

    def __init__(self, formula=None, response=None, predictors=None):
        self.__stats = importr("stats")
        self.formula = formula
        self.response = response
        self.predictors = predictors
        self._coefs = None

    @property
    def formula(self):
        return self._formula

    @formula.setter
    def formula(self, f):
        self._formula = Formula(f)
        self.env = self._formula.environment

    def fit(self):
        """Fit the linear model and extract the coefficients.
        FIXME: This function assumes the model has a single predictor variable (x), but may appear multiple times with different exponents.  That is, the equation must be of the form

            y ~ x + I(x^2) + I(x^3)"""
        if self.formula is None or self.response is None or self.predictors is None:
            raise RuntimeError("set formula, response, and predictor variables")
        ## FIXME: This is a quick and dirty hack.
        self.env["y"] = self.response
        self.env["x"] = self.predictors.loc[:, "x"]
        fit = self.__stats.lm(self.formula)
        self._coefs = pandas2ri.ri2py(fit.rx("coefficients")[0])

    @property
    def coefs(self):
        if self._coefs == None:
            self.fit()
        return self._coefs
