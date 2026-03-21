import time
import lgpio as sbc

from mcp23017 import Expander

expander = Expander(sbc, 1, 0x20)

def write_test_bank_register():
    # Set the first four pins of bank B to output. 
    expander.bank_b.iodir_is_input = 0xf0

    while True:
        for a in range(4):
            bits = 0x01 << a
            print("{0:08b}".format(bits))
            expander.bank_b.gpios = bits
            time.sleep(.5)

write_test_bank_register()            

