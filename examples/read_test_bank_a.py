import time
import lgpio as sbc

from mcp23017 import Expander

expander = Expander(sbc, 1, 0x20)

def read_test_bank_a():
    # Set all pins on bank_a to input. 
    expander.bank_a.iodir_is_input = True

    # Activate the weak pull-up registers on all A-side GPIOs.
    expander.bank_a.internal_pull_up_is_active = True

    # Invert (logical) polarity of the A side.
    expander.bank_a.pin_polarity_is_reversed = True

    last = None
    while True:
        for a in range(8):
            t = time.time()
            result = expander.bank_a.read()
            d = time.time()-t
            if result != last:
                print("{0:08b} {1:.4f}".format(result, d)) # , end="\r"
            last = result
            time.sleep(.5)

read_test_bank_a()  


