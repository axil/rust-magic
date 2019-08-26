//! ```cargo
//! [dependencies]
//! time = "0.1.42"
//! ndarray = "0.12.1"
//! ```
extern crate time;
extern crate ndarray;
#[allow(unused)]
fn main(){
    println!("{:?}", (||{
        (time::now().rfc822z().to_string(), 
         ndarray::Array::from_vec(vec![1., 2., 3.]).sum())
    })());
}
