const WORD_BITS: u32 = 32;

pub fn get_sum(a: i32, b: i32) -> i32 {
    // The 32-bit two's complement patterns of the inputs: `as u32` reinterprets the bits.
    let (x, y) = (a as u32, b as u32);
    let (mut result, mut carry) = (0_u32, 0_u32);
    for position in 0..WORD_BITS {
        let (bit_a, bit_b) = ((x >> position) & 1, (y >> position) & 1);
        result |= (bit_a ^ bit_b ^ carry) << position;
        carry = (bit_a & bit_b) | (carry & (bit_a ^ bit_b)); // carry out: at least two of the three bits
    }
    // A set sign bit means a negative value: reading the pattern as an i32 recovers it.
    result as i32
}
