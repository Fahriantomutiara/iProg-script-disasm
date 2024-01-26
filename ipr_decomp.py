from listing import Listing

io_host = {
    0: 'PBMAX',
    1: 'PBPOS',
    2: 'PIN_TEST_WINDOW',
    3: 'PIN_TEST_RESULT',
    33: 'WINDOW',
    69: 'SW_VERSION',
    70: 'DEVICE_SERIAL',
    71: 'OPEN_FILE_DIALOG',
    72: 'SAVE_FILE_DIALOG',
}

io_device = {
    0: 'PORTA',
    1: 'PORTB',
    2: 'PORTC',
    3: 'PORTD',
    4: 'PORTE',
    5: 'TIMER',
    6: 'UART_DATA',
    7: ('VM_ID', 'UART_CR'),  # in / out
    8: 'UART_MR',
    9: 'UART_BRGR',
    10: 'USB',
    11: 'USB_WAIT',
    12: 'USB16',
    13: 'USB16_WAIT',
    14: 'USB32',
    15: 'USB32_WAIT',
    16: 'POWER',
    17: 'SPI_CR',
    18: 'SPI_DATA32',
    19: 'SPI_DATA8',
    20: 'ADC_CR',
    21: 'ADC_SR',
    22: 'ADC_DATA0',
    23: 'ADC_DATA1',
    24: ('ADC_DATA2', 'I2C_PINS'),  # in / out
    25: 'ADC_DATA3',
    26: 'IDLE_ENABLE',
    27: 'TIMER2',
    28: 'PWM0',
    29: 'PWM1',
    30: 'PWM2',
    31: 'IRQ_FLAG',
    32: 'IRQ_ENABLE',

    34: 'FAST_TIMER',
    35: 'CAPT_VALUE',
    36: 'CAPT_CLOCK',
    37: ('CAPT_VALUE2', 'TIMER_ENABLE'),
    38: 'SPI_DATA16',
    39: 'SPI_DATA24',
    40: ('RANDOM', 'CAPT_MODE'),
    41: 'CAPT_TIMER',
    42: 'FAST_TIMER_CLOCK',

    50: 'CAPT_INTERVAL0',
    51: 'CAPT_INTERVAL1',
    52: 'CAPT_INTERVAL2',
    53: 'CAPT_INTERVAL3',
    54: 'CAPT_INTERVAL4',
    55: 'CAPT_INTERVAL5',
    56: 'CAPT_INTERVAL6',
    57: 'CAPT_INTERVAL7',
    58: 'CAPT_INTERVAL8',
    59: 'CAPT_INTERVAL9',
    60: 'BDM_ENABLE',
    61: 'BDM_TIMES',
    62: 'BDM_DATA_8',
    63: 'BDM_DATA_16',
    64: 'BDM_DATA_32',
    65: 'I2C_DATA',
    66: 'ESPI_CONFIG',
    67: 'ESPI_DATA8',
    68: 'ESPI_DATA16',
    69: 'ESPI_DATA32',
    70: 'I2C_DATA_ACK',
    71: 'I2C_ACK',
    72: 'PWM0_RUN',
    73: 'PWM0_PULSE',
    74: 'PULSE_35080',
    75: 'PORTA_PULSE',
    76: 'PWM_PULSE',

    77: 'SOUND',

    253: 'USB_INT',
    254: 'WRITE_ENABLE',
    255: 'SERIAL',

    # 21: 'BDM_SYNC_PULSE',
    # 22: 'BDM_CLOCK',
    # 23: 'BDM_MULT',
    # 28: 'SPI_CSR',
    # 29: 'DBG1',
    # 30: 'DBG2',
    # 54: 'PULSE2_35080',
    # 64: 'BDM_SYNC',
    # 65: 'ESIZE1',
    # 66: 'ESIZE2',
    # 67: 'ESIZE3',
    # 68: 'FILEEXISTS',
    # 71: 'ER35080',
    # 72: 'DDEVICE_SERIAL',
    # 77: 'PWM_DIRECT',
    # 200: 'DBGA'
}


def get_io_name(listing, io_id, output):
    io_names = io_host if listing.dis.is_host() else io_device
    if io_id in io_names:
        io = io_names[io_id]
        return io if isinstance(io, str) else io[output]
    else:
        return str(io_id)


def set_device_label(listing, ea, name, comment=None):
    if 'device_labels' in listing.dis.presets:
        listing.dis.presets['device_labels'].append((ea, name, comment))


def add_global_emem_var(listing, emem_var, emem_idx):
    emem = (emem_var, emem_idx)
    if emem not in listing.dis.presets['global']['emem']:
        listing.dis.presets['global']['emem'].append(emem)


def add_global_str_idx(listing, str_idx):
    if str_idx not in listing.dis.presets['global']['string']:
        listing.dis.presets['global']['string'].append(str_idx)


def decompile(listing: Listing, ea):

    if 'b' in listing.type(ea):
        # skip bad functions
        return

    line = listing.line(ea)
    while True:

        if 'P' in line.type and line.ea != ea:  # конец ф-ии
            break

        # begin proc
        if line.instruction == 'PUSHR':
            line2 = line.next()
            if line2.instruction == 'ENTER':
                v = ', '.join([f'R{a}' for a in range(line2.arg(0))])
                line.set_comment(f'proc {line.name}({v}){{')
                # Typically the last one register is used as an unnamed variable.
                v = ', '.join([f'R{a + line2.arg(0)}' for a in range(line2.arg(1) - line2.arg(0) - 1)])
                if v:
                    line2.set_comment(f'var {v};')
                line = line2.next()
                continue

        #
        # for((const)_init_;(const)_cond_;_incr_){} instruction
        if line.instruction in ['LDB', 'LDW', 'LDD'] and line.arg_type(0) == 'r':
            line2 = line.next()
            if line2.instruction in ['LDB', 'LDW', 'LDD'] and line2.arg_type(0) == 'r':
                line3 = line2.next()
                if line3.instruction[:4] == 'CMPJ' and line3.arg(0) == line.arg(0) and line3.arg(1) == line2.arg(0):
                    ncond = {'E': '!=', 'NE': '=', 'GE': '<', 'LE': '>', 'L': '>=', 'G': '<='}.get(
                        line3.instruction[4:], '??')

                    if line2.name:
                        line3.set_comment(f'for ({line.arg_str(0)} = {line.arg_str(1)}; '
                                          f'{line.arg_str(0)} {ncond} {line2.arg_str(1)}; _incr_) {{')
                        line.set_comment('_init_')
                        line2.set_comment('_cond_')
                    else:
                        line3.set_comment(f'if ({line3.arg_str(0)} {ncond} {line3.arg_str(1)}) {{')
                        line = line3.next()
                        continue

                    linee = line3.next()
                    lineincr = None
                    while 'P' not in linee.type:
                        if linee.instruction == 'JMP' and linee.arg(0) == line2.ea and linee.next().ea == line3.arg(
                                2):
                            if lineincr is not None:
                                lineincr.set_comment('_incr_')
                            linee.set_comment('}')
                            break

                        elif linee.instruction == 'JMP' and linee.arg(0) == line2.ea:
                            linee.set_comment('  continue;')

                        elif linee.instruction == 'JMP' and linee.arg(0) == line3.arg(2):
                            linee.set_comment('  break;')

                        lineincr = linee
                        linee = linee.next()

                    line = line3.next()
                    continue

        #
        # for((const)_init_;(var)_cond_;_incr_){} instruction
        if line.instruction in ['LDB', 'LDW', 'LDD'] and line.arg_type(0) == 'r':
            line2 = line.next()
            if line2.instruction[:4] == 'CMPJ' and line2.arg(0) == line.arg(0):
                ncond = {'E': '!=', 'NE': '=', 'GE': '<', 'LE': '>', 'L': '>=', 'G': '<='}.get(
                    line2.instruction[4:], '??')

                if line2.name:
                    line2.set_comment(f'for ({line.arg_str(0)} = {line.arg_str(1)}; '
                                      f'{line2.arg_str(0)} {ncond} {line2.arg_str(1)}; _incr_) {{')
                    line.set_comment('_init_')
                else:
                    line2.set_comment(f'if ({line2.arg_str(0)} {ncond} {line2.arg_str(1)}) {{')
                    line = line2.next()
                    continue

                linee = line2.next()
                lineincr = None
                while 'P' not in linee.type:
                    if linee.instruction == 'JMP' and linee.arg(0) == line2.ea and linee.next().ea == line2.arg(2):
                        if lineincr is not None:
                            lineincr.set_comment('_incr_')
                        linee.set_comment('}')
                        break

                    elif linee.instruction == 'JMP' and linee.arg(0) == line2.ea:
                        linee.set_comment('  continue;')

                    elif linee.instruction == 'JMP' and linee.arg(0) == line2.arg(2):
                        linee.set_comment('  break;')

                    lineincr = linee
                    linee = linee.next()

                line = line2.next()
                continue

        #
        # if
        if line.instruction[:4] == 'CMPJ':
            ncond = {'E': '!=', 'NE': '=', 'GE': '<', 'LE': '>', 'L': '>=', 'G': '<='}.get(line.instruction[4:],
                                                                                           '??')
            line.set_comment(f'if ({line.arg_str(0)} {ncond} {line.arg_str(1)}) {{')
            line = line.next()
            continue

        if line.instruction[:4] == 'CPIJ':
            ncond = {'E': '!=', 'NE': '='}.get(line.instruction[4:], '??')
            line.set_comment(f'if ({line.arg_str(0)} {ncond} {line.arg_str(1)}) {{')
            line = line.next()
            continue

        if line.instruction == 'JZ':
            line.set_comment(f'if ({line.arg_str(0)}) {{')
            line = line.next()
            continue

        if line.instruction == 'JNZ':
            line.set_comment(f'if ({line.arg_str(0)}=0) {{')
            line = line.next()
            continue

        if line.instruction == 'JBRC':
            line.set_comment(f'if ({line.arg_str(0)} & 0x{1 << line.arg(1):02x}) {{')
            line = line.next()

        if line.instruction == 'JBRS':
            line.set_comment(f'if (({line.arg_str(0)} & 0x{1 << line.arg(1):02x}) = 0) {{')
            line = line.next()

        #
        #
        if line.instruction == 'IN':
            r = line.arg_str(0)
            a = line.arg(1)
            io = get_io_name(listing, a, False)
            line.set_comment(f'{r} = {io};')
            line = line.next()
            continue

        #
        #
        if line.instruction == 'OUT':
            a = line.arg(0)
            r = line.arg_str(1)
            io = get_io_name(listing, a, True)
            line.set_comment(f'{io} = {r};\n')
            line = line.next()
            continue

        if line.instruction == 'ORPI':
            a = line.arg(0)
            io = get_io_name(listing, a, True)
            r = line.arg(1)
            line.set_comment(f'{io} |= 0x{r:x};')
            line = line.next()
            continue

        if line.instruction == 'ANDPI':
            a = line.arg(0)
            io = get_io_name(listing, a, True)
            r = line.arg(1)
            line.set_comment(f'{io} &= 0x{r ^ 255:x} ^ 255;')
            line = line.next()
            continue

        if line.instruction == 'JNZIO':
            a = line.arg(0)
            io = get_io_name(listing, a, False)
            line.set_comment(f'if ({io} = 0) {{\n')
            line = line.next()
            continue

        # if line.instruction == 'JZIO':
        #     a = line.arg(0)
        #     io = get_io_name(listing, a, False)
        #     line.set_comment(f'if ({io}) {{\n')
        #     line = line.next()
        #     continue

        #
        # SYS 0 -> clear temp string
        if line.instruction == 'SYS' and line.arg(0) == 0:
            line.set_comment('TMP = ""')
            line = line.next()
            continue

        #
        # SYS 2 -> global str = temp string
        if line.instruction == 'LDB' and line.arg_str(0) == 'R15':
            line2 = line.next()
            if line2.instruction == 'SYS' and line2.arg(0) == 2:
                line.set_comment('')
                line2.set_comment(f'str_{line.arg(1)} = TMP;\n')
                add_global_str_idx(listing, line.arg(1))
                line = line.next()
                continue

        #
        # SYS 13 -> put global str to temp string
        if line.instruction in ['LDB'] and line.arg_str(0) == 'R15':
            line2 = line.next()
            if line2.instruction == 'SYS' and line2.arg(0) == 13:
                line.set_comment('')
                line2.set_comment(f'TMP += str_{line.arg(1)}')
                add_global_str_idx(listing, line.arg(1))
                line = line.next()
                continue

        #
        # SYS 13 -> STREAMPIN = PORT[ABD].bit
        if line.instruction in ['LDW'] and line.arg_str(0) == 'R15':
            line2 = line.next()
            if line2.instruction == 'SYS' and line2.arg(0) == 13:
                port = 'PORT' + chr(ord('A') + (line.arg(1) >> 8))
                bit_number = len(bin(line.arg(1) & 0xFF)) - 3
                line.set_comment('')
                line2.set_comment(f'STREAMPIN = {port}.{bit_number};')
                line = line2.next()
                continue

        #
        # SYS 3 -> put int into temp string
        if line.instruction == 'MOV' and line.arg_str(0) == 'R15':
            line2 = line.next()
            if line2.instruction == 'SYS' and line2.arg(0) == 3:
                line.set_comment('')
                line2.set_comment('TMP += #i.R15')
                line = line2.next()
                continue

        if line.instruction in ['LDB', 'LDW', 'LDD'] and line.arg_str(0) == 'R15':
            line2 = line.next()
            if line2.instruction == 'SYS' and line2.arg(0) == 3:
                v = line.arg(1)
                line.set_comment('')
                line2.set_comment(f'TMP += #i.{v}')
                line = line2.next()
                continue

        if line.instruction in ['LDMB', 'LDMW', 'LDMD'] and line.arg_str(0) == 'R15':
            line2 = line.next()
            if line2.instruction == 'SYS' and line2.arg(0) == 3:
                v = line.arg_str(1)
                line.set_comment('')
                line2.set_comment(f'TMP += #i.{v}')
                line = line2.next()
                continue

        #
        # SYS 4 -> put char into temp string
        if line.instruction == 'MOV' and line.arg_str(0) == 'R15':
            line2 = line.next()
            if line2.instruction == 'SYS' and line2.arg(0) == 4:
                line.set_comment('')
                line2.set_comment('TMP += #c.R15')
                line = line2.next()
                continue

        if line.instruction in ['LDB', 'LDW', 'LDD'] and line.arg_str(0) == 'R15':
            line2 = line.next()
            if line2.instruction == 'SYS' and line2.arg(0) == 4:
                v = line.arg(1)
                line.set_comment('')
                line2.set_comment(f'TMP += #c.{v}')
                line = line2.next()
                continue

        if line.instruction in ['LDMB', 'LDMW', 'LDMD'] and line.arg_str(0) == 'R15':
            line2 = line.next()
            if line2.instruction == 'SYS' and line2.arg(0) == 4:
                v = line.arg_str(1)
                line.set_comment('')
                line2.set_comment(f'TMP += #c.{v}')
                line = line2.next()
                continue

        #
        # SYS [5,6,7,8] - > put hex into temp string
        if line.instruction == 'MOV' and line.arg_str(0) == 'R15':
            line2 = line.next()
            if line2.instruction == 'SYS' and line2.arg(0) in [5, 6, 7, 8]:
                w = line2.arg(0) - 4
                line.set_comment('')
                line2.set_comment(f'TMP += #h{w}.R15')
                line = line2.next()
                continue

        if line.instruction in ['LDMB', 'LDMW', 'LDMD'] and line.arg_str(0) == 'R15':
            line2 = line.next()
            if line2.instruction == 'SYS' and line2.arg(0) in [5, 6, 7, 8]:
                w = line2.arg(0) - 4
                v = line.arg_str(1)
                line.set_comment('')
                line2.set_comment(f'TMP += #h{w}.{v}')
                line = line2.next()
                continue

        #
        # SYS 1 -> put string into temp string
        if line.instruction == 'LDW' and line.arg_str(0) == 'R15' and line.arg_type(1) == 'd':
            line2 = line.next()
            if line2.instruction == 'SYS' and line2.arg(0) == 1:
                str_offset = line.arg(1)
                listing.setCString(str_offset)
                line.set_arg_type(1, 'o')
                comment = f'TMP += {listing.line(str_offset).arg(0)}'
                line.set_comment('')
                line2.set_comment(comment)
                line = line2.next()
                continue

        #
        # SYS 9 -> mbox(temp string, NUM)
        if line.instruction == 'ORD' and line.arg_str(0) == 'R15':
            line2 = line.next()
            if line2.instruction == 'SYS' and line2.arg(0) == 9:
                a = line.arg(1)
                lo = a & 0xFFFF
                hi = a >> 16
                line.set_comment(f'/* {a} is {hi}:{lo} */')
                line2.set_comment(f'R15 = mbox(TMP, {hi});\n')
                line = line2.next()
                continue

        #
        # SYS 12 -> print(temp string)
        if line.instruction == 'SYS' and line.arg(0) == 12:
            line.set_comment('print(TMP);\n')
            line = line.next()
            continue

        #
        # SYS 26 -> backup(temp string)
        if line.instruction == 'SYS' and line.arg(0) == 26:
            line.set_comment('backup(TMP);\n')
            line = line.next()
            continue

        #
        # SYS 15 -> label_R15 = temp string
        if line.instruction == 'LDB' and line.arg_str(0) == 'R15':
            line2 = line.next()
            if line2.instruction == 'SYS' and line2.arg(0) == 15:
                line.set_comment('')
                line2.set_comment(f'label_{line.arg(1):04X} = TMP;\n')
                line = line2.next()
                continue

        #
        # SYS 15 -> STREAMOUT(R15, R14h, R14l)
        if line.instruction in ['LDB', 'LDW', 'LDD'] and line.arg_str(0) == 'R15':
            line2 = line.next()
            if line2.instruction == 'LDD' and line2.arg_str(0) == 'R14':
                line3 = line2.next()
                if line3.instruction in ['ORB', 'ORW'] and line3.arg_str(0) == 'R14':
                    line4 = line3.next()
                    if line4.instruction == 'SYS' and line4.arg(0) == 15:
                        d = line.arg(1)
                        bit_len = line2.arg(1) >> 16
                        pulse = line3.arg(1)
                        line.set_comment('')
                        line2.set_comment(f'/* ({bit_len} << 16) */')
                        line3.set_comment('')
                        line4.set_comment(f'StreamOut({d}, {bit_len}, {pulse});\n')
                        line = line4.next()
                        continue

        if line.instruction in ['MOV', 'LDB', 'LDW', 'LDD', 'LDMD'] and line.arg_str(0) == 'R15':
            line2 = line.next()
            if line2.instruction in ['MOV', 'LDMW', 'LDMD'] and line2.arg_str(0) == 'R14':
                line3 = line2.next()
                if line3.instruction == 'RL' and line3.arg_str(0) == 'R14' and line3.arg(1) == 16:
                    line4 = line3.next()
                    if line4.instruction in ['OR', 'ORB', 'ORW', 'ORD', 'ORMW'] and line4.arg_str(0) == 'R14':
                        line5 = line4.next()
                        if line5.instruction == 'ORD' and line5.arg_str(0) == 'R14':
                            line6 = line5.next()
                        else:
                            line6 = line5
                            line5 = None

                        if line6.instruction == 'SYS' and line6.arg(0) == 15:
                            if line.instruction[:2] == 'LD':
                                a1 = line.arg(1)
                                host_label = f'd_{a1:04X}'
                                listing.set_label(a1, host_label, False)
                                line.set_arg_type(1, 'o')

                            d = line.arg_str(1)
                            bit_len = line2.arg_str(1)
                            pulse = line4.arg_str(1)
                            line.set_comment('')
                            line2.set_comment('')
                            line3.set_comment('')
                            line4.set_comment('')
                            if line5:
                                line5.set_comment('???')
                            line6.set_comment(f'StreamOut({d}, {bit_len}, {pulse});\n')
                            line = line6.next()
                            continue

        #
        # SYS 16 -> (byte|word|dword)device.R14 = R15
        if line.instruction in ['MOV', 'LDD'] and line.arg_str(0) == 'R15':
            line2 = line.next()
            if line2.instruction == 'LDW' and line2.arg_str(0) == 'R14' and line2.arg_type(1) == 'd':
                line3 = line2.next()
                if line3.instruction == 'ORD' and line3.arg_str(0) == 'R14' and line3.arg_type(1) == 'd':
                    line4 = line3.next()
                    if line4.instruction == 'SYS' and line4.arg(0) == 16:
                        w = line3.arg(1) >> 16
                        w, pref = {1: ('byte', 'b_'), 2: ('word', 'w_'), 4: ('dword', 'd_')}.get(w, str(w))
                        dev_label = f'{pref}{line2.arg(1):04X}'
                        set_device_label(listing, line2.arg(1), dev_label)
                        line.set_comment(f'')
                        line2.set_comment('')
                        line3.set_comment(f'/* {line3.arg(1)}:{line2.arg(1)} is {w}:device.{dev_label} */')
                        line4.set_comment(f'({w})device.{dev_label} = {line.arg_str(1)};\n')
                        line = line4.next()
                        continue

        # device.any_array[NUM] = any
        if line.instruction == 'MOV' and line.arg_str(0) == 'R15':
            line2 = line.next()
            if line2.instruction == 'LDD' and line2.arg_str(0) == 'R14':
                line3 = line2.next()
                if line3.instruction == 'RL' and line3.arg_str(0) == 'R14':
                    w = line3.arg(1)
                    line4 = line3.next()
                else:
                    w = 0
                    line4 = line3
                    line3 = None
                if line4.instruction == 'ADDW' and line4.arg_str(0) == 'R14':
                    line5 = line4.next()
                    if line5.instruction == 'SYS' and line5.arg(0) == 16:
                        w, pref = {0: ('byte', 'b_'), 1: ('word', 'w_'), 2: ('dword', 'd_')}.get(w, str(w))
                        dev_label = f'{pref}{line4.arg(1):04X}'
                        set_device_label(listing, line4.arg(1), dev_label)
                        line.set_comment('')
                        line2.set_comment('')
                        if line3:
                            line3.set_comment('')
                        line4.set_comment('')
                        line5.set_comment(f'({w})device.{dev_label}[{line2.arg_str(1)}] = {line.arg_str(1)};\n')
                        line = line5.next()
                        continue

        # device.byte_array[local_var] = any
        if line.instruction == 'MOV' and line.arg_str(0) == 'R15':
            line2 = line.next()
            if line2.instruction == 'LMA' and line2.arg_str(0) == 'R14':
                line3 = line2.next()
                if line3.instruction == 'SYS' and line3.arg(0) == 16:
                    w = 'byte'
                    dev_label = f'b_{line2.arg(2):04X}'
                    set_device_label(listing, line2.arg(2), dev_label)
                    line.set_comment('')
                    line2.set_comment('')
                    line3.set_comment(f'({w})device.{dev_label}[{line2.arg_str(1)}] = {line.arg_str(1)};\n')
                    line = line3.next()
                    continue

        # device.byte_array[expression] = any
        if line.instruction == 'LMA' and line.arg_str(0) == 'R14':
            line2 = line.next()
            if line2.instruction == 'SYS' and line2.arg(0) == 16:
                w = 'byte'
                dev_label = f'b_{line.arg(2):04X}'
                set_device_label(listing, line.arg(2), dev_label)
                line.set_comment('')
                line2.set_comment(f'({w})device.{dev_label}[{line.arg_str(1)}] = R15;\n')
                line = line2.next()
                continue

        # device.word_array|dword_array[local_var] = any
        if line.instruction == 'MOV' and line.arg_str(0) == 'R15':
            line2 = line.next()
            if line2.instruction == 'MOV' and line2.arg_str(0) == 'R14':
                line3 = line2.next()
                if line3.instruction == 'RL' and line3.arg_str(0) == 'R14':
                    line4 = line3.next()
                    if line4.instruction == 'ADDW' and line4.arg_str(0) == 'R14':
                        line5 = line4.next()
                        if line5.instruction == 'SYS' and line5.arg(0) == 16:
                            w = line3.arg(1)
                            w, pref = {0: ('byte', 'b_'), 1: ('word', 'w_'), 2: ('dword', 'd_')}.get(w, str(w))
                            dev_label = f'{pref}{line4.arg(1):04X}'
                            set_device_label(listing, line4.arg(1), dev_label)
                            line.set_comment('')
                            line2.set_comment('')
                            line3.set_comment('')
                            line4.set_comment('')
                            line5.set_comment(f'({w})device.{dev_label}[{line2.arg_str(1)}] = {line.arg_str(1)};\n')
                            line = line5.next()
                            continue

        # device.word_array|dword_array[expression] = any
        if line.instruction == 'MOV' and line.arg_str(0) == 'R14':
            line2 = line.next()
            if line2.instruction == 'RL' and line2.arg_str(0) == 'R14':
                line3 = line2.next()
                if line3.instruction == 'ADDW' and line3.arg_str(0) == 'R14':
                    line4 = line3.next()
                    if line4.instruction == 'SYS' and line4.arg(0) == 16:
                        w = line2.arg(1)
                        w, pref = {1: ('word', 'w_'), 2: ('dword', 'd_')}.get(w, str(w))
                        dev_label = f'{pref}{line3.arg(1):04X}'
                        set_device_label(listing, line3.arg(1), dev_label)
                        line.set_comment('')
                        line2.set_comment('')
                        line3.set_comment('')
                        line4.set_comment(f'({w})device.{dev_label}[{line.arg_str(1)}] = R15;\n')
                        line = line4.next()
                        continue

        #
        # SYS 17 -> R15 = device.prc_id_R15low_byte(R15hi_byte args)
        if line.instruction == 'LDB' and line.arg_str(0) == 'R15' and line.arg_type(1) == 'd':
            line2 = line.next()
            if line2.instruction == 'SYS' and line2.arg(0) == 17:
                line.set_comment('')
                line2.set_comment(f'R15 = device.prc_id{line.arg(1)}();\n')
                line = line2.next()
                continue

        if line.instruction == 'LDB' and line.arg_str(0) == 'R15' and line.arg_type(1) == 'd':
            line2 = line.next()
            if line2.instruction == 'ORW' and line2.arg_str(0) == 'R15' and line2.arg_type(1) == 'd':
                line3 = line2.next()
                if line3.instruction == 'SYS' and line3.arg(0) == 17:
                    a = line2.arg(1)
                    proc_id = line.arg(1)
                    n = a >> 8
                    line.set_comment('')
                    line2.set_comment('')
                    line3.set_comment(f'R15 = device.prc_id{proc_id}(<{n} args>);\n')
                    line = line3.next()
                    continue

        #
        # SYS 18 -> device.prc_id_R15low_byte(R15hi_byte args)
        if line.instruction == 'LDB' and line.arg_str(0) == 'R15' and line.arg_type(1) == 'd':
            line2 = line.next()
            if line2.instruction == 'SYS' and line2.arg(0) == 18:
                line.set_comment('')
                line2.set_comment(f'device.prc_id{line.arg(1)}();\n')
                line = line2.next()
                continue

        if line.instruction == 'LDB' and line.arg_str(0) == 'R15' and line.arg_type(1) == 'd':
            line2 = line.next()
            if line2.instruction == 'ORW' and line2.arg_str(0) == 'R15' and line2.arg_type(1) == 'd':
                line3 = line2.next()
                if line3.instruction == 'SYS' and line3.arg(0) == 18:
                    a = line2.arg(1)
                    proc_id = line.arg(1)
                    n = a >> 8
                    line.set_comment(f'id {proc_id}')
                    line2.set_comment(f'args {n}')
                    line3.set_comment(f'device.prc_id{proc_id}(<{n} args>);\n')
                    line = line3.next()
                    continue

        #
        # SYS 19 -> R15 = (byte|word|dword)device.R15l
        if line.instruction == 'LDD' and line.arg_str(0) == 'R15' and line.arg_type(1) == 'd':
            line2 = line.next()
            if line2.instruction == 'SYS' and line2.arg(0) == 19:
                # SYS 19. R15hi - len bytes(1,2 or 4), R15lo = offset to device variable
                a = line.arg(1)
                w = a >> 16
                w, pref = {1: ('byte', 'b_'), 2: ('word', 'w_'), 4: ('dword', 'd_')}.get(w, str(w))
                o = a & 0xFFFF
                dev_label = f'{pref}{o:04X}'
                set_device_label(listing, o, dev_label)
                line.set_comment(f'/* {a} is {w}:device.{dev_label} */')
                line2.set_comment(f'R15 = ({w})device.{dev_label};')
                line = line2.next()
                continue

        if line.instruction == 'MOV' and line.arg_str(0) == 'R15':
            line2 = line.next()
            if line2.instruction == 'ADDD' and line2.arg_str(0) == 'R15' and line2.arg_type(1) == 'd':
                line3 = line2.next()
                if line3.instruction == 'SYS' and line3.arg(0) == 19:
                    # SYS 19. R15hi - len bytes(1,2 or 4), R15lo = offset to device variable
                    a = line2.arg(1)
                    w = a >> 16
                    w, pref = {1: ('byte', 'b_'), 2: ('word', 'w_'), 4: ('dword', 'd_')}.get(w, str(w))
                    o = a & 0xFFFF
                    dev_label = f'{pref}{o:04X}'
                    set_device_label(listing, o, dev_label)
                    line.set_comment('')
                    line2.set_comment(f'/* {a} is {w}:device.{dev_label} */')
                    line3.set_comment(f'R15 = ({w})device.{dev_label}[{line.arg_str(1)}];')
                    line = line3.next()
                    continue

        if line.instruction == 'MOV' and line.arg_str(0) == 'R15':
            line2 = line.next()
            if line2.instruction == 'RL' and line2.arg_str(0) == 'R15' and line2.arg_type(1) == 'd':
                line3 = line2.next()
                if line3.instruction == 'ADDD' and line3.arg_str(0) == 'R15':
                    line4 = line3.next()
                    if line4.instruction == 'SYS' and line4.arg(0) == 19:
                        a = line3.arg(1)
                        w = a >> 16
                        w, pref = {1: ('byte', 'b_'), 2: ('word', 'w_'), 4: ('dword', 'd_')}.get(w, str(w))
                        o = a & 0xFFFF
                        i = line.arg_str(1)
                        dev_label = f'{pref}{o:04X}'
                        set_device_label(listing, o, dev_label)
                        line.set_comment('')
                        line2.set_comment('')
                        line3.set_comment(f'/* {a} is {w}:device.{dev_label} /*')
                        line4.set_comment(f'R15 = ({w})device.{dev_label}[{i}];')
                        line = line4.next()
                        continue

        #
        # SYS 20 -> block(R15 = device.R14l, R14h)
        if line.instruction == 'LDW' and line.arg_str(0) == 'R15':
            line2 = line.next()
            if line2.instruction == 'LDW' and line2.arg_str(0) == 'R14':
                line3 = line2.next()
                if line3.instruction == 'ORD' and line3.arg_str(0) == 'R14':
                    line4 = line3.next()
                    if line4.instruction == 'SYS' and line4.arg(0) == 20:
                        a1 = line.arg(1)
                        host_label = f'd_{a1:04X}'
                        listing.set_label(a1, host_label, False)
                        line.set_arg_type(1, 'o')
                        dev_label = f'b_{line2.arg(1):04X}'
                        set_device_label(listing, line2.arg(1), dev_label)
                        a3 = line3.arg(1) >> 16
                        line.set_comment(f'/* {host_label} is byte array */')
                        line2.set_comment(f'/* device.{dev_label} */')
                        line3.set_comment(f'/* ({a3} << 16) */')
                        line4.set_comment(f'block({host_label} = device.{dev_label}, {a3});\n')
                        line = line4.next()
                        continue

        if line.instruction == 'LDW' and line.arg_str(0) == 'R15':
            line2 = line.next()
            if line2.instruction == 'LDW' and line2.arg_str(0) == 'R14':
                line3 = line2.next()
                if line3.instruction == 'RL':
                    line4 = line3.next()
                    if line4.instruction == 'OR' and line4.arg_str(0) == 'R14' and line4.arg_str(1) == line3.arg_str(0):
                        line5 = line4.next()
                        if line5.instruction == 'SYS' and line5.arg(0) == 20:
                            a1 = line.arg(1)
                            host_label = f'd_{a1:04X}'
                            listing.set_label(a1, host_label, False)
                            line.set_arg_type(1, 'o')
                            dev_label = f'b_{line2.arg(1):04X}'
                            set_device_label(listing, line2.arg(1), dev_label)
                            # a3 = line4.arg(1) >> 16
                            a3 = line3.arg_str(0)
                            line.set_comment(f'{a3} is arg2')
                            line2.set_comment('')
                            line3.set_comment('')
                            line4.set_comment('')
                            line5.set_comment(f'block({host_label} = device.{dev_label}, arg2);\n')
                            line = line5.next()
                            continue

        #
        # SYS 21 -> block|memcopy(fbuf[R15] = device.R14l, R14h)
        if line.instruction in ['MOV', 'LDD'] and line.arg_str(0) == 'R15':
            line2 = line.next()
            if line2.instruction == 'LDW' and line2.arg_str(0) == 'R14':
                line3 = line2.next()
                if line3.instruction == 'ORD' and line3.arg_str(0) == 'R14':
                    line4 = line3.next()
                    if line4.instruction == 'SYS' and line4.arg(0) == 21:
                        a1 = line.arg_str(1)
                        dev_label = f'b_{line2.arg(1):04X}'
                        set_device_label(listing, line2.arg(1), dev_label)
                        a3 = line3.arg(1) >> 16
                        if a1.isdigit():
                            a1l = int(a1) & 0x00FFFFFF
                            a1 = f'{a1l} | 0x{int(a1) & 0xFF000000:08x}'
                            line.set_comment(f'/* {a1} */')
                            a1 = a1l
                        else:
                            line.set_comment('')
                        line2.set_comment(f'/* device.{dev_label} is byte array */')
                        line3.set_comment('')
                        line4.set_comment(f'block|memcopy(fbuf_?[{a1}] = device.{dev_label}, {a3});\n')
                        # add_global_emem_var(listing, ?, ?)
                        line = line4.next()
                        continue

        if line.instruction == 'LDW' and line.arg_str(0) == 'R14':
            line2 = line.next()
            if line2.instruction == 'RL' and line2.arg(1) == 16:
                line3 = line2.next()
                if line3.instruction == 'OR' and line3.arg_str(0) == 'R14':
                    line4 = line3.next()
                    if line4.instruction == 'SYS' and line4.arg(0) == 21:
                        dev_label = f'b_{line.arg(1):04X}'
                        set_device_label(listing, line.arg(1), dev_label)
                        line.set_comment('')
                        line2.set_comment('')
                        line3.set_comment('')
                        line4.set_comment(f'block(fbuf_?[R15] = device.{dev_label}, HWORD(R14));\n')
                        # add_global_emem_var(listing, ?, ?)
                        line = line4.next()
                        continue

        #
        # SYS 22 -> block|memcopy(device.R14l = R15, R14h)
        if line.instruction == 'LDW' and line.arg_str(0) == 'R14':
            line2 = line.next()
            if line2.instruction == 'LDW' and line2.arg_str(0) == 'R15':
                line3 = line2.next()
                if line3.instruction == 'ORD' and line3.arg_str(0) == 'R14':
                    line4 = line3.next()
                    if line4.instruction == 'SYS' and line4.arg(0) == 22:
                        line2.set_arg_type(1, 'o')
                        dev_label = f'b_{line.arg(1):04X}'
                        set_device_label(listing, line.arg(1), dev_label)
                        host_label = f'd_{line2.arg(1):04X}'
                        a3 = line3.arg(1) >> 16
                        line.set_comment(f'/* device.{dev_label} */')
                        line2.set_comment('')
                        line3.set_comment(f'/* ({a3} << 16) */')
                        line4.set_comment(f'block|memcopy(device.{dev_label} = {host_label}, {a3});\n')
                        line = line4.next()
                        continue

        #
        # SYS 23 -> block|memcopy(device.R14l=fbuf[R15],R14h)
        if line.instruction == 'LDW' and line.arg_str(0) == 'R14':
            line2 = line.next()
            if line2.instruction == 'MOV' and line2.arg_str(0) == 'R15':
                line3 = line2.next()
                if line3.instruction == 'RL' and line3.arg(1) == 16:
                    line4 = line3.next()
                    if line4.instruction == 'OR' and line4.arg_str(0) == 'R14':
                        line5 = line4.next()
                        if line5.instruction == 'SYS' and line5.arg(0) == 23:
                            dev_label = f'b_{line.arg(1):04X}'
                            set_device_label(listing, line.arg(1), dev_label)
                            a3 = line4.arg_str(1)
                            line.set_comment(f'/* device.{dev_label} */')
                            line2.set_comment('')
                            line3.set_comment('')
                            line4.set_comment('')
                            line5.set_comment(f'block|memcopy(device.{dev_label} = fbuf_?[{line2.arg_str(1)}], {a3});\n')
                            # add_global_emem_var(listing, ?, ?)
                            line = line5.next()
                            continue

        # block|memcopy(device.R14l=fbuf[any],const)
        if line.instruction == 'LDW' and line.arg_str(0) == 'R14':
            line2 = line.next()
            if line2.instruction in ['MOV', 'LDD'] and line2.arg_str(0) == 'R15':
                line3 = line2.next()
                if line3.instruction == 'ORD' and line3.arg_str(0) == 'R14':
                    line4 = line3.next()
                    if line4.instruction == 'SYS' and line4.arg(0) == 23:
                        dev_label = f'b_{line.arg(1):04X}'
                        set_device_label(listing, line.arg(1), dev_label)
                        a3 = line3.arg(1) >> 16
                        line.set_comment(f'/* device.{dev_label} */')
                        line2.set_comment('')
                        line3.set_comment(f'/* ({a3} << 16) */')
                        line4.set_comment(f'block|memcopy(device.{dev_label} = fbuf_?[{line2.arg_str(1)}], {a3});\n')
                        # add_global_emem_var(listing, ?, ?)
                        line = line4.next()
                        continue

        # block|memcopy(device.R14l=fbuf[any],any)
        if line.instruction == 'RL' and line.arg(1) == 16:
            line2 = line.next()
            if line2.instruction == 'OR' and line2.arg_str(0) == 'R14' and line.arg_str(0) == line2.arg_str(1):
                line3 = line2.next()
                if line3.instruction == 'SYS' and line3.arg(0) == 23:
                    dev_label = 'device.(LOWORD(R14))'
                    a3 = line2.arg_str(1)
                    line.set_comment('')
                    line2.set_comment('')
                    line3.set_comment(f'block|memcopy({dev_label} = fbuf_?[R15], {a3});\n')
                    # add_global_emem_var(listing, ?, ?)
                    line = line3.next()
                    continue

        #
        # SYS 24 -> label_R14.color = R15
        if line.instruction == 'LDD' and line.arg_str(0) == 'R15':
            line2 = line.next()
            if line2.instruction == 'LDD' and line2.arg_str(0) == 'R14':
                line3 = line2.next()
                if line3.instruction == 'SYS' and line3.arg(0) == 24:
                    line.set_comment('')
                    line2.set_comment('')
                    line3.set_comment(f'label_{line2.arg(1):04X} = 0x{line.arg(1):06x};\n')
                    line = line3.next()
                    continue

        #
        # SYS 25 -> R14.color = R15
        if line.instruction in ['LDW', 'LDD'] and line.arg_str(0) == 'R14':
            line2 = line.next()
            if line2.instruction == 'LDD' and line2.arg_str(0) == 'R15':
                line3 = line2.next()
                if line3.instruction == 'SYS' and line3.arg(0) == 25:
                    line.set_arg_type(1, 'o')
                    line.set_comment('')
                    line2.set_comment('')
                    ui = listing.line(line.arg(1)).name
                    line3.set_comment(f'{ui}.color = 0x{line2.arg(1):06x};\n')
                    line = line3.next()
                    continue

        #
        # SYS 29 -> FILENAME = TMP
        if line.instruction == 'SYS' and line.arg(0) == 29:
            line.set_comment(f'FILENAME = TMP;\n')
            line = line.next()
            continue

        #
        # SYS 30 -> SaveToFile(...)
        # SYS 31 -> LoadFromFile(...)
        if line.instruction == 'LDD' and line.arg_str(0) == 'R15':
            line2 = line.next()
            if line2.instruction == 'SYS' and line2.arg(0) in [30, 31]:
                v = line.arg(1)
                if v & 0x80000000 == 0x80000000:
                    v1 = v ^ 0x80000000
                    s = f'fbuf_{v1}'
                    line.set_comment(f'/* 0x80000000 | {v1} */')
                else:
                    v1 = v
                    s = f'fbuf_{v1}'
                    line.set_comment('')
                line2.set_comment(f'{"SaveToFile" if line2.arg(0) == 30 else "LoadFromFile"}({s})\n')
                add_global_emem_var(listing, s, v1)
                line = line2.next()
                continue

        if line.instruction == 'LDW' and line.arg_str(0) == 'R15' and line.arg_type(1) == 'd':
            line2 = line.next()
            if line2.instruction == 'ORD' and line2.arg_str(0) == 'R15':
                line3 = line2.next()
                if line3.instruction == 'SYS' and line3.arg(0) in [30, 31]:
                    line.set_arg_type(1, 'o')
                    a3 = line2.arg(1) >> 16
                    line.set_comment(f'/* {line.arg_str(1)} is a byte array, {a3} bytes length */')
                    line2.set_comment(f'/* ({a3} << 16) */')
                    line3.set_comment(f'{"SaveToFile" if line3.arg(0) == 30 else "LoadFromFile"}({line.arg_str(1)})\n')
                    line = line3.next()
                    continue

        #
        # SYS 34 -> text = str
        if line.instruction == 'LDB' and line.arg_str(0) == 'R15':
            line2 = line.next()
            if line2.instruction == 'SYS' and line2.arg(0) == 34:
                line.set_comment('-')
                line2.set_comment(f'TMP += text_{line.arg(1):04X}')
                line = line2.next()
                continue

        #
        # SYS 40 -> R15 = len(str_stack0)
        if line.instruction == 'LDB' and line.arg_str(0) == 'R15':
            line2 = line.next()
            if line2.instruction == 'PUSH' and line2.arg_str(0) == 'R15':
                line3 = line2.next()
                if line3.instruction == 'SYS' and line3.arg(0) == 40:
                    line4 = line3.next()
                    if line4.instruction == 'MOV' and line4.arg_str(1) == 'R15':
                        line.set_comment('')
                        line2.set_comment('')
                        line3.set_comment('')
                        line4.set_comment(f'{line4.arg_str(0)} = len(str_{line.arg(1)});\n')
                        add_global_str_idx(listing, line.arg(1))
                        line = line4.next()
                        continue

        #
        # SYS 50 -> R15 = str_stack0[stack1]
        if line.instruction == 'PUSH':
            line2 = line.next()
            if line2.instruction == 'LDB' and line2.arg_str(0) == 'R15':
                line3 = line2.next()
                if line3.instruction == 'PUSH' and line3.arg_str(0) == 'R15':
                    line4 = line3.next()
                    if line4.instruction == 'SYS' and line4.arg(0) == 50:
                        line5 = line4.next()
                        if line5.instruction == 'MOV' and line5.arg_str(1) == 'R15':
                            line.set_comment('')
                            line2.set_comment('')
                            line3.set_comment('')
                            line4.set_comment('')
                            line5.set_comment(f'{line5.arg_str(0)} = str_{line2.arg(1)}[{line.arg_str(0)}];')
                            add_global_str_idx(listing, line2.arg(1))
                            line = line5.next()
                            continue

        #
        #
        if line.instruction == 'CALL':
            a = line.arg(0)
            a = listing.get_label(a)
            line.set_comment(f'{a}();\n')
            line = line.next()
            continue

        #
        # SYS 10 -> ShowWindow
        if line.instruction == 'SYS' and line.arg(0) == 10:
            line.set_comment(f'ShowWindow;\n')
            line = line.next()
            continue

        #
        # SYS 11 -> CloseWindow
        if line.instruction == 'SYS' and line.arg(0) == 11:
            line.set_comment(f'CloseWindow;\n')
            line = line.next()
            continue

        #
        # SYS 14 -> Delay(R15)
        if line.instruction in ['LDB', 'LDW', 'LDD', 'MOV'] and line.arg_str(0) == 'R15':
            line2 = line.next()
            if line2.instruction == 'SYS' and line2.arg(0) == 14:
                a = line.arg_str(1)
                line.set_comment(f'')
                line2.set_comment(f'Delay({a});\n')
                line = line2.next()
                continue

        #
        # return
        if line.instruction == 'POPR' and line.name:
            line2 = line.next()
            if line2.instruction == 'RET':
                label = f'end_{listing.get_label(ea)}'
                listing.set_label(line.ea, label)
                line_ = listing.line(ea)
                line_pre = None
                while True:
                    if 'P' in line_.type and line_.ea != ea:  # конец ф-ии
                        break
                    if line_.instruction == 'JMP' and line_.arg_str(0) == label:
                        if line_pre and line_pre.instruction in ['MOV', 'LDB', 'LDW', 'LDD'] and \
                                line_pre.arg_str(0) == 'R15':
                            line_pre.set_comment('')
                            line_.set_comment(f'return({line_pre.arg_str(1)});\n')
                        else:
                            line_.set_comment('return;\n')
                    line_pre = line_
                    line_ = line_.next()
                line = line2.next()
                continue

        if line.instruction == 'MOV' and line.arg_str(0) == 'R15':
            line2 = line.next()
            if line2.instruction == 'POPR':
                line3 = line2.next()
                if line3.instruction == 'RET':
                    line.set_comment(f'return({line.arg_str(1)});')

        #
        #
        if line.instruction in ['STMB', 'STMW', 'STMD']:
            line.set_comment(f'{line.arg_str(0)} = {line.arg_str(1)};\n')
            line = line.next()
            continue

        #
        #
        if line.instruction in ['LDMB', 'LDMW', 'LDMD']:
            line.set_comment(f'{line.arg_str(0)} = {line.arg_str(1)};\n')
            line = line.next()
            continue

        #
        # emem fbuf=...
        if line.instruction in ['LDB', 'LDW', 'LDD'] and line.arg_str(0) == 'R15':
            line2 = line.next()
            if line2.instruction in ['LDB', 'LDW', 'LDD'] and line2.arg_str(0) == 'R14':
                line3 = line2.next()
                if line3.instruction == 'STEM' and line3.arg_str(1) == 'R14' and line3.arg_str(2) == 'R15':
                    line.set_comment(f'')
                    line2.set_comment(f'')
                    b = line3.arg(0)
                    idx = line2.arg(1)
                    v = line.arg(1)
                    s = f'fbuf_{b}'
                    line3.set_comment(f'{s}[{idx}] = {v};\n')
                    add_global_emem_var(listing, s, b)
                    line = line3.next()
                    continue

        if line.instruction == 'STEM':
            b = line.arg(0)
            idx = line.arg_str(1)
            v = line.arg_str(2)
            s = f'fbuf_{b}'
            line.set_comment(f'{s}[{idx}] = {v};\n')
            add_global_emem_var(listing, s, b)
            line = line.next()
            continue

        if line.instruction == 'LDEM':
            b = line.arg(0)
            v = line.arg_str(1)
            idx = line.arg_str(2)
            s = f'fbuf_{b}'
            line.set_comment(f'{v} = {s}[{idx}];\n')
            add_global_emem_var(listing, s, b)
            line = line.next()
            continue

        if line.instruction in ['AWRB', 'AWRW', 'AWRD']:
            v = line.arg_str(0)
            idx = line.arg_str(1)
            a = line.arg_str(2)
            line.set_comment(f'{v}[{idx}] = {a};\n')
            line = line.next()
            continue

        if line.instruction in ['ARDB', 'ARDW', 'ARDD']:
            a = line.arg_str(0)
            v = line.arg_str(1)
            idx = line.arg_str(2)
            line.set_comment(f'{a} = {v}[{idx}];\n')
            line = line.next()
            continue

        #
        # next line
        line = line.next()


def decompile_post(listing: Listing):
    # emem
    for v, i in listing.dis.presets['global']['emem']:
        listing.glob.append(f'emem {v}={i};')
    if listing.dis.presets['global']['emem']:
        listing.glob.append('')

    # string
    s = listing.dis.presets['global']['string']
    if s:
        str_vars = ', '.join(f'str_{i}' for i in range(max(s) + 1))
        listing.glob.append(f'string {str_vars};')
        listing.glob.append('')
