use std::collections::{HashMap, HashSet};
use std::fs::File;
use std::io::{self, BufRead, Write};
use std::path::Path;

#[derive(PartialEq, Debug)]
pub struct CNF {
    pub num_vars: usize,
    pub num_clauses: usize,
    pub clauses: Vec<Vec<i32>>,
    pub comments: Vec<String>,
}

impl CNF {
    pub fn from_clauses(clauses: Vec<Vec<i32>>) -> Self {
        let max_var = clauses
            .iter()
            .map(|c| c.iter().map(|lit| lit.abs()).max().unwrap_or(0))
            .max()
            .unwrap_or(0) as usize;
        CNF {
            num_vars: max_var,
            num_clauses: clauses.len(),
            clauses,
            comments: Vec::new(),
        }
    }

    pub fn write_dimacs(&self, path: &Path) -> io::Result<()> {
        let mut file = File::create(path)?;

        // write comments
        for comment in &self.comments {
            writeln!(file, "c {}", comment)?;
        }

        // write header
        writeln!(file, "p cnf {} {}", self.num_vars, self.clauses.len())?;

        // write clauses
        for clause in &self.clauses {
            let clause_line: String = clause
                .iter()
                .map(|&lit| lit.to_string())
                .collect::<Vec<String>>()
                .join(" ");
            writeln!(file, "{} 0", clause_line)?;
        }

        Ok(())
    }

    /// Assuming dimacs comments like `165 Name`, extracts the ID and the name from the comments, keeping the order.
    pub fn get_names_from_comments(&self) -> Vec<(usize, String)> {
        self.comments
            .iter()
            .filter_map(|entry| {
                let parts: Vec<&str> = entry.splitn(2, ' ').collect();
                if let Ok(id) = parts[0].parse::<usize>() {
                    return Some((id, parts[1].to_string()));
                }
                None
            })
            .collect()
    }

    /// Adds a new clause to the CNF formula.
    ///
    /// # Arguments
    ///
    /// * `clause` - A vector of integers representing a clause, where each integer is a
    ///   literal (a positive or negative variable index).
    ///
    /// # Panics
    ///
    /// This function panics if any literal in the clause has an absolute value greater than
    /// `num_vars`, since variables are indexed from 1 to `num_vars`.
    ///
    /// # Example
    ///
    /// ```
    /// # use zampler_core::cnf::CNF;
    /// let mut cnf = CNF {
    ///     num_vars: 3,
    ///     num_clauses: 0,
    ///     clauses: Vec::new(),
    ///     comments: Vec::new(),
    /// };
    /// cnf.add_clause(vec![1, -2, 3]); // Valid clause
    /// ```
    pub fn add_clause(&mut self, clause: Vec<i32>) {
        for lit in &clause {
            assert!(lit.unsigned_abs() as usize <= self.num_vars);
        }
        self.clauses.push(clause);
        self.num_clauses += 1;
    }

    pub fn add_comment(&mut self, comment: String) {
        self.comments.push(comment);
    }

    /// Remaps variable IDs in both clauses and comments using the provided mapping.
    pub fn remap_variable_ids(&mut self, id_mapping: &HashMap<usize, usize>) {
        // Update num_vars to the highest new ID
        self.num_vars = *id_mapping.values().max().unwrap_or(&0);

        // Update clauses
        for clause in self.clauses.iter_mut() {
            for lit in clause.iter_mut() {
                let abs_lit = lit.unsigned_abs() as usize;
                if let Some(&new_id) = id_mapping.get(&abs_lit) {
                    *lit = lit.signum() * (new_id as i32);
                }
            }
        }

        // Update comments
        for comment in self.comments.iter_mut() {
            let parts: Vec<&str> = comment.splitn(2, ' ').collect();
            if let Ok(old_id) = parts[0].parse::<usize>() {
                if let Some(&new_id) = id_mapping.get(&old_id) {
                    *comment = format!("{} {}", new_id, parts[1]);
                }
            }
        }
    }
}

/// Parses a DIMACS CNF file and returns a `CNF` representation.
///
/// # Arguments
///
/// * `path` - A reference to a `Path` pointing to the DIMACS file.
///
/// # Returns
///
/// * `io::Result<CNF>` - A `CNF` structure containing the parsed number of variables,
///   number of clauses, list of clauses, and any comments found in the file.
///
/// # Format
///
/// The function expects a valid DIMACS file:
/// - Comment lines start with 'c' and are stored in `comments`.
/// - The problem line starts with 'p cnf' followed by the number of variables and clauses.
/// - Clauses consist of space-separated integers, ending with '0' (which is ignored).
///
/// # Errors
///
/// Returns an `Err` if the file cannot be opened or if any parsing step fails.
pub fn parse_dimacs(path: &Path) -> io::Result<CNF> {
    let file = File::open(path)?;
    let reader = io::BufReader::new(file);

    let mut num_vars = 0;
    let mut num_clauses = 0;
    let mut clauses = Vec::new();
    let mut comments = Vec::new();

    for line in reader.lines() {
        let line = line?;
        let line = line.trim();

        if line.starts_with("c") {
            comments.push(line[1..].trim().to_string()); // Store comments without 'c ' prefix
            continue;
        }

        if line.starts_with("p cnf") {
            let parts: Vec<&str> = line.split_whitespace().collect();
            num_vars = parts[2].parse().unwrap();
            num_clauses = parts[3].parse().unwrap();
        } else if !line.is_empty() {
            let clause: Vec<i32> = line
                .split_whitespace()
                .map(|s| s.parse().unwrap())
                .take_while(|&x| x != 0)
                .collect();
            clauses.push(clause);
        }
    }

    Ok(CNF {
        num_vars,
        num_clauses,
        clauses,
        comments,
    })
}

/// Unify the given CNFs such that variable IDs are consistent w.r.t. the unique names
/// This may cause new variables to be added to some CNFs, which is done with accompanying constraints
/// that ensure these variables are set to false, preserving the model count.
pub fn unify_variable_mappings(cnfs: &mut [CNF]) -> HashMap<String, usize> {
    let mut name_to_global_id: HashMap<String, usize> = HashMap::new();
    let mut global_id_to_name: HashMap<usize, String> = HashMap::new();
    let mut next_id = 1;

    // Collect unique variable names and assign global IDs
    for cnf in cnfs.iter() {
        for (_id, name) in cnf.get_names_from_comments() {
            if !name_to_global_id.contains_key(&name) {
                name_to_global_id.insert(name.clone(), next_id);
                global_id_to_name.insert(next_id, name);
                next_id += 1;
            }
        }
    }
    let max_var = next_id - 1;

    // Remap variables in each CNF and add constraints for missing variables
    for cnf in cnfs.iter_mut() {
        let names = cnf.get_names_from_comments();
        let local_to_global: HashMap<usize, usize> = names
            .iter()
            .map(|(local_id, name)| (*local_id, *name_to_global_id.get(name).unwrap()))
            .collect();
        cnf.remap_variable_ids(&local_to_global);
        cnf.num_vars = max_var;

        let variable_ids: HashSet<usize> = names
            .iter()
            .map(|(id, _name)| local_to_global[id])
            .collect();
        for new_var in 1..=max_var {
            if !variable_ids.contains(&new_var) {
                cnf.add_clause(vec![-(new_var as i32)]); // Add constraint to fix to false
                cnf.add_comment(new_var.to_string() + " " + &global_id_to_name[&new_var]);
            }
        }
    }

    name_to_global_id
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn test_from_clauses() {
        let clauses = vec![];
        let cnf = CNF::from_clauses(clauses);
        assert_eq!(cnf.num_vars, 0);
        assert_eq!(cnf.num_clauses, 0);

        let clauses = vec![vec![1, -2], vec![3]];
        let cnf = CNF::from_clauses(clauses);
        assert_eq!(cnf.num_vars, 3);
        assert_eq!(cnf.num_clauses, 2);
    }

    #[test]
    fn test_remap_variable_ids() {
        let mut cnf = CNF {
            num_vars: 3,
            num_clauses: 2,
            clauses: vec![vec![1, -2, 3], vec![-1, 2, -3]],
            comments: vec!["1 X".to_string(), "2 Y".to_string(), "3 Z".to_string()],
        };

        let id_mapping = HashMap::from([(1, 10), (3, 30)]);

        cnf.remap_variable_ids(&id_mapping);

        // Expected clauses after remapping
        let expected_clauses = vec![vec![10, -2, 30], vec![-10, 2, -30]];
        assert_eq!(cnf.clauses, expected_clauses);

        // Expected comments after remapping
        let expected_comments = vec!["10 X".to_string(), "2 Y".to_string(), "30 Z".to_string()];
        assert_eq!(cnf.comments, expected_comments);

        // num_vars should be updated to the highest new ID
        assert_eq!(cnf.num_vars, 30);
    }
}
