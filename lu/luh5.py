
LU = {'primary': 'primf + primn',
      'secondary': 'secdf + secdn',
      'cropland': 'c3ann + c4ann + c3nfx',
      'pasture': 'pastr + range',
      'urban': 'urban',
      'plantation_pri': 'c3per + c4per',
      'plantation_sec': '0',
}

LUp3 = {'primary': 'primf + primn',
        'young_secondary': 'secdy',
        'intermediate_secondary': 'secdi',
        'mature_secondary': 'secdm',
        'cropland': 'c3ann + c4ann + c3nfx',
        'pasture': 'pastr + range',
        'urban': 'urban',
        'plantation_pri': 'c3per + c4per',
        'plantation_sec': '0',
}

def types(plus3=False):
  if plus3:
    return sorted(LUp3.keys())
  return sorted(LU.keys())
