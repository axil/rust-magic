//! ```cargo
//! [dependencies]
//! time = "0.1.42"
//! ```
extern crate time;

#[allow(unused)]
fn main(){
    println!("{}", time::now().rfc822z());
}