use cs_support::ListNode;

/// A non-negative integer as little-endian base 2^32 limbs; the standard library has no big
/// integer. Every operation walks all limbs, as a big-integer library's would.
struct BigUint(Vec<u32>);

impl BigUint {
    /// `self = self * factor + addend`.
    fn mul_add(&mut self, factor: u32, addend: u32) {
        let mut carry = u64::from(addend);
        for limb in &mut self.0 {
            let product = u64::from(*limb) * u64::from(factor) + carry;
            *limb = product as u32;
            carry = product >> 32;
        }
        if carry > 0 {
            self.0.push(carry as u32);
        }
    }

    fn add(&mut self, other: &BigUint) {
        if self.0.len() < other.0.len() {
            self.0.resize(other.0.len(), 0);
        }
        let mut carry = 0;
        for (i, limb) in self.0.iter_mut().enumerate() {
            let sum = u64::from(*limb) + u64::from(other.0.get(i).copied().unwrap_or(0)) + carry;
            *limb = sum as u32;
            carry = sum >> 32;
        }
        if carry > 0 {
            self.0.push(carry as u32);
        }
    }

    /// `self = self / divisor`, returning the remainder.
    fn div_rem(&mut self, divisor: u32) -> u32 {
        let mut remainder = 0;
        for limb in self.0.iter_mut().rev() {
            let current = (remainder << 32) | u64::from(*limb);
            *limb = (current / u64::from(divisor)) as u32;
            remainder = current % u64::from(divisor);
        }
        while self.0.last() == Some(&0) {
            self.0.pop();
        }
        remainder as u32
    }

    fn is_zero(&self) -> bool {
        self.0.is_empty()
    }
}

pub fn add_two_numbers(
    l1: Option<Box<ListNode>>,
    l2: Option<Box<ListNode>>,
) -> Option<Box<ListNode>> {
    let mut total = to_int(l1.as_deref());
    total.add(&to_int(l2.as_deref()));
    let mut dummy = Box::new(ListNode::new(0));
    let mut tail = &mut dummy;
    loop {
        let digit = total.div_rem(10);
        tail = tail.next.insert(Box::new(ListNode::new(digit as i32)));
        if total.is_zero() {
            return dummy.next;
        }
    }
}

fn to_int(head: Option<&ListNode>) -> BigUint {
    let digits: Vec<i32> = std::iter::successors(head, |node| node.next.as_deref())
        .map(|node| node.val)
        .collect();
    // Horner's rule from the most significant digit.
    let mut value = BigUint(Vec::new());
    for digit in digits.into_iter().rev() {
        value.mul_add(10, digit as u32);
    }
    value
}
