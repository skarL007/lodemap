mod cli;
use shop_core::model::{item::Item, order};
use shop_core::prelude::*;
use clap::Parser;
use ::shop_core::util::money::Cents;

pub struct Config;

fn main() {
    let _ = shop_core::util::fmt_money();
}
