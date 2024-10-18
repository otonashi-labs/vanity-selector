import pyopencl as cl
import numpy as np
from web3 import Web3
w3 = Web3()

def get_kernel(
        target_hash, 
        string_prefix,
        string_suffix,
        string_len,
        process_seed
    ):
    assert(len(target_hash) <= 8)
    hash_len = len(target_hash)
    with open("kernel_v2.cl", "r") as f:
        kernel_raw = f.read()
    
    kernel_raw = kernel_raw.replace("PYTHON_INJECTION_1", target_hash)
    kernel_raw = kernel_raw.replace("PYTHON_INJECTION_2", string_prefix)
    kernel_raw = kernel_raw.replace("PYTHON_INJECTION_3", string_suffix)
    kernel_raw = kernel_raw.replace("PYTHON_INJECTION_4", str(hash_len))
    kernel_raw = kernel_raw.replace("PYTHON_INJECTION_5", str(string_len))
    kernel_raw = kernel_raw.replace("PYTHON_INJECTION_6", str(process_seed) + "UL")

    return kernel_raw

def lcg_rand(seed, process_seed):
    seed = int(seed)
    seed = (seed * process_seed * 6364136223846793005 + 1) & 0xffffffffffffffff  # 64-bit modulus
    return seed
    
def rand_mod(seed, process_seed, mod):  
    seed = lcg_rand(seed, process_seed)  
    return seed % mod, seed  
  
def generate_random_string(gid, string_len, process_seed):  
    seed = gid
    random_string = ''  
    charset = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"  
    for _ in range(string_len):  
        rand_num, seed = rand_mod(seed, process_seed, 62)  
        random_string += charset[rand_num]  
    return random_string  


def get_selector(
        iterations,
        num_work_items,
        target_prefix,
        string_prefix,
        string_suffix,
        string_len
    ):
    print(f"[VANITY-SELECTOR] Started")

    NUM_WORK_ITEMS = num_work_items

    platforms = cl.get_platforms()
    devices = platforms[0].get_devices(device_type=cl.device_type.GPU)

    if not devices:
        devices = platforms[0].get_devices(device_type=cl.device_type.CPU)

    context = cl.Context(devices=devices)
    queue = cl.CommandQueue(context)

    for i in range(iterations):
        process_seed = np.random.randint(10**3, 10**6)
        kernel_code = get_kernel(
            target_hash = target_prefix, 
            string_prefix = string_prefix,
            string_suffix = string_suffix,
            string_len = string_len,
            process_seed = process_seed
        )

        output_flags = np.zeros(NUM_WORK_ITEMS, dtype=np.uint8)

        mf = cl.mem_flags
        output_buf = cl.Buffer(context, mf.WRITE_ONLY, output_flags.nbytes)

        program = cl.Program(context, kernel_code).build()

        global_size = (NUM_WORK_ITEMS,)
        local_size = None 

        program.keccak_hash(queue, global_size, local_size, output_buf)

        cl.enqueue_copy(queue, output_flags, output_buf)
        queue.finish()

        matches = np.where(output_flags == 1)[0]

        if len(matches) > 0:
            print("[iter-{i}] Found matches:")
            for idx in matches:
                random_string = generate_random_string(idx, string_len, process_seed) 
                print(f"[iter-{i}] rand_str: {random_string}")
                selector = w3.keccak(text=f"{string_prefix}{random_string}{string_suffix}").hex()[:10]
                print(f"[iter-{i}] Selector: {selector}")
                print()
        else:
            pass
            if i % 10 == 0:
                print(f"[iter-{i}] No matches found.")

def main():
    get_selector(
        iterations = 40,
        num_work_items = 100_000_000,
        target_prefix = "deadfac",
        string_prefix = "rebalance_",
        string_suffix = "((int24,int24,uint128,uint128,uint128),(bool,int256,uint160,int256),(address,int24,int24,uint256,uint256,uint256,uint256))",
        string_len = 10
    )

if (__name__ == "__main__"):
    main()