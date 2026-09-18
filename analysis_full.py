"""
Influencer Collab A/B Test — full pipeline
Consolidated from a step-by-step build in Google Colab.
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from statsmodels.stats.proportion import proportions_ztest, proportion_confint

np.random.seed(42)
N = 60000

# ---- Randomized assignment ----
group = np.random.choice(["organic", "collab"], size=N, p=[0.5, 0.5])
content_format = np.random.choice(["reel", "static"], size=N, p=[0.5, 0.5])

tier = np.full(N, "none", dtype=object)
collab_mask = group == "collab"
tier[collab_mask] = np.random.choice(
    ["nano", "micro", "macro"], size=collab_mask.sum(), p=[0.33, 0.33, 0.34]
)

# ---- Click-through model (ground truth, chosen deliberately) ----
ctr_lookup = {
    ("organic", "static", "none"): 0.055,
    ("organic", "reel", "none"): 0.065,
    ("collab", "static", "nano"): 0.060,
    ("collab", "static", "micro"): 0.070,
    ("collab", "static", "macro"): 0.085,
    ("collab", "reel", "nano"): 0.075,
    ("collab", "reel", "micro"): 0.110,
    ("collab", "reel", "macro"): 0.095,
}
base_ctr = np.array(
    [ctr_lookup[(g, f, t)] for g, f, t in zip(group, content_format, tier)]
)
clicked = np.random.binomial(1, base_ctr)

# ---- Conversion-given-click model ----
p_convert_given_click = np.where(group == "collab", 0.205, 0.180)
noise = np.random.normal(0, 0.01, size=N)
p_convert_given_click = np.clip(p_convert_given_click + noise, 0.01, 0.99)

converted = np.zeros(N, dtype=int)
click_idx = clicked == 1
converted[click_idx] = np.random.binomial(1, p_convert_given_click[click_idx])

# ---- Assemble dataset ----
df = pd.DataFrame({
    "user_id": [f"U{i:06d}" for i in range(N)],
    "group": group,
    "content_format": content_format,
    "influencer_tier": tier,
    "clicked": clicked,
    "converted": converted,
})
df.to_csv("influencer_ab_test.csv", index=False)

# ---- Analysis ----
organic = df[df.group == "organic"]
collab = df[df.group == "collab"]

# Overall conversion test
n_o, x_o = len(organic), organic.converted.sum()
n_c, x_c = len(collab), collab.converted.sum()
stat, pval = proportions_ztest(count=[x_c, x_o], nobs=[n_c, n_o])
ci_o = proportion_confint(x_o, n_o, alpha=0.05, method="wilson")
ci_c = proportion_confint(x_c, n_c, alpha=0.05, method="wilson")

print(f"Organic: {x_o/n_o*100:.2f}% (95% CI {ci_o[0]*100:.2f}-{ci_o[1]*100:.2f}%)")
print(f"Collab: {x_c/n_c*100:.2f}% (95% CI {ci_c[0]*100:.2f}-{ci_c[1]*100:.2f}%)")
print(f"z={stat:.3f}, p={pval:.5f}")

# CTR test
n_o_ctr, x_o_ctr = len(organic), organic.clicked.sum()
n_c_ctr, x_c_ctr = len(collab), collab.clicked.sum()
stat_ctr, pval_ctr = proportions_ztest(count=[x_c_ctr, x_o_ctr], nobs=[n_c_ctr, n_o_ctr])
print(f"\nCTR — organic: {x_o_ctr/n_o_ctr*100:.2f}% | collab: {x_c_ctr/n_c_ctr*100:.2f}%")
print(f"z={stat_ctr:.3f}, p={pval_ctr:.5f}")

# CVR-given-click test
clicked_organic = organic[organic.clicked == 1]
clicked_collab = collab[collab.clicked == 1]
n_o_cvr, x_o_cvr = len(clicked_organic), clicked_organic.converted.sum()
n_c_cvr, x_c_cvr = len(clicked_collab), clicked_collab.converted.sum()
stat_cvr, pval_cvr = proportions_ztest(count=[x_c_cvr, x_o_cvr], nobs=[n_c_cvr, n_o_cvr])
print(f"\nCVR|click — organic: {x_o_cvr/n_o_cvr*100:.2f}% | collab: {x_c_cvr/n_c_cvr*100:.2f}%")
print(f"z={stat_cvr:.3f}, p={pval_cvr:.5f}")

# Segment breakdown
seg = collab.groupby(["content_format", "influencer_tier"]).agg(
    n=("clicked", "size"), ctr=("clicked", "mean"), cvr=("converted", "mean")
).reset_index().sort_values("ctr", ascending=False)
seg["ctr"] = (seg["ctr"] * 100).round(2)
seg["cvr"] = (seg["cvr"] * 100).round(2)
print("\nSegment breakdown (collab group):")
print(seg.to_string(index=False))

# Chart
rates = [x_o/n_o*100, x_c/n_c*100]
plt.bar(["Organic", "Collab"], rates, color=["#94a3b8", "#6366f1"])
plt.ylabel("Conversion rate (%)")
plt.title("Overall conversion: Organic vs Collab")
plt.savefig("results_chart.png", dpi=150)
print("\nSaved results_chart.png")
