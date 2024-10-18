
#define TARGET_PREFIX "PYTHON_INJECTION_1"
#define STRING_PREFIX "PYTHON_INJECTION_2"
#define STRING_SUFFIX "PYTHON_INJECTION_3"
#define TARGET_LEN PYTHON_INJECTION_4

__constant char target_prefix[9] = TARGET_PREFIX;
__constant char prefix[] = STRING_PREFIX;
__constant char suffix[] = STRING_SUFFIX;

// Function to convert uint to string
int uint_to_string(uint value, char *str) {
    int len = 0;
    uint num = value;
    char temp_str[12]; // Maximum length for uint32 is 10 digits
    do {
        temp_str[len++] = '0' + (num % 10);
        num = num / 10;
    } while (num > 0);
    // Reverse the string
        for (int i = 0; i < len; i++) {
        str[i] = temp_str[len - i - 1];
    }
    return len;
}

// Rotate left function
ulong rotl64(ulong x, uint n) {
    return (x << n) | (x >> (64 - n));
}

// Keccak-f[1600] permutation
void keccakf(ulong *state) {
    const ulong keccakf_rndc[24] = {
        0x0000000000000001UL, 0x0000000000008082UL,
        0x800000000000808aUL, 0x8000000080008000UL,
        0x000000000000808bUL, 0x0000000080000001UL,
        0x8000000080008081UL, 0x8000000000008009UL,
        0x000000000000008aUL, 0x0000000000000088UL,
        0x0000000080008009UL, 0x000000008000000aUL,
        0x000000008000808bUL, 0x800000000000008bUL,
        0x8000000000008089UL, 0x8000000000008003UL,
        0x8000000000008002UL, 0x8000000000000080UL,
        0x000000000000800aUL, 0x800000008000000aUL,
        0x8000000080008081UL, 0x8000000000008080UL,
        0x0000000080000001UL, 0x8000000080008008UL
    };

    const uint keccakf_rotc[24] = {
        1, 3, 6, 10, 15, 21,
        28, 36, 45, 55, 2, 14,
        27, 41, 56, 8, 25, 43,
        62, 18, 39, 61, 20, 44
    };

    const uint keccakf_piln[24] = {
        10, 7,11,17,18, 3, 5,16,
        8,21,24, 4,15,23,19,13,
        12, 2,20,14,22, 9, 6, 1
    };

    int round;
    for (round = 0; round < 24; round++) {
        ulong t, bc[5];
        int i, j;

        // Theta
        for (i = 0; i < 5; i++) {
            bc[i] = state[i] ^ state[i + 5] ^ state[i + 10] ^ state[i + 15] ^ state[i + 20];
        }

        for (i = 0; i < 5; i++) {
            t = bc[(i + 4) % 5] ^ rotl64(bc[(i + 1) % 5], 1);
            for (j = 0; j < 25; j += 5) {
                state[j + i] ^= t;
            }
        }

        // Rho Pi
        t = state[1];
        for (i = 0; i < 24; i++) {
            j = keccakf_piln[i];
            bc[0] = state[j];
            state[j] = rotl64(t, keccakf_rotc[i]);
            t = bc[0];
        }

        // Chi
        for (j = 0; j < 25; j += 5) {
            for (i = 0; i < 5; i++) {
                bc[i] = state[j + i];
            }
            for (i = 0; i < 5; i++) {
                state[j + i] = bc[i] ^((~bc[(i + 1)%5]) & bc[(i + 2)%5]);
            }
        }

        // Iota
        state[0] ^= keccakf_rndc[round];
    }
}

__kernel void keccak_hash(__global const uint *input_numbers, __global uchar *output_flags){
    uint gid = get_global_id(0);

    // Prepare the input string with the random number inserted
    char random_number_str[12]; // Max length for uint32 is 10 digits
    int num_len = uint_to_string(input_numbers[gid], random_number_str);

    // Compute the total length of the final string
    int prefix_len = sizeof(prefix) - 1; // Exclude null terminator
    int suffix_len = sizeof(suffix) - 1; // Exclude null terminator
    int total_len = prefix_len + num_len + suffix_len;

    // Ensure the message buffer is large enough
    uchar msg[200] = {0}; // Adjust size if needed

    // Build the final string
    int pos = 0;

    // Copy prefix
    for (int i = 0; i < prefix_len; i++, pos++) {
        msg[pos] = prefix[i];
    }

    // Copy random number string
    for (int i = 0; i < num_len; i++, pos++) {
        msg[pos] = random_number_str[i];
    }

    // Copy suffix
    for (int i = 0; i < suffix_len; i++, pos++) {
        msg[pos] = suffix[i];
    }

    // Padding (Keccak pad10*1)
    int rate = 136; // For Keccak-256, rate is 1088 bits (136 bytes)
    msg[pos++] = 0x01; // Append '1' bit at the end of the message

    // Zero padding
    while (pos % rate != (rate - 1)) {
        msg[pos++] = 0;
    }
    
    msg[pos++] = 0x80; // Append '1' bit at the end of the block

    // Initialize the state array
    ulong state[25] = {0};

    // Absorb the message into the state
    int block_size = rate;
    int offset = 0;
    while (offset < pos) {
        // For each block
        for (int i = 0; i < block_size / 8; i++) {
            ulong temp = 0;
            for (int j = 0; j < 8; j++) {
                temp |= ((ulong)msg[offset + i * 8 + j]) << (8 * j);
            }
            state[i] ^= temp;
        }
        keccakf(state);
        offset += block_size;
    }

    // Squeeze the output
    uchar hash[32];
    int hash_output_len = 32;
    int hash_pos = 0;
    offset = 0;
    while (hash_pos < hash_output_len) {
        for (int i = 0; i < (block_size / 8) && hash_pos < hash_output_len; i++) {
            ulong t = state[i];
            for (int j = 0; j < 8 && hash_pos < hash_output_len; j++) {
                hash[hash_pos++] = (t >> (8 * j)) & 0xFF;
            }
        }
        if (hash_pos < hash_output_len) {
            keccakf(state);
        }
    }

    // Convert the first 4 bytes to hex and compare with the target prefix
    char hash_hex[9];
    const char hex_chars[17] = "0123456789abcdef";
    for (int i = 0; i < 4; i++) {
        hash_hex[i * 2] = hex_chars[(hash[i] >> 4) & 0x0F];
        hash_hex[i * 2 + 1] = hex_chars[hash[i] & 0x0F];
    }
    hash_hex[8] = '\\0';

    int match = 1;
    for (int i = 0; i < TARGET_LEN; i++) {
        if (hash_hex[i] != target_prefix[i]) {
            match = 0;
            break;
        }
    }
    output_flags[gid] = match ? 1 : 0;
}