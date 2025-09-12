use clap::Parser;

use unify_dimacs::unify_dimacs;
pub mod cnf;
pub mod unify_dimacs;

#[derive(Parser)]
pub struct Cli {
    /// directory of dimacs files to be unified
    directory: std::path::PathBuf,
    /// overwrite dimacs files instead of creating a subfolder
    #[arg(long)]
    overwrite: bool,
}

fn main() {
    let args = Cli::parse();
    let _result = unify_dimacs(&args.directory, args.overwrite);
}
