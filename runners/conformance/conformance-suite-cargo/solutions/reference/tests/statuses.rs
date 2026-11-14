//! One test for each status of a suite job.

use std::process;
use std::thread;
use std::time::Duration;

use probe::Probe;

#[test]
fn passes() {
    assert_eq!(Probe::new().ping(), "pong");
}

#[test]
fn fails_an_assertion() {
    assert_eq!(Probe::new().ping(), "ping");
}

#[test]
fn panics() {
    panic!("conformance failure");
}

#[test]
fn hangs() {
    loop {
        thread::sleep(Duration::from_secs(1));
    }
}

#[test]
fn aborts() {
    process::abort();
}

#[test]
fn prints() {
    println!("conformance output");
}

#[test]
#[ignore = "conformance reason"]
fn is_ignored() {}

#[test]
#[should_panic(expected = "conformance failure")]
fn panics_as_expected() {
    panic!("conformance failure");
}
