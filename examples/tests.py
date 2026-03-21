if __name__ == "__main__":
    import time
    import lgpio as sbc
    
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
        
                
    # write_test_bank_register()
    #write_test_pin_config()
    read_test_bank_a()  

    
