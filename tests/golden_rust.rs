// Golden Rust file for symbol extraction tests
pub struct Foo {}

impl Foo {
    pub fn new() -> Self {
        Foo {}
    }
    pub fn bar(&self) {}
}

pub enum MyEnum {
    A,
    B,
}

pub trait MyTrait {
    fn do_it(&self);
}

fn free_function() {}
