import time
import lgpio as sbc

from mcp23017 import Expander


expander = Expander(sbc, 1, 0x20)

def write_test_pin_config():
    # This is not very efficient, but good for testing.

    # Set the first four pins of bank B to output. 
    for a in range(4):
        expander.bank_b[a].iodir_is_input = False
        expander.bank_b[a].write(False)

    last = None
    while True:
        for a in range(4):
            print(a)

            if last is not None:
                # Turn of the light that burns.
                expander.bank_b[last].write(False)

            expander.bank_b[a].write(True)

            last = a                
            time.sleep(.5)

write_test_pin_config()            
