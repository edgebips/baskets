from . import vanguard
from . import ishares
from . import powershares
from . import spdr
from . import americanfunds

MODULES = {'Vanguard': vanguard,
           'iShares': ishares,
           'PowerShares': powershares,
           'StateStreet': spdr,
           'AmericanFunds': americanfunds}
