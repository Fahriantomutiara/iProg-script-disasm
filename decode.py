import struct
import des


class Decoder:
    most_popular_sn = [1, 777, 19]
    sn_list = None
    # sn_list = range(65535)
    ignore_check = False

    @classmethod
    def touch(cls, sn_list):
        cls.sn_list = sn_list

    @classmethod
    def serial_numbers(cls):
        if cls.sn_list:
            for sn in cls.sn_list:
                yield sn
        else:
            for sn in cls.most_popular_sn:
                yield sn
            # for sn in (sn for sn in range(0xFFFF) if sn not in cls.most_popular_sn):
            #     yield sn

    @classmethod
    def decode_ipr_bytecode(cls, data, crc):
        if crc == crc16(data):
            # bytecode не закодирован
            print("## device bytecode is not encoded")
            return data

        for sn in cls.serial_numbers():
            print(f'try sn: {sn:>5} \r', end='')
            r = decode_ipr_v1(data, crc, sn)
            if r is not None:
                print(f"## device bytecode is encoded (sn: {sn})")
                return r

            # if not decode_ipr_v2_fastcheck(data, crc, sn, 0):
            #     continue

            r = decode_ipr_v2(data, crc, sn)
            if r is not None:
                print(f"## device bytecode is DES encoded (sn: {sn})")
                return r

            r = decode_ipr_v2(data, crc, sn, 0xB33506FB)
            if r is not None:
                print(f"## device bytecode is DES (777) encoded (sn: {sn})")
                return r

        print("## bad bytecode or unknown encoding")
        return None

    @classmethod
    def decode_cal_bytecode(cls, data):
        data_len = len(data)
        if data_len < 32+2:  # minimum 1 block +2 bytes crc
            print('## data size is too small, the file is corrupted')
            return None
        data_len = 32 * (data_len // 32) - 32
        _data = data[:data_len]
        _pad = data[data_len:]
        crc = _pad[0] << 8 | _pad[1]
        if len(_pad) != 32:
            print('## data size is not a multiple of 32, the file is probably corrupted')

        for sn in cls.serial_numbers():
            print(f'try sn: {sn:>5} \r', end='')
            r = decode_cal(_data, crc, sn)
            if r is not None:
                print(f"## calculator bytecode is encoded (sn: {sn})")
                return r

        print("## bad bytecode or unknown encoding")
        return None


def crc16(data):
    crc = 0xFFFF
    for i in range(len(data)):
        crc ^= data[i] << 8
        for j in range(0, 8):
            if (crc & 0x8000) > 0:
                crc = (crc << 1) ^ 0x8408
            else:
                crc = crc << 1
    return crc & 0xFFFF


def crc16_1021(data):
    crc = 0xFFFF
    for i in range(len(data)):
        crc ^= data[i] << 8
        for j in range(0, 8):
            if (crc & 0x8000) > 0:
                crc = (crc << 1) ^ 0x1021
            else:
                crc = crc << 1
    return crc & 0xFFFF


def get_sn():
    sn_encoded = 0x69EB7BDF  # sn == 1
    # sn_encoded = 0x23b9318D     # sn == 19
    # sn_encoded = 0x0f6bd109     # sn == 777 ?? не сходится...
    # sn_encoded = 0x79a96b9d     # sn == 777

    # sn_encoded = 0x0f6b
    # sn_encoded = ((sn_encoded ^ 0x1234) << 16) | sn_encoded
    if (sn_encoded >> 0x10 ^ sn_encoded) & 0xFFFF == 0x1234:
        result = sn_encoded & 0xFFFF
        for n in range(0x10):
            if (sn_encoded & 1) == 0:
                result = (result << 1) ^ 0x8021
            else:
                result <<= 1
            sn_encoded >>= 1
        return result & 0xFFFF
    else:
        return 0xFFFF


def decode_ipr_v1(data, crc, sn):
    # Закодирован
    # v1
    tbl1 = (0x11, 0x22, 0x33, 0x14, 0x25, 0x36, 0x17, 0x28, 0x39, 0x1A, 0x2B, 0x3C, 0x1D, 0x2E, 0x3F, 0x35)
    datalen = len(data)
    data2 = list(data)
    crcpad = [0] * 64
    crcpad[0] = crc >> 8
    crcpad[1] = crc & 0xFF
    data2 += crcpad

    # sn = get_sn()
    x = tbl1[sn & 0x0F]

    data2[datalen] ^= data2[0]
    data2[datalen+1] ^= data2[1]

    z = (sn >> 8) ^ sn ^ data2[datalen] ^ data2[datalen+1]

    buf = [0] * 64
    for p in range(0, datalen, 64):

        for i in range(64):
            buf[i ^ (x & 0xFF)] = data2[p + i] ^ (z & 0xFF)
            z += i
        for i in range(64):
            data2[p + i] = buf[i]

    crc2 = data2[-64] << 8 | data2[-63]
    data2 = bytearray(data2[:-64])
    if crc2 == crc16(data2):
        return data2
    else:
        return data2 if Decoder.ignore_check else None


def decode_ipr_v2(data, crc, sn, sub_key=0xA5A5A5A5):
    # Закодирован DES
    # v2

    def get_xyz(seed):
        result = 0
        for i in range(32):
            if seed & 0x80000000 == 0:
                result = (result ^ 0x8437A5BE) * 0x11
            else:
                result = (result * 0x0B) ^ (result * 0xB0000)
            seed <<= 1
        return result & 0xFFFFFFFF

    if len(data) % 8:
        return None

    # sn = get_sn()
    k = get_xyz(sn)

    # DES ECB
    key = struct.pack('>II', k, k ^ sub_key)

    dkeys = tuple(des.derive_keys(key))[::-1]
    tmp = []
    blocks = (struct.unpack(">Q", data[i: i + 8])[0] for i in range(0, len(data), 8))
    for block in blocks:
        tmp.append(des.encode_block(block, dkeys))
    decoded = bytearray(b''.join(struct.pack(">Q", block) for block in tmp))

    # Additional iprog decoding
    for i in range(len(decoded)):
        decoded[i] ^= k & 0xFF
        k += 1

    if crc == crc16(decoded):
        return decoded
    else:
        return decoded if Decoder.ignore_check else None


def decode_ipr_v2_fastcheck(data, _crc, sn, offset=0):
    # Search pattern.
    # PUSHR  xx         5A xx
    # ENTER  yy, zz     5F yz
    # ...
    # Procs may start with a different pattern if they have no variables and arguments

    def get_xyz(seed):
        result = 0
        for i in range(32):
            if seed & 0x80000000 == 0:
                result = (result ^ 0x8437A5BE) * 0x11
            else:
                result = (result * 0x0B) ^ (result * 0xB0000)
            seed <<= 1
        return result & 0xFFFFFFFF

    maxblocks = 1 + (offset + 2) // 8
    k = get_xyz(sn)

    # DES ECB
    key = struct.pack('>II', k, k ^ 0xA5A5A5A5)

    dkeys = tuple(des.derive_keys(key))[::-1]
    tmp = []
    blocks = (struct.unpack(">Q", data[i: i + 8])[0] for i in range(0, len(data), 8))
    for block in blocks:
        tmp.append(des.encode_block(block, dkeys))
        if len(tmp) >= maxblocks:
            break

    decoded = bytearray(b''.join(struct.pack(">Q", block) for block in tmp))

    # Additional iprog decoding
    for i in range(len(decoded)):
        decoded[i] ^= k & 0xFF
        k += 1

    if decoded[offset] == 0x5A and decoded[offset+1] < 32 and decoded[offset+2] == 0x5F:
        print(f'## possible sn: {sn}')
        return True
    else:
        return False


def decode_cal(data, crc, sn):
    tbl1 = (0x1F, 0x0E, 0x1D, 0x0C, 0x1B, 0x0A, 0x19, 0x08, 0x17, 0x06, 0x15, 0x04, 0x13, 0x02, 0x11, 0x05)
    x = tbl1[sn & 0x0F]
    z = (x * ((sn >> 8) ^ sn) & 0xFF) ^ (crc >> 8) ^ (crc & 0xFF)
    z &= 0xFF
    buf = [0] * 32
    data2 = bytearray(data)
    for p in range(0, len(data2), 32):
        for i in range(32):
            buf[i ^ x] = data2[p + i] ^ z
            z = (z + 0x55) & 0xFF
        for i in range(32):
            data2[p + i] = buf[i]

    if crc == crc16_1021(data2):
        return data2
    else:
        return data2 if Decoder.ignore_check else None
