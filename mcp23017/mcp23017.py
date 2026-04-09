#!/usr/bin/env python3

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

### Overview

* The `Expander` class provides connectivity and access to the Expander’s
  banks of eight GPIOs each, `bank_a` and `bank_b`. The `Expander` class
  provides several boolean configuration parameters that are written to
  the IOCON register, the most relevant of which are `mirror_interrupts`
  and `interrupt_polarity`. 
* The `Bank` class procides access to the bank’s configuration registers
  through properties (`iodir_is_input`, `input_polarity_is_reversed`,
  `interrupt_on_change`, `default_comparison_values`,
  `interrupt_compare_to_default`, `internal_pull_up_is_active`,
  `interrupt_flags`, `interrupt_captured`, `gpios`, `output_latches`) and
  also `read()` and `write()` methods that set and get GPIO bin status
  as one would expect. A `Bank` acts like an eight-tuple of `Pin`s. The
  register properties correspond to the actual registers. The datasheet
  is quoted extensively below to document them. 
* The `Pin` class represents a pin on a bank and allows read() and write()
  as one might expect. The class also provides access to the Pin’s Bank
  configuration registers. All values will go through the `Register`s on the
  corresponding `Bank` and will trigger i2c read and/or write operations,
  if needed. 
* The `Byte` class subclasses int and provides helper functions to read
  and manipulate single bits. You will interact with registers on the banks
  almost exclusively through this class. Everything should be
  self-explainatory, though.
* The (`Cached`-, `ReadOnly`-) `Register` classes and the (`ReadOnly`-)
  `PinConfig` classes implement Python’s property protocol to facilitate
  access to the device’s configuration and data. It is in the `Register`
  class that the only calls to i2c IO functions are actually made. There
  are exactly two lines in this program where this happens, one for reading
  (in `__get__()`) and one for writing (in `__set__()`). 

The [MCP23017
datasheet](https://ww1.microchip.com/downloads/en/devicedoc/20001952c.pdf)
is quoted extensively below, explaing the configuration registers. For
the somewhat complex dependencies between the registers governing
interrupt operation, I refer you to that document. The registers to
controll the internal pull-up resistors and logical pin reversal are
easily understood. In many contexts in which I use the device, this
saves me resistors and soldering. Nice!
"""

from i2cutils.bitpattern import ByteSpec, Byte
from i2cutils.device import SBC, Device

from .abc import Expander, Bank, Pin

# TABLE 3-5: CONTROL REGISTER SUMMARY (IOCON.BANK = 0)
# The “B” version of each bank register is the A-number + 1.
IODIRA   = 0x00
IPOLA    = 0x02
GPINTENA = 0x04
DEFVALA  = 0x06
INTCONA  = 0x08
IOCONA   = 0x0A
GPPUA    = 0x0C
INTFA    = 0x0E
INTCAPA  = 0x10
GPIOA    = 0x12
OLATA    = 0x14

class ConfigurationBit(object):
    """
    The MCP23017’s IOCON register allows for configuration of the
    device through seven bit settings. This class implements Python’s
    property protocol to make these available as boolean properties of
    the `Expander` class. They are accessed through the `configuration`
    `Register` of the expander’s `bank_a`. Since the IOCON register is
    shared between the banks, this doesn’s make any difference
    (cf. the datasheet under 3.5).
    """
    def __init__(self, bitno:int):
        self._bitno = bitno

    def __set__(self, expander:Expander, value:bool):
        old = expander.bank_a.configuration
        expander.bank_a.configuration = old.set_bit_to(self._bitno, value)

    def __get__(self, expander:Expander, owner:object) -> bool:
        return expander.bank_a.configuration[self._bitno]
        
class Expander(Expander):
    """
    A MCP23017 in IOCON.BANK = 0 mode. This mode allows read and write
    operations to single byte registers to access two banks (A and B)
    of eight GPIOs each. 
    """    
    def __init__(self, sbc:SBC, i2c_bus:int, address:int):
        """
        Args:
            sbc: Either the lgpio module, a rgpio.sbc instance or a
                wrapper thereof.
            i2c_bus: Bus number
            address: The device’s address on that bus. 
        """
        super().__init__(sbc, i2c_bus, address)
        
        self.bank_a = Bank(self, 0)
        self.bank_b = Bank(self, 1)
        
    # 3.5.6 CONFIGURATION REGISTER
    bank:bool = ConfigurationBit(7)
    """\
    The BANK bit changes how the registers are mapped
    (see Tables 3-4 and3-5 for more details).

    Controls how the registers are addressed<br>
    1 = The registers associated with each port are separated into
        different banks.<br>
    0 = The registers are in the same bank (addresses are sequential).
    
    **You don’t want to use this. This class assumes BANK=0.**
    """
    
    mirror_interrupts:bool = ConfigurationBit(6)
    """\
    The MIRROR bit controls how the INTA and INTB pins
    function with respect to each other.
    * When MIRROR = 1, the INTn pins are functionally
      OR’ed so that an interrupt on either port will cause
      both pins to activate.
    * When MIRROR = 0, the INT pins are separated.
      Interrupt conditions on a port will cause its
      respective INT pin to activate.

    INT Pins Mirror bit<br>
    1 = The INT pins are internally connected<br>
    0 = The INT pins are not connected. INTA is associated with PORTA
      and INTB is associated with PORTB.
    """

    sequential_operation:bool = ConfigurationBit(5)
    """\
    The Sequential Operation (SEQOP) controls the incrementing
    function of the Address Pointer. If the address pointer is
    disabled, the Address Pointer does not automatically increment
    after each byte is clocked during a serial transfer. This feature
    is useful when it is desired to continuously poll (read) or modify
    (write) a register.

    Sequential Operation mode bit<br>
    1 = Sequential operation disabled, address pointer does not increment.<br>
    0 = Sequential operation enabled, address pointer increments.
    """

    slew_rate:bool = ConfigurationBit(4)
    """
    The Slew Rate (DISSLW) bit controls the slew rate
    function on the SDA pin. If enabled, the SDA slew rate
    will be controlled when driving from a high to low.

     Slew Rate control bit for SDA output<br>
    1 = Slew rate disabled<br>
    0 = Slew rate enabled
    """

    enable_hardware_address:bool = ConfigurationBit(3)
    """
    The Hardware Address Enable (HAEN) bit
    enables/disables hardware addressing on the
    MCP23S17 only. The address pins (A2, A1 and A0)
    must be externally biased, regardless of the HAEN bit
    value.
    
    If enabled (HAEN = 1), the device’s hardware address
    matches the address pins.
    
    If disabled (HAEN = 0), the device’s hardware address
    is A2 = A1 = A0 = 0.

    HAEN: Hardware Address Enable bit (MCP23S17 only) (Note 1)<br>
    1 = Enables the MCP23S17 address pins.<br>
    0 = Disables the MCP23S17 address pins.
    """

    interrupt_is_open_drain:bool = ConfigurationBit(2)
    """
    The Open-Drain (ODR) control bit enables/disables the
    INT pin for open-drain configuration. Setting this bit
    overrides the INTPOL bit.

    Configures the INT pin as an open-drain output<br>
    1 = Open-drain output (overrides the INTPOL bit.)<br>
    0 = Active driver output (INTPOL bit sets the polarity.)
    """

    interrupt_polarity:bool = ConfigurationBit(1)
    """
    The Interrupt Polarity (INTPOL) sets the polarity of the
    INT pin. This bit is functional only when the ODR bit is
    cleared, configuring the INT pin as active push-pull.

     This bit sets the polarity of the INT output pin<br>
     1 = Active-high<br>
     0 = Active-lo
     """

class Register(object):
    """
    A configuration register on the MCP23017.

    This class implements Python’s property protocol. 
    
    Setting triggers a write operation, getting a read operation.
    """
    def __init__(self, register_a:int):
        """
        Args:
            register_a: The register’s number for the A bank.
               B is that number +1.
        """
        self.register_a = register_a
        
    def __set_name__(self, owner:object, name:str):
        self._name = name

    def __get__(self, bank:Bank, owner:object) -> Byte:
        return Byte(bank.expander.read_byte_data(
            self.register_a + bank.bank_no))

    def __set__(self, bank:Bank, value:ByteSpec):
        value = Byte(value)
        bank.expander.write_byte_data(
            self.register_a + bank.bank_no, value)
        return value

class CachedRegister(Register):
    """
    This is meant for configuration registers. We assume exclusive
    access to the chip. We cache configuration values written and
    return them as current values if requested. If no value has been
    written, yet, current values are read from the chip.
    """
    def __get__(self, bank:Bank, owner:object) -> Byte:
        ret = self.get_cache(bank)
        if ret is None:
            ret = super().__get__(bank, owner)
            self.set_cache(bank, ret)
        return Byte(ret)

    def __set__(self, bank:Bank, value:ByteSpec):
        value = super().__set__(bank, value)
        self.set_cache(bank, value)
        
    @property
    def _cache_name(self):
        return f"_{self._name}_cache"
    
    def get_cache(self, bank:Bank):
        return getattr(bank, self._cache_name, None)

    def set_cache(self, bank:Bank, value:int):
        setattr(bank, self._cache_name, value)

class ReadOnlyRegister(Register):
    """
    This is regular (non-cached) register we cannot write to. 
    """
    def __set__(self, bank:Bank, owner:object) -> Byte:
        raise IOError("Register is read-only.")
        
class Bank(Bank):
    """
    In IOCON.BANK=0 mode MCP23017 has two banks of eight GPIOs each. 
    """
    def __init__(self, expander:Expander, bank_no:int):
        """
        Args:
            expander: The IO Expander we belong to.
            bank_no: 0 for bank A, 1 for bank B.
        """
        self._expander = expander
        self._bank_no = bank_no

    @property
    def expander(self) -> Expander:
        return self._expander

    @property
    def bank_no(self) -> int:
        return self._bank_no
        
    def read(self) -> Byte:
        """
        Use the GPIOx register to read the bank. 
        """
        return self.gpios
        
    def write(self, value:Byte):
        """
        Write the byte pattern to the OLATx (output latch) register. 
        """
        self.output_latches = value

    def __getitem__(self, idx:int):
        """
        Provide subscript syntax for the pins. The bank acts like
        a tuple of eight Pin objects, see below. 
        """
        assert 0 <= idx < 8, IndexError
        return Pin(self, idx)

    # Properties. To configure a whole IO bank, set to a Byte value.

    iodir_is_input: Byte = CachedRegister(IODIRA)
    """\
    3.5.1 I/O DIRECTION REGISTER (IODIRx `Register`)
    
    Controls the direction of the data I/O. When a bit is set, the
    corresponding pin becomes an input. When a bit is clear, the
    corresponding pin becomes an output.
    """
    
    input_polarity_is_reversed: Byte = CachedRegister(IPOLA)
    """\
    3.5.2 INPUT POLARITY REGISTER (IPOLx `Register`)
    
    This register allows the user to configure the polarity on the
    corresponding GPIO port bits.
    If a bit is set, the corresponding GPIO register bit will reflect the
    inverted value on the pin. 
    """

    interrupt_on_change: Byte = CachedRegister(GPINTENA)
    """\
    3.5.3 INTERRUPT-ON-CHANGE CONTROL REGISTER (GPINTENx `Register`)
    
    The GPINTEN register controls the interrupt-on-change feature for each
    pin.

    If a bit is set, the corresponding pin is enabled for interrupt-on-change.
    The DEFVAL and INTCON registers must also be configured if any pins are
    enabled for interrupt-on-change.
    """

    default_comparison_values: Byte = CachedRegister(DEFVALA)
    """\
    3.5.4 DEFAULT COMPARE REGISTER FOR INTERRUPT-ON-CHANGE (DEFVALx `Register`)
    
    The default comparison value is configured in the DEFVAL register. If
    enabled (via GPINTEN and INTCON) to compare against the DEFVAL register,
    an opposite value on the associated pin will cause an interrupt to occur.
    """

    interrupt_compare_to_default: Byte = CachedRegister(INTCONA)
    """\
    3.5.5 INTERRUPT CONTROL REGISTER (INTCONx `Register`)
    
    The INTCON register controls how the associated pin value is compared
    for the interrupt-on-change feature. If a bit is set, the corresponding
    I/O pin is compared against the associated bit in the DEFVAL register.
    If a bit value is clear, the corresponding I/O pin is compared against
    the previous value.
    """

    configuration = CachedRegister(IOCONA)
    """\
    3.5.6 CONFIGURATION REGISTER (IOCON `CachedRegister`)

    This register is shared between the two ports (banks), cf. to the
    datasheet under 3.5.

    It is set by the `ConfigurationBit` properties of the `Expander`
    cass. 
    """
    
    internal_pull_up_is_active: Byte = CachedRegister(GPPUA)
    """\
    3.5.7 PULL-UP RESISTOR CONFIGURATION REGISTER (GPPUx `Register`)
    
    The GPPU register controls the pull-up resistors for the port pins.
    If a bit is set and the corresponding pin is configured as an input,
    the corresponding port pin is internally pulled up with a 100
    kΩ resistor.
    """
    
    interrupt_flags: Byte = ReadOnlyRegister(INTFA)
    """\
    3.5.8 INTERRUPT FLAG REGISTER (INTFx `Register`)
    
    The INTF register reflects the interrupt condition on the port pins of
    any pin that is enabled for interrupts via the GPINTEN register. A set
    bit indicates that the associated pin caused the interrupt.
    
    This register is read-only. Writes to this register will be ignored.
    """

    interrupt_captured: Byte = ReadOnlyRegister(INTCAPA)
    """\
    3.5.9 INTERRUPT CAPTURED REGISTER (INTCAPx `Register`)
    
    The INTCAP register captures the GPIO port value at the time the
    interrupt occurred. The register is read-only and is updated only when
    an interrupt occurs. The register remains unchanged until the interrupt
    is cleared via a read of INTCAP or GPIO.
    """

    gpios: Byte = Register(GPIOA)
    """\
    3.5.10 PORT REGISTER (GPIOx `Register`)
    
    The GPIO register reflects the value on the port. Reading from this
    register reads the port. Writing to this register modifies the Output
    Latch (OLAT) register.
    """

    output_latches: Byte = CachedRegister(OLATA)
    """\
    3.5.11 OUTPUT LATCH REGISTER (OLATx `Register`)
    
    The OLAT register provides access to the output latches. A read from
    this register results in a read of the OLAT and not the port itself.
    A write to this register modifies the output latches that modifies the
    pins configured as outputs.
    """

class PinConfig(object):
    """
    A bit of a configuration register.

    This class implements Python’s property protocol. 
    
    Each change will trigger a (cached) read from the register and a
    write. To change multiple bits in a register use the registers
    directly.
    """
    def __set_name__(self, pin:Pin, name:str):
        """
        The name of the Pin’s boolean property must correspond to the
        (Cached or ReadOnly) Register in the Bank class. This is hard coded
        here. The Bank class may use plural.

        BTW: This is not an efficiancy issue. This constructor is called at
        import time.

        Raises:
           NameError: If the Bank class does not contain a corresponding
               register.
        """
        for n in (name, name + "s", name + "es",):
            if n in Bank.__dict__:
                self.register = Bank.__dict__[n]
                break
        else:
            raise NameError(repr(name))

    def __get__(self, pin:Pin, owner:object) -> bool:
        return bool(self.register.__get__(pin.bank, pin) & pin.mask)

    def __set__(self, pin:Pin, value:bool):
        old = self.register.__get__(pin.bank, pin)
        self.register.__set__(pin.bank, old.set_bit_to(pin.no, value))

class ReadOnlyPinConfig(object):
    def __set__(self, pin:Pin, value:Byte):
        raise IOError("Register is read only (trying to modify pin config.")
        
class Pin(Pin):
    """
    Model one GPIO pin. Each change to any of the configuration
    parameters will cause bank configuration registers to be written.
    Changes to multiple paramters are performed more efficiently by changing
    bank registers. 
    """
    def __init__(self, bank:Bank, no:int):
        self._bank = bank
        self._no = no
        self._mask = (0x1 << no)

    @property
    def bank(self) -> Bank:
        return self._bank

    @property
    def no(self) -> int:
        return self._no
    
    @property
    def mask(self) -> int:
        return self._mask

    def read(self) -> bool:
        return bool(self._bank.gpios & self._mask)

    def write(self, value:bool|int):
        self._bank.gpios = self._bank.gpios.set_bit_to(
            self._no, bool(value))

    iodir_is_input:bool = PinConfig()
    "IODIRx `Register` bit for this pin"
    
    input_polarity_is_reversed:bool = PinConfig()
    "IPOLx `Register` bit for this pin"
    
    interrupt_on_change:bool = PinConfig()
    "GPINTENx `Register` bit for this pin"
    
    default_comparison_value:bool = PinConfig()
    "DEFVALx `Register` bit for this pin"
    
    interrupt_compare_to_default:bool = PinConfig()
    "INTCONx `Register` bit for this pin"
    
    internal_pull_up_is_active:bool = PinConfig()
    "GPPUx `Register` bit for this pin"
    
    interrupt_flag:bool = ReadOnlyPinConfig()
    "INTFx `Register` bit for this pin"
    
    interrupt_captured:bool = ReadOnlyPinConfig()
    "INTCAPx `Register` bit for this pin"
    
    output_latch:bool = PinConfig()
    "OLATx `Register` bit for this pin"

