import os
from pathlib import Path

import numpy as np
import matplotlib.pyplot as plt


OUTPUT_DIR = Path(os.getenv("OUTPUT_DIR", "output")) / "plots"
OUTPUT_DIR.mkdir(exist_ok=True, parents=True)

n = 10
r_vals = np.linspace(0, 1, 1000)
nr_vals = n * r_vals
frac = nr_vals - np.floor(nr_vals)

var_custom = frac * (1 - frac)
var_binom = nr_vals * (1 - r_vals)
ratio = np.divide(
    var_custom, var_binom, out=np.zeros_like(var_custom), where=var_binom != 0
)

plt.figure(figsize=(5, 2))
plt.plot(r_vals, var_binom, label="Alg. 1", linewidth=2)  # linestyle="--"
plt.plot(r_vals, var_custom, label="Alg. 2", linewidth=2)
plt.xlabel("Ratio $r$")
plt.ylabel("Variance($k$)")
# plt.title(f"Variance Comparison ($n = {n}$)")
plt.legend(loc="upper right")
plt.grid(True)
plt.tight_layout()
# plt.show()
path = OUTPUT_DIR / "variance.pdf"
plt.savefig(path)
print("Saved to", path)

# # Optional: ratio plot
# plt.figure(figsize=(10, 4))
# plt.plot(r_vals, ratio, label="Var(custom) / Var(Binomial)", color="purple")
# plt.axhline(1, color="gray", linestyle="--")
# plt.xlabel("r")
# plt.ylabel("Variance Ratio")
# plt.title(f"Variance Ratio (n = {n})")
# plt.grid(True)
# plt.show()
