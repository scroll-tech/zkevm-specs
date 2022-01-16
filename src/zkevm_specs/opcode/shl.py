from ..encoding import U8, u8s_to_u64s, is_circuit_code, LookupTable
from typing import Sequence


class BitslevelTable(LookupTable):
    def __init__(self):
        super().__init__(["powtag", "value"])
        for level in range(0, 9):
            for idx in range(0, 1 << level):
                self.add_row(powtag=level, value=idx)


class Pow64Table(LookupTable):
    def __init__(self):
        super().__init__(["value", "value_pow", "value_depow"])
        for idx in range(64):
            self.add_row(
                value=idx,
                value_pow=1 << idx,
                value_depow=(1 << (64 - idx))
            )


def shl_common(
    a: Sequence[U8],
    b: Sequence[U8],
    shift: Sequence[U8],
    a_slice_front: Sequence[U8],
    a_slice_back: Sequence[U8],
    shift_div_by_64,
    shift_mod_by_64_decpow,
    shift_mod_by_64_div_by_8,
    shift_mod_by_64_pow,
    shift_mod_by_8,
    bitsleveltable: BitslevelTable,
    pow64Table: Pow64Table,
):
    assert len(a) == len(b) == len(shift) == 32
    assert len(a_slice_back) == len(a_slice_front) == 32

    a_digits = u8s_to_u64s(a)
    b_digits = u8s_to_u64s(b)
    a_slice_back_digits = u8s_to_u64s(a_slice_back)
    a_slice_front_digits = u8s_to_u64s(a_slice_front)

    # shift_constraints
    for idx in range(1, 32):
        assert shift[idx] == 0

    # shl_constraints
    for transplacement in range(4):
        if shift_div_by_64 == transplacement:
            select_transplacement_polynomial = 1
        else:
            select_transplacement_polynomial = 0
        for idx in range(4 - transplacement):
            tmp_idx = idx + transplacement
            if idx == 0:
                merge_a = a_slice_front_digits[idx] * shift_mod_by_64_pow
            else:
                merge_a = a_slice_front_digits[idx] * shift_mod_by_64_pow + a_slice_back_digits[idx - 1]
            assert (merge_a - b_digits[tmp_idx]) * select_transplacement_polynomial == 0
        for idx in range(0, transplacement):
            assert select_transplacement_polynomial * b_digits[idx] == 0

    # shift_split_constraints
    shift_mod_by_64 = shift_mod_by_64_div_by_8 * 8 + shift_mod_by_8
    assert shift[0] == shift_div_by_64 * 64 + shift_mod_by_64

    # merge_constraints
    for idx in range(4):
        assert a_slice_back_digits[idx] + a_slice_front_digits[idx] * shift_mod_by_64_decpow == a_digits[idx]
    
    # slice_equal_to_zero_constraints
    for digit_transplacement in range(8):
        if shift_mod_by_64_div_by_8 == digit_transplacement:
            select_transplacement_polynomial = 1
        else:
            select_transplacement_polynomial = 0
        for virtual_idx in range(4):
            for idx in range(digit_transplacement + 1, 8):
                now_idx = virtual_idx * 8 + idx
                assert select_transplacement_polynomial * a_slice_front[now_idx] == 0
            for idx in range(8 - digit_transplacement, 8):
                now_idx = virtual_idx * 8 + idx
                assert select_transplacement_polynomial * a_slice_back[now_idx] == 0

    # slice_bits_lookups
    for virtual_idx in range(4):
        slice_bits_polynomial = [0] * 2
        for digit_transplacement in range(8):
            if shift_mod_by_64_div_by_8 == digit_transplacement:
                select_transplacement_polynomial = 1
            else:
                select_transplacement_polynomial = 0
            now_idx = virtual_idx * 8 + digit_transplacement
            slice_bits_polynomial[0] += select_transplacement_polynomial * a_slice_front[now_idx]
            now_idx = virtual_idx * 8 + 7 - digit_transplacement
            slice_bits_polynomial[1] += select_transplacement_polynomial * a_slice_back[now_idx]

        assert bitsleveltable.lookup(
            powtag = shift_mod_by_8,
            value = slice_bits_polynomial[0]
        )
        assert bitsleveltable.lookup(
            powtag = 8 - shift_mod_by_8,
            value = slice_bits_polynomial[1]
        )
    
    # pow_lookups
    assert pow64Table.lookup(
        value=shift_mod_by_64,
        value_pow=shift_mod_by_64_pow,
        value_depow=shift_mod_by_64_decpow
    )

    # given_value_lookups
    assert bitsleveltable.lookup(
        powtag=2,
        value=shift_div_by_64
    )
    assert bitsleveltable.lookup(
        powtag=3,
        value=shift_mod_by_64_div_by_8
    )
    assert bitsleveltable.lookup(
        powtag=3,
        value=shift_mod_by_8
    )


@is_circuit_code
def check_shl(
    a: Sequence[U8],
    b: Sequence[U8],
    shift: Sequence[U8],
    a_slice_front: Sequence[U8],
    a_slice_back: Sequence[U8],
    shift_div_by_64,
    shift_mod_by_64_decpow,
    shift_mod_by_64_div_by_8,
    shift_mod_by_64_pow,
    shift_mod_by_8,
    bits_level_table: BitslevelTable,
    pow64_table: Pow64Table
):
    shl_common(
        a,
        b,
        shift,
        a_slice_front,
        a_slice_back,
        shift_div_by_64,
        shift_mod_by_64_decpow,
        shift_mod_by_64_div_by_8,
        shift_mod_by_64_pow,
        shift_mod_by_8,
        bits_level_table,
        pow64_table
    )