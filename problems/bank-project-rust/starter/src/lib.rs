//! A set of bank accounts that grows over four levels.
//!
//! `cstudy submit` and the tests reach `Bank` as `bank::Bank`, so keep it re-exported here.

mod account;
mod bank;

pub use bank::Bank;
