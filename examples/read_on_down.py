import sys, signal, time, argparse
import lgpio as sbc

import icecream; icecream.install()

from mcp23017 import Expander

"""
** Rasberry Pi**
* The MCP23017 is connected to the Pi’s 3.3V pin and GND.
* I2C SDA and SCL are connected correctly.
* I connect the INTA pin to GPIO #25 (BCM numbering) through a 10kΩ resistor. 

**Setup MCP23017**
* It is configured on address 0 by connecting all address pins to GND.
* The RESET pin is conntected to 3.3V through a 10kΩ resistor.

I have several free cables to connect various BANK A pins to GND
to wire bit patterns. 

"""

def parse_int(s):
    if s.startswith("0x"):
        return int(s[2:], 16)
    else:
        return int(s)

def read_on_interrupt():
    parser = argparse.ArgumentParser(description=__doc__)

    parser.add_argument("--i2c-bus", "-b", type=int, default=1,
                        help="i2c bus. Defaults to 1 for most models "
                        "of Raspberry Pis. On older models it’s 0.")
    parser.add_argument("--i2c-address", "-a", type=parse_int,
                        default=0x20,
                        help="i2c address. Defaults to 0x20.")
    parser.add_argument("--interrupt-pin", "-p", type=int, default=23,
                        help="GPIO pin on the Pi (in BCM numbering)")
    parser.add_argument("--bank", "-B", choices=("a", "b",), default="a",
                        help="MPC23017’s bank, a or b")

    args = parser.parse_args()
    
    expander = Expander(sbc, args.i2c_bus, args.i2c_address)

    if args.bank == "a":
        bank = expander.bank_a
    else:
        bank = expander.bank_b
    
    # Set all pins on bank_a to input. 
    bank.iodir_is_input = True

    # Activate the weak pull-up registers on all A-side GPIOs.
    bank.internal_pull_up_is_active = False

    # Invert (logical) polarity of the A side.
    bank.input_polarity_is_reversed = False

    # Leaving the pin blank will read as 0 now,
    # connecting it to GND will read as 1. 
    
    # All pins on BANK A will set the interrupt on change. 
    bank.interrupt_on_change = True

    # Set the interrupt pin’s polarity to 0 (False) to indicate
    # an active interrupt through a LOW state.
    expander.interrupt_polarity = False


    # The rpi-lgpio library provided a wrapper (sans i2c) for this
    # functionality. I’m using lgpio directly here for learning
    # purposes.
    
    # Set up the Pi’s GPIO.
    handle = sbc.gpiochip_open(0)
    
    def on_interrupt(chip, gpio, level, timestamp):
        byte = bank.read()
        for bit in reversed(byte):
            if bit:
                b = "X"
            else:
                b = "•"
            print(b, end=" ")
        print()
        
    sbc.gpio_claim_alert(handle, args.interrupt_pin, sbc.FALLING_EDGE)
    callback = sbc.callback(handle, args.interrupt_pin,
                            sbc.FALLING_EDGE, on_interrupt)

    on_interrupt(None, None, None, None)
    
    # Make the program terminate nicely on Ctrl-C.
    def signal_handler(sig, frame):
        sbc.gpio_free(handle, args.interrupt_pin)
        sbc.gpiochip_close(handle)
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.pause()
    

read_on_interrupt()  


