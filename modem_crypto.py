class ModemCrypto:
    AES_Sbox = [
        99,124,119,123,242,107,111,197,48,1,103,43,254,215,171,118,202,130,201,125,250,89,71,240,173,212,162,175,156,164,114,192,183,253,147,38,54,63,247,204,52,165,229,241,113,216,49,21,4,199,35,195,24,150,5,154,7,18,128,226,235,39,178,117,9,131,44,26,27,110,90,160,82,59,214,179,41,227,47,132,83,209,0,237,32,252,177,91,106,203,190,57,74,76,88,207,208,239,170,251,67,77,51,133,69,249,2,127,80,60,159,168,81,163,64,143,146,157,56,245,188,182,218,33,16,255,243,210,205,12,19,236,95,151,68,23,196,167,126,61,100,93,25,115,96,129,79,220,34,42,144,136,70,238,184,20,222,94,11,219,224,50,58,10,73,6,36,92,194,211,172,98,145,149,228,121,231,200,55,109,141,213,78,169,108,86,244,234,101,122,174,8,186,120,37,46,28,166,180,198,232,221,116,31,75,189,139,138,112,62,181,102,72,3,246,14,97,53,87,185,134,193,29,158,225,248,152,17,105,217,142,148,155,30,135,233,206,85,40,223,140,161,137,13,191,230,66,104,65,153,45,15,176,84,187,22
    ]

    AES_ShiftRowTab = [
        0,5,10,15,4,9,14,3,8,13,2,7,12,1,6,11
    ]

    @staticmethod
    def hexstr2array(input_str, length):
        output = [0] * length
        for i in range(length):
            if i < len(input_str) // 2:
                substr = input_str[i*2 : i*2+2]
                try:
                    output[i] = int(substr, 16)
                except ValueError:
                    output[i] = 0
            else:
                output[i] = 0
        return output

    @staticmethod
    def str2hexstr(input_str):
        output = ""
        for char in input_str:
            output += hex(ord(char))[2:]
        return output

    @staticmethod
    def array2hexstr(input_arr):
        output = ""
        for val in input_arr:
            tmp = hex(val)[2:]
            if len(tmp) == 1:
                tmp = "0" + tmp
            output += tmp
        return output

    @classmethod
    def AES_AddRoundKey(cls, state, rkey):
        for i in range(16):
            state[i] ^= rkey[i]

    @classmethod
    def AES_SubBytes(cls, state):
        for i in range(16):
            state[i] = cls.AES_Sbox[state[i]]

    @classmethod
    def AES_ShiftRows(cls, state):
        h = list(state)
        for i in range(16):
            state[i] = h[cls.AES_ShiftRowTab[i]]
            
    # MixColumns is unused in the specific flow (loop doesn't run), so omitted.

    @classmethod
    def AES_Encrypt(cls, block, key):
        # block is a list of 16 ints (mutable)
        # key is a list of 32 ints
        l = len(key)
        
        # Initial AddRoundKey (bytes 0-16)
        cls.AES_AddRoundKey(block, key[0:16])
        
        # Loop: for(var i = 16; i < l - 16; i += 16)
        # l=32, l-16=16. i starts at 16. i < 16 is False. Loop skipped.
        
        # Final rounds
        cls.AES_SubBytes(block)
        cls.AES_ShiftRows(block)
        
        # Final AddRoundKey (bytes 16-32)
        # i would be 16 from the loop if it ran, or logic implies last 16 bytes.
        # The JS code uses 'i' variable from the loop scope:
        # for(var i = 16...); AES_AddRoundKey(..., key.slice(i, l))
        # Since loop doesn't run, 'i' is initialized to 16? 
        # JS `var i` hoisting: 'i' is declared.
        # Check explicit loop:
        # for(var i = 16; i < l - 16; i += 16) { ... }
        # AES_AddRoundKey(block, key.slice(i, l));
        # In JS, if the loop condition fails immediately, 'i' has been initialized to 16.
        # So we use index 16.
        cls.AES_AddRoundKey(block, key[16:32])
        
        return block

    @classmethod
    def encode_pw(cls, password):
        key = "54494641" # TIFA
        private_key_byte = cls.hexstr2array(key, 32)
        
        # Password to hex string
        pw_hex = cls.str2hexstr(password)
        # Hex string to 64-byte array (padding with zeros)
        passwd_byte = cls.hexstr2array(pw_hex, 64)
        
        output_byte = [0] * 64
        
        # Encrypt 4 blocks
        for i in range(4):
            # Extract 16-byte block
            block = passwd_byte[i*16 : (i+1)*16]
            
            # Encrypt
            cls.AES_Encrypt(block, private_key_byte)
            
            # Store result
            for j in range(16):
                output_byte[i*16 + j] = block[j]
                
        return cls.array2hexstr(output_byte)

if __name__ == "__main__":
    # Test with known value
    # User: admin, Pass: Q7fR9xL2M6ZKp8dS
    # Expected: 6bbcbeed1205437de307b72351f329b3206363636363638363635a63633b6363206363636363638363635a63633b6363206363636363638363635a63633b6363
    
    test_pass = "Q7fR9xL2M6ZKp8dS"
    expected = "6bbcbeed1205437de307b72351f329b3206363636363638363635a63633b6363206363636363638363635a63633b6363206363636363638363635a63633b6363"
    
    result = ModemCrypto.encode_pw(test_pass)
    print(f"Password: {test_pass}")
    print(f"Result:   {result}")
    print(f"Expected: {expected}")
    print(f"Match:    {result == expected}")
