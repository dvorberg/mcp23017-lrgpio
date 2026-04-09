import time, signal
import lgpio as sbc

gpio = 23
def main():
    handle = sbc.gpiochip_open(0)
    sbc.gpio_claim_input(handle, gpio, sbc.SET_PULL_UP)

    old = None
    while True:
        value = sbc.gpio_read(handle, gpio)
        if value != old:
            print(value)
        time.sleep(.5)
        old = value
        
    # Make the program terminate nicely on Ctrl-C.
    def signal_handler(sig, frame):
        sbc.gpio_free(handle, gpio)
        sbc.gpiochip_close(handle)
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.pause()
        
main()        
    
