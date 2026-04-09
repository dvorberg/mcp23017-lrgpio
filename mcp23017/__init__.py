"""
Access a MCP23017 “IO Expander” through the i2c wrapper provided
by [rgpio](http://abyz.me.uk/lg/py_lgpio.html) or
[lgpio](http://abyz.me.uk/lg/py_rgpio.html).

This is a learning project of mine to understand I2C programming
better, and an API design exercise. I plan to use this in “production”
on my model railway, but I will only test it is as far as I use
it. Your milage may vary. Patches welcome.

The MCP23017 “GPIO Expander” is interfaced in IOCON.BANK = 0
mode. This mode allows read and write operations to single byte
registers to access two banks (A and B) of eight GPIOs each.

There are two submodules:
* The `mcp23017.abc` module provides abstract base classes for proper typing.
* The `mcp23017.mcp23017` module contains the stuff that actually matters.
"""

# Import the user-facing interface for convenience. 
from .mcp23017 import Expander, Bank, Pin

# These may be imported from here to convenience. 
from i2cutils.bitpattern import ByteSpec, Byte

