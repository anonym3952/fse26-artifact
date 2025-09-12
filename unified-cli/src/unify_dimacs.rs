use std::{fs, io, path::Path};

use crate::cnf::{parse_dimacs, unify_variable_mappings};
const DIMACS_FILE_EXT: &str = "dimacs";

/// Unify all DIMACS files in the given directory such that variable IDs are consistent over all files.
/// This may cause new variables to be added to some files, which is done with accompanying constraints
/// that ensure these variables are set to false, preserving the model count.
pub fn unify_dimacs(directory: &Path, overwrite: bool) -> io::Result<()> {
    let mut cnfs = Vec::new();
    let mut file_paths = Vec::new();

    // Collect all CNF files in the directory
    for entry in fs::read_dir(directory)? {
        let entry = entry?;
        let path = entry.path();
        if path.extension().map_or(false, |ext| ext == DIMACS_FILE_EXT) {
            cnfs.push(parse_dimacs(&path)?);
            file_paths.push(path);
        }
    }

    if cnfs.is_empty() {
        return Err(io::Error::new(
            io::ErrorKind::NotFound,
            "No DIMACS files found",
        ));
    }

    // Perform variable unification
    let name_to_global_id = unify_variable_mappings(&mut cnfs);
    assert_eq!(
        name_to_global_id.len(),
        *name_to_global_id.values().max().unwrap_or(&0)
    );
    println!("number of unified variables: {}", name_to_global_id.len());

    let unified_dir;
    if !overwrite {
        // Create a subfolder for unified files
        unified_dir = directory.join("unified");
        fs::create_dir_all(&unified_dir)?;
    } else {
        unified_dir = directory.join("");
    }

    // Write the updated CNF files
    for (cnf, path) in cnfs.iter().zip(file_paths.iter()) {
        let file_name = path.file_name().unwrap(); // Safe because we collected valid files
        let new_path = unified_dir.join(file_name);
        cnf.write_dimacs(&new_path)?;
    }

    Ok(())
}
