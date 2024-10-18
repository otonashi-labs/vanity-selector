import pyopencl as cl
import numpy as np
from web3 import Web3
w3 = Web3()


def get_kernel(
        target_hash, 
        string_prefix,
        string_suffix
    ):
    assert(len(target_hash) <= 8)
    hash_len = len(target_hash)
    with open("kernel_v0.cl", "r") as f:
        kernel_raw = f.read()
    
    kernel_raw = kernel_raw.replace("PYTHON_INJECTION_1", target_hash)
    kernel_raw = kernel_raw.replace("PYTHON_INJECTION_2", string_prefix)
    kernel_raw = kernel_raw.replace("PYTHON_INJECTION_3", string_suffix)
    kernel_raw = kernel_raw.replace("PYTHON_INJECTION_4", str(hash_len))

    return kernel_raw

def get_selector(
        iterations,
        num_random_numbers,
        target_prefix,
        string_prefix,
        string_suffix
    ):
    print(f"[VANITY-SELECTOR] Started")

    NUM_RANDOM_NUMBERS = num_random_numbers

    kernel_code = get_kernel(
        target_hash = target_prefix, 
        string_prefix = string_prefix,
        string_suffix = string_suffix
    )

    platforms = cl.get_platforms()
    devices = platforms[0].get_devices(device_type=cl.device_type.GPU)

    if not devices:
        devices = platforms[0].get_devices(device_type=cl.device_type.CPU)

    context = cl.Context(devices=devices)
    queue = cl.CommandQueue(context)

    for i in range(iterations):
        random_numbers = np.random.randint(0, 2**32 - 1, size=NUM_RANDOM_NUMBERS, dtype=np.uint32)

        output_flags = np.zeros(NUM_RANDOM_NUMBERS, dtype=np.uint8)

        mf = cl.mem_flags
        input_buf = cl.Buffer(context, mf.READ_ONLY | mf.COPY_HOST_PTR, hostbuf=random_numbers)
        output_buf = cl.Buffer(context, mf.WRITE_ONLY, output_flags.nbytes)

        program = cl.Program(context, kernel_code).build()

        global_size = (NUM_RANDOM_NUMBERS,)
        local_size = None 

        program.keccak_hash(queue, global_size, local_size, input_buf, output_buf)

        cl.enqueue_copy(queue, output_flags, output_buf)
        queue.finish()

        matches = np.where(output_flags == 1)[0]

        if len(matches) > 0:
            print("[iter-{i}] Found matches:")
            for idx in matches:
                print(f"[iter-{i}]  number: {random_numbers[idx]}, Index: {idx}")
                selector = w3.keccak(text=f"{string_prefix}{random_numbers[idx]}{string_suffix}").hex()[:10]
                print(f"[iter-{i}] Selector: {selector}")
                print()
        else:
            pass
            if i % 10 == 0:
                print(f"[iter-{i}] No matches found.")

def main():
    get_selector(
        iterations = 43,
        num_random_numbers = 100_000_000,
        target_prefix = "0000000",
        string_prefix = "CodeIsLawZ",
        string_suffix = "(address,address[],address[],uint256[])"
    )

if (__name__ == "__main__"):
    main()