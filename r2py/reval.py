
import collections
import importlib
import inspect
import numpy as np
import pandas as pd
import string

from . import poly
from .tree import Node, Operator

Context = collections.namedtuple('Context', 'context index')

def to_list(l):
  return '[' + ', '.join(map(str, l)) + ']'

def to_rexpr(root):
  if isinstance(root, str):
    return root
  if isinstance(root, int):
    return str(root)
  if isinstance(root, float):
    return str(root)
  if root.type is Operator('+'):
    return ' + '.join(map(to_rexpr, root.args))
  if root.type is Operator('-'):
    return ' - '.join(map(to_rexpr, root.args))
  if root.type is Operator('*'):
    return ' * '.join(map(to_rexpr, root.args))
  if root.type is Operator('/'):
    return ' / '.join(map(to_rexpr, root.args))
  if root.type is Operator('I'):
    return 'I(%s)' % to_rexpr(root.args[0])
  if root.type is Operator('in'):
    return '%s' % root.args[0]
  if root.type is Operator('sel'):
    return '%s[%d]' % (to_rexpr(root.args[0]), root.args[1])
  if root.type is Operator('poly'):
    return 'poly(%s, %d)' % (to_rexpr(root.args[0]), root.args[1])
  if root.type is Operator('log'):
    return 'log(%s)' % to_rexpr(root.args[0])
  if root.type is Operator('exp'):
    return 'exp(%s)' % to_rexpr(root.args[0])
  if root.type is Operator('scale'):
    return 'rescale(%s, newrange = c(%d, %d))' % (to_rexpr(root.args[0]),
                                                  root.args[1], root.args[2])
  raise ValueError("unexpected node type: %s" % repr(root.type))

def to_repr(root):
  if isinstance(root, str):
    return root
  if isinstance(root, int):
    return "%d" % root
  if isinstance(root, float):
    return "%f" % root
  if root.type is Operator('+'):
    return '(+ ' + ' '.join(map(to_repr, root.args)) + ')'
  if root.type is Operator('-'):
    return '(- ' + ' '.join(map(to_repr, root.args)) + ')'
  if root.type is Operator('*'):
    return '(* ' + ' '.join(map(to_repr, root.args)) + ')'
  if root.type is Operator('/'):
    return '(/ ' + ' '.join(map(to_repr, root.args)) + ')'
  if root.type is Operator(':'):
    return '(* ' + ' '.join(map(to_repr, root.args)) + ')'
  if root.type is Operator('=='):
    return '(== ' + ' '.join(map(to_repr, root.args)) + ')'
  if root.type is Operator('in'):
      return '%s' % root.args[0]
  if root.type is Operator('I'):
    return to_repr(root.args[0])
  if root.type is Operator('var'):
    return to_repr(root.args[1])
  if root.type is Operator('list'):
    return '[' + ', '.join(map(str, root.args)) + ']'
  if root.type is Operator('sel'):
    expr = to_repr(root.args[0])
    return '(%s[%d])' % (expr, root.args[1])
    #return '%s[%d]' % (expr, root.args[1])
    #return '(%s[:, %d])' % (expr, root.args[1])
  if root.type is Operator('poly'):
    assert len(root.args) == 4, "norm2 and alpha not set"
    return '(%s ** %d)' % (to_repr(root.args[0]), root.args[1])
  if root.type is Operator('poly_fit'):
    return 'poly.ortho_poly_fit(%s, %d)' % (to_repr(root.args[0]), root.args[1])
  if root.type is Operator('log'):
    return '(log(%s))' % to_repr(root.args[0])
  if root.type is Operator('exp'):
    return '(exp(%s))' % to_repr(root.args[0])
  if root.type is Operator('scale'):
    if len(root.args) == 3:
      return '(scale(%s, %d, %d))' % (to_repr(root.args[0]),
                                      root.args[1], root.args[2])
    if len(root.args) == 5:
      return '(scale(%s, %d, %d, %f, %f))' % (to_repr(root.args[0]),
                                              root.args[1], root.args[2],
                                              root.args[3], root.args[4])
    raise ValueError("unexpected number of arguments for scale: %s" %
                     ', '.join(map(str, root.args)))
  if root.type is Operator('pow'):
    return '(pow(%s, %s))' % (to_repr(root.args[0]),
                              to_repr(root.args[1]))
  if root.type is Operator('max'):
    return '(max(%s, %s))' % (to_repr(root.args[0]),
                              to_repr(root.args[1]))
  if root.type is Operator('min'):
    return '(min(%s, %s))' % (to_repr(root.args[0]),
                              to_repr(root.args[1]))
  if root.type is Operator('inv_logit'):
    expr = to_repr(root.args[0])
    return '(exp(%s) / (1 + exp(%s)))' % (expr, expr)
  raise ValueError("unexpected node type: %s" % repr(root.type))

def to_expr(root, ctx=None):
  recurse = lambda x: to_expr(x, ctx)
  guvec = lambda: ctx is not None and ctx.context == 'guvec'
  jit = lambda: ctx is not None and ctx.context == 'jit'
  if isinstance(root, str):
    return root
  if isinstance(root, int):
    return "np.float32(%d)" % root
  if isinstance(root, float):
    return "np.float32(%f)" % root
  if root.type is Operator('+'):
    return '(' + ' + '.join(map(recurse, root.args)) + ')'
  if root.type is Operator('-'):
    return '(' + ' - '.join(map(recurse, root.args)) + ')'
  if root.type is Operator('*'):
    return '(' + ' * '.join(map(recurse, root.args)) + ')'
  if root.type is Operator('/'):
    return '(' + ' / '.join(map(recurse, root.args)) + ')'
  if root.type is Operator(':'):
    return '(' + ' * '.join(map(recurse, root.args)) + ')'
  if root.type is Operator('=='):
    return '(' + ' == '.join(map(recurse, root.args)) + ')'
  if root.type is Operator('in'):
    if guvec():
      return '%s[0]' % root.args[0]
    elif jit():
      return '%s[%s]' % (root.args[0], ctx.index)
    else:
      return '%s' % root.args[0]
  if root.type is Operator('I'):
    return recurse(root.args[0])
  if root.type is Operator('var'):
    return 'var_%d' % hash(root.args[0])
  if root.type is Operator('list'):
    return '[' + ', '.join(map(str, root.args)) + ']'
  if root.type is Operator('sel'):
    expr = recurse(root.args[0])
    if isinstance(root.args[0], str):
      import pdb; pdb.set_trace()
    if guvec():
      return '(%s[%d])' % (expr, root.args[1])
    elif jit():
      if isinstance(root.args[0], Node) and \
         root.args[0].type is Operator('in'):
        # NOTE: This is a horrible kludge.  Naturally a select with an
        # input would translate into
        #   var_333096001[idx][3]
        
        # unfortunately numba is really slow at compiling this.  Compile
        # time drop from ~4 min to ~40 sec if I use
        #   var_333096001[idx, 3]
        return '%s[%s, %d]' % (to_expr(root.args[0]), ctx.index, root.args[1])
      else:
        return '%s[%d]' % (expr, root.args[1])
    else:
      return '(%s[:, %d])' % (expr, root.args[1])
  if root.type is Operator('poly'):
    assert len(root.args) == 4, "norm2 and alpha not set"
    return '(poly.ortho_poly_predict(%s, %s, %s, %d))' % (recurse(root.args[0]),
                                                          recurse(root.args[2]),
                                                          recurse(root.args[3]),
                                                          root.args[1])
  if root.type is Operator('poly_fit'):
    return 'poly.ortho_poly_fit(%s, %d)' % (recurse(root.args[0]), root.args[1])
  if root.type is Operator('log'):
    return '(ma.log(%s))' % recurse(root.args[0])
  if root.type is Operator('exp'):
    return '(ma.exp(%s))' % recurse(root.args[0])
  if root.type is Operator('scale'):
    if len(root.args) == 3:
      return '(poly.scale(%s, %d, %d))' % (recurse(root.args[0]),
                                           root.args[1], root.args[2])
    if len(root.args) == 5:
      return '(poly.scale(%s, %d, %d, %f, %f))' % (recurse(root.args[0]),
                                                   root.args[1], root.args[2],
                                                   root.args[3], root.args[4])
    raise ValueError("unexpected number of arguments for scale: %s" %
                     ', '.join(map(str, root.args)))
  if root.type is Operator('pow'):
    return '(np.power(%s, %s))' % (recurse(root.args[0]),
                                     recurse(root.args[1]))
  if root.type is Operator('max'):
    return '(np.maximum(%s, %s))' % (recurse(root.args[0]),
                                     recurse(root.args[1]))
  if root.type is Operator('min'):
    return '(np.minimum(%s, %s))' % (recurse(root.args[0]),
                                     recurse(root.args[1]))
  if root.type is Operator('inv_logit'):
    expr = recurse(root.args[0])
    return '(np.exp(%s) / (1 + np.exp(%s)))' % (expr, expr)
  raise ValueError("unexpected node type: %s" % repr(root.type))

def make_inputs(root):
  def replace(node):
    if isinstance(node, str):
      return Node(Operator('in'), (node, 'float32[:]'))
    if isinstance(node, Node) and node.type is Operator('in'):
      raise StopIteration
    return node
  return replace(root) if isinstance(root, str) else root.transform(replace)

def find_syms(root, ctx=None):
  lsyms = collections.OrderedDict()
  if isinstance(root, Node):
    for node in root.walk():
      if isinstance(node, Node) and node.type == Operator('var'):
        name = 'var_%d' % node.args[0]
        if name not in lsyms:
          lsyms[name] = to_expr(node.args[1], ctx)
  return lsyms

def find_inputs(root):
  return tuple(find_input_types(root).keys())

def find_input_types(root):
  types = collections.OrderedDict()
  assert isinstance(root, Node), 'node should be a Node'
  for node in root.walk():
    if (isinstance(node, Node) and node.type is Operator('in') and
        node.args[0] not in types):
      types[node.args[0]] = node.args[1:3]
  return types

def find_nonvector(root):
  letters = list(string.ascii_lowercase)
  nonvector = (Operator('poly'), )
  nodes = collections.OrderedDict()
  def replace(node):
    if not isinstance(node, Node):
      return node
    if node.type is Operator('var') and node.args[1].type in nonvector:
      nodes[node.args[0]] = node.args[1]
      if node.args[1].type is Operator('poly'):
        t = 'float32[:, :]'
      else:
        t = 'float32[:]'
      return Node(Operator('in'), ("var_%d" % node.args[0], t))
    if node.type in nonvector:
      nodes[hash(node)] = node
      if node.type is Operator('poly'):
        t = 'float32[:, :]'
      else:
        t = 'float32[:]'
      #return "var_%d" % hash(node)
      return Node(Operator('in'), ("var_%d" % hash(node), t))
    return node
  root.transform(replace)
  ## Walk the tree again to verify are no non-vectorizable nodes left
  for node in root.walk():
    if isinstance(node, Node):
      assert not node.type in nonvector, 'non-vectorizable operator left'
  return nodes

def evalr(root, stab):
  if isinstance(stab, pd.DataFrame):
    lsyms = dict()
    for col in stab.columns:
      lsyms[col] = stab[col]
  else:
    lsyms = stab
  for name, expr in find_syms(root).items():
    if name not in lsyms:
      lsyms[name] = eval(to_expr(expr), None, lsyms)
  return eval(to_expr(root), None, lsyms)

def to_py(root, fname):
  lsyms = find_syms(root)
  decls = ["%s = %s" % (name, lsyms[name]) for name in lsyms.keys()]
  inputs = find_inputs(root)
  prelude = '''
import numpy as np
import numpy.ma as ma
import projections.r2py.poly as poly
'''
  expr = 'return ' + to_expr(root)
  iodecls = ['%s' % v for v in sorted(set(inputs))]
  fdecl =  "def %s(%s):" % (fname, ', '.join(iodecls))
  fun1 = fdecl + "\n  " + ";".join(decls) + "\n  " + expr
  fdecl = "def %s_st(stab):" % fname
  iodecls = ["stab['%s']" % v for v in sorted(set(inputs))]
  fun2 = fdecl + "\n  return %s(%s)" % (fname, ", ".join(iodecls))
  fun3 = "def func_name(): return '%s'" % fname
  return prelude + "\n\n\n" + fun1 + "\n\n\n" + fun2 + "\n\n\n" + fun3 + "\n\n"

def to_pyx(root, fname):
  lsyms = find_syms(root)
  decls = ["cdef np.ndarray %s = %s" % (name, lsyms[name])
           for name in lsyms.keys()]
  inputs = find_inputs(root)
  prelude = '''
cimport cython
import projections.r2py.poly as poly
cimport numpy as np
import numpy.ma as ma
DTYPE = np.float
ctypedef np.float_t DTYPE_t
'''
  expr = 'return ' + to_expr(root)
  iodecls = ['np.ndarray[DTYPE_t, ndim=1] %s not None' % v
             for v in sorted(set(inputs))]
  fdecl =  ("@cython.boundscheck(False)\n" +
            "def %s(%s):" % (fname, ', '.join(iodecls)))
  fun1 = fdecl + "\n  " + ";".join(decls + [expr])
  fun2 = "def func_name(): return '%s'" % fname
  return prelude + "\n\n\n" + fun1 + "\n\n\n" + fun2 + "\n\n"

# rreplace('(), (), ()', ',', ' ->', 1)
def rreplace(src, what, repl, num=1):
  return repl.join(src.rsplit(what, num))

def to_numba(root, fname, out_name, child=False, ctx=None):
  inputs = find_inputs(root)
  poly_src = inspect.getsource(poly.ortho_poly_predict)
  impts = '''
from numba import jit, guvectorize, float32, int64
import numpy as np
import numpy.ma as ma
import projections.r2py.poly as poly
{poly}
'''.format(poly=poly_src)
  ## *****
  ## NOTE: This operation modifies the expression tree.
  ## *****
  io_types = find_input_types(root)
  ios = sorted(io_types.keys())
  nonvector = find_nonvector(root)
  params = ["df['%s']" % v for v in sorted(inputs)]
  
  if nonvector:
    vec_fun = to_numba(root, '_' + fname, out_name, child=True)
    inner_inputs = sorted(find_inputs(root))
    stmts = ["var_%d = %s" % (name, to_expr(nonvector[name]))
             for name in nonvector.keys()]
    body = '''
{vec_fun}
def {fname}({iodecls}):
  {stmts}
  return _{fname}({inputs})
'''.format(vec_fun = vec_fun,
           fname = fname,
           iodecls = ', '.join(ios),
           stmts = '\n  '.join(stmts),
           inputs = ', '.join(inner_inputs))
  else:
    lsyms = find_syms(root, Context('jit', 'idx'))
    stmts = ["%s = %s" % (name, lsyms[name]) for name in lsyms.keys()]
    expr = to_expr(root, Context('jit', 'idx'))
    nb_types = ', '.join([io_types[x][0] for x in sorted(io_types)])
    body = '''
@jit(#[float32[:]({nb_types})],
     cache=True, nopython=True, nogil=True)
def {fname}({iodecls}):
  res = np.empty({first_in}.size, dtype=np.float32)
  for idx in np.arange({first_in}.size):
    {stmts}
    res[idx] = {expr}
  return res
'''.format(nb_types = nb_types,
           fname = fname,
           iodecls = ', '.join(ios),
           first_in = inputs[0],
           stmts = "\n    ".join(stmts),
           expr = expr)
    if child:
      return body
    
  code = '''
{prelude}
{body}

def {fname}_st(df):
  return {fname}({params})

def inputs():
  return {in_list}

def output():
  return "{out_name}"

def func_name():
  return "{fname}"

'''.format(prelude = impts if not child else '',
           body = body,
           fname = fname,
           params = ', '.join(params),
           in_list = sorted(inputs),
           out_name = out_name)
  return code
