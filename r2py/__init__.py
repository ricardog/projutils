import inflection


def pythonify(mod):
    # Convert variable names to valid pythin identifiers.  Converts
    # CamelCase to snake_case as a by-product.
    def nodots(root):
        if isinstance(root, str):
            return inflection.parameterize(inflection.underscore(root), "_")
        return root

    syms = mod.hstab
    if not syms:
        return
    mod.equation.transform(nodots)
    return
