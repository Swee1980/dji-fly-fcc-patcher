#!/usr/bin/env python3
"""
Patches libsdk_jni.so to force FCC area code ("US").

Two patch points:
  1. AreaCodeLogic::UpdateAreaCode - replaces area_code arg (x4) upstream
  2. wlm_set_country_code - replaces country_code arg (x1) at WLM command level
"""

import struct
import sys
from pathlib import Path

import lief
from capstone import CS_ARCH_ARM64, CS_MODE_ARM, Cs

# libc++ __ndk1 SSO string "US" (24 bytes, 64-bit)
# byte 0 = (len << 1) | is_long = 0x04, then "US\0", zero-padded
US_SSO_STRING = bytes([0x04, 0x55, 0x53, 0x00]) + b'\x00' * 20

SYM_UPDATE_AREA_CODE = (
    '_ZN3uav3sdk13AreaCodeLogic14UpdateAreaCodeEjjRKNS0_16AreaCode'
    'StrategyERKNSt6__ndk112basic_stringIcNS5_11char_traitsIcEENS5'
    '_9allocatorIcEEEE'
)
SYM_WLM_SET_CC = (
    '_ZN3uav4core20wlm_set_country_codeERKNSt6__ndk112basic_string'
    'IcNS1_11char_traitsIcEENS1_9allocatorIcEEEE'
)


def encode_adrp(rd, pc, target_page):
    pc_page = pc & ~0xFFF
    target_p = target_page & ~0xFFF
    offset = ((target_p - pc_page) >> 12) & 0x1FFFFF
    immlo = offset & 0x3
    immhi = (offset >> 2) & 0x7FFFF
    return struct.pack('<I', 0x90000000 | (immlo << 29) | (immhi << 5) | rd)


def encode_add_imm(rd, rn, imm12):
    return struct.pack('<I', 0x91000000 | (imm12 << 10) | (rn << 5) | rd)


def encode_b(pc, target):
    delta = target - pc
    assert -0x8000000 <= delta <= 0x7FFFFFC, \
        f"branch out of range: 0x{pc:x} -> 0x{target:x} ({delta})"
    return struct.pack('<I', 0x14000000 | ((delta >> 2) & 0x3FFFFFF))


def encode_ldr_x(rt, rn):
    return struct.pack('<I', 0xF9400000 | (rn << 5) | rt)


def find_cave(data, near, size=48):
    """Find the closest zero-filled region of at least `size` bytes."""
    caves = []
    run_start = None
    for i in range(len(data)):
        if data[i] == 0:
            if run_start is None:
                run_start = i
        else:
            if run_start is not None and i - run_start >= size:
                aligned = (run_start + 15) & ~15
                if aligned + size <= i:
                    caves.append(aligned)
            run_start = None
    if not caves:
        return None
    caves.sort(key=lambda a: abs(a - near))
    return caves[0]


def resolve(binary, name):
    for sym in binary.exported_symbols:
        if sym.name == name:
            return sym.value
    return None


def patch(src, dst):
    print(f"[*] Loading {src}")
    binary = lief.parse(str(src))
    data = bytearray(src.read_bytes())
    md = Cs(CS_ARCH_ARM64, CS_MODE_ARM)

    ua_addr = resolve(binary, SYM_UPDATE_AREA_CODE)
    wlm_addr = resolve(binary, SYM_WLM_SET_CC)
    assert ua_addr and wlm_addr, "target symbols not found"
    print(f"[*] UpdateAreaCode @ 0x{ua_addr:x}")
    print(f"[*] wlm_set_country_code @ 0x{wlm_addr:x}")

    first = list(md.disasm(bytes(data[ua_addr:ua_addr+4]), ua_addr))
    assert first[0].mnemonic == 'stp', f"unexpected prologue: {first[0].mnemonic}"

    cave = find_cave(data, ua_addr)
    assert cave is not None, "no code cave found"
    print(f"[*] Code cave @ 0x{cave:x}")

    # place SSO string at cave start
    data[cave:cave + len(US_SSO_STRING)] = US_SSO_STRING
    us_page = cave & ~0xFFF
    us_off = cave & 0xFFF
    hook = cave + len(US_SSO_STRING)

    # --- patch 1: UpdateAreaCode trampoline ---
    # x4 = &area_code (5th arg). Replace with pointer to our "US" string.
    # Trampoline: run saved prologue insn, load x4, jump back.
    saved = data[ua_addr:ua_addr + 4]
    tramp = bytearray()
    tramp += saved
    tramp += encode_adrp(4, hook + 4, us_page)
    tramp += encode_add_imm(4, 4, us_off)
    tramp += encode_b(hook + 12, ua_addr + 4)
    data[hook:hook + len(tramp)] = tramp
    data[ua_addr:ua_addr + 4] = encode_b(ua_addr, hook)
    print(f"[*] Patched UpdateAreaCode -> trampoline @ 0x{hook:x}")

    # --- patch 2: wlm_set_country_code ---
    # 24-byte thunk. Keep insns [0],[1],[5]; replace [2],[3],[4].
    # [2] adrp x1, us_page   (was: mov x1, x0)
    # [3] add  x1, x1, off   (was: ldr x8, [x8])
    # [4] ldr  x0, [x8]      (was: mov x0, x8 — fused with old [3])
    p2 = bytearray()
    p2 += encode_adrp(1, wlm_addr + 8, us_page)
    p2 += encode_add_imm(1, 1, us_off)
    p2 += encode_ldr_x(0, 8)
    data[wlm_addr + 8:wlm_addr + 20] = p2
    print(f"[*] Patched wlm_set_country_code insns [2-4]")

    # verify
    for insn in md.disasm(bytes(data[wlm_addr:wlm_addr+24]), wlm_addr):
        print(f"    {insn.address:x}: {insn.mnemonic} {insn.op_str}")

    Path(dst).write_bytes(data)
    print(f"[*] Wrote {dst}")


if __name__ == '__main__':
    if len(sys.argv) != 3:
        print(f"Usage: {sys.argv[0]} <input.so> <output.so>")
        sys.exit(1)
    patch(Path(sys.argv[1]), Path(sys.argv[2]))
