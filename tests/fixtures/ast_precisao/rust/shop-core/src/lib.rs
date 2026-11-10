// mod fantasma;
/* mod fantasma2; */
pub mod model;
pub mod util;
mod internal;
pub mod prelude;
#[cfg(test)]
mod tests;
#[path = "weird/other.rs"]
mod outro;
mod em_linha {
    pub fn f() {}
}
pub use model::Item;
const S: &str = "mod fantasma;";
