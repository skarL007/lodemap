pub fn p() -> i32 { 1 }

#[cfg(test)]
mod tests {
    // dentro de `mod tests { }` o super e o proprio arquivo, nao o util/mod.rs
    use super::*;
    use super::p;
    #[test]
    fn t() { assert_eq!(p(), 1); }
}
