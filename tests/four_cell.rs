#[allow(unused)]
fn main(){
    println!("{:?}", (||{
        2+2
    })());
}    