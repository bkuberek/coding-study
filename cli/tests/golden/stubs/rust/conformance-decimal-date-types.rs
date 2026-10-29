// Conformance: decimal and date round-trip. Statement: .statements/conformance-decimal-date-types.md. Run: cstudy test conformance-decimal-date-types

use chrono::NaiveDate;
use rust_decimal::Decimal;

pub struct TypeEcho {}

impl TypeEcho {
    pub fn new(label: String) -> Self {
        TypeEcho {}
    }

    pub fn echo_decimal(&mut self, value: Decimal) -> Decimal {
        todo!()
    }

    pub fn echo_date(&mut self, value: NaiveDate) -> NaiveDate {
        todo!()
    }

    pub fn echo_decimal_array(&mut self, value: Vec<Decimal>) -> Vec<Decimal> {
        todo!()
    }

    pub fn echo_date_array(&mut self, value: Vec<NaiveDate>) -> Vec<NaiveDate> {
        todo!()
    }

    pub fn echo_decimal_matrix(&mut self, value: Vec<Vec<Decimal>>) -> Vec<Vec<Decimal>> {
        todo!()
    }

    pub fn echo_date_matrix(&mut self, value: Vec<Vec<NaiveDate>>) -> Vec<Vec<NaiveDate>> {
        todo!()
    }

    pub fn echo_decimal_list(&mut self, value: Vec<Decimal>) -> Vec<Decimal> {
        todo!()
    }

    pub fn echo_date_list(&mut self, value: Vec<NaiveDate>) -> Vec<NaiveDate> {
        todo!()
    }
}
