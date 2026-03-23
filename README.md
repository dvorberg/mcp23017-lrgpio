Access a MCP23017 “IO Expander” through the i2c wrapper provided by
rgpio or lgpio.

This is a learning project of mine. I want to understand I2C programming
better. It is also an API design exercise. 

I plan to use this in “production” on my model railway, but I will
only test it is as far as I use it. Your milage may vary.

* [API Reference](https://dvorberg.github.io/mcp23017-lrgpio/mcp23017.html) 
* [MCP23017 datasheet](https://ww1.microchip.com/downloads/en/devicedoc/20001952c.pdf)
* A hopefully growing number of examples in `examples/`. 

```python
# I hooked up the MCP23017 to my Raspberry Pi and I have four
# switches connecting four lower number pins of the A bank to GND. 

import lgpio as sbc

from mcp23017 import Expander

def read_test_bank_a():
    expander = Expander(sbc, 1, 0x20)
    
    # Set the lower four pins on bank_a to input. 
    expander.bank_a.iodir_is_input = 0b00001111

    # Activate the weak pull-up registers on all A-side GPIOs.
    expander.bank_a.internal_pull_up_is_active = True

    # Invert (logical) polarity of the relevant pins.
    expander.bank_a.pin_polarity_is_reversed = 0b00001111

    last = None
    while True:
        for a in range(8):
            t = time.time()
            result = expander.bank_a.read()
            d = time.time()-t
            if result != last:
                print("{0:08b} {1:.4f}".format(result, d))
            last = result
            time.sleep(.5)

read_test_bank_a()  
```
