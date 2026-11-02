
# Test Lineup Creation
# This file will run a test with test data from 10-18-2026. 
# It will only run a small subset of all brute for combinations. This is a simple demonstration
import pandas as pd
import re
import datetime
from datetime import datetime, timedelta
import numpy as np
from pathlib import Path
from itertools import combinations
import math

pd.options.display.max_rows = 1000
pd.options.display.max_columns = 100
    

# Clean DK names by removing suffixes
def clean_name(name):
    if pd.isna(name):
        return name
    
    # Convert to string and normalize
    cleaned = str(name).strip()
    
    # Remove common suffixes (case insensitive)
    suffixes = r'\b(Jr\.?|Sr\.?|III|II|IV|V)\b'
    cleaned = re.sub(suffixes, '', cleaned, flags=re.IGNORECASE)

    # Handle common apostrophe variations (normalize them all)
    # Replace curly apostrophes, straight quotes, etc. with standard apostrophe
    cleaned = re.sub(r"[''`]", "'", cleaned)
    
    # Remove all punctuation EXCEPT apostrophes (keep De'Von as DeVon after next step)
    cleaned = re.sub(r"[^A-Za-z' ]+", '', cleaned)
    
    # Now remove apostrophes to standardize (De'Von -> DeVon)
    cleaned = cleaned.replace("'", "")
    
    # Collapse multiple spaces and trim
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    
    # Convert to lowercase for consistent matching
    cleaned = cleaned.lower()
    
    return cleaned

# Clean the position column to remove /Flex
def clean_position(pos):
    if pd.isna(pos):
        return pos
    return pos.replace('/Flex', '')


current_path = Path.cwd()
DATA_DIR = current_path / "sample_data"
date = "2026-10-18"

def get_weekly_salaries(date=date, data_dir=DATA_DIR):
    """
    Load weekly DFS salary and projection data for the given Sunday.
    Returns:
        DK_salaries (DataFrame): DraftKings salaries.
        Vegas_projection (DataFrame): Vegas projections.
        FFA_projections (DataFrame): FFA projections.
    """
    
    DK_salaries = pd.read_csv(
        data_dir / "contest_salaries_draftkings" / f"DKSalaries_{date}.csv" )

    FFA_projections = pd.read_csv(
        data_dir / "projections" / "ffa" / f"ffa_projections_{date}.csv")

    try:
        Vegas_projection = pd.read_csv(
            data_dir / f"vegas_ppr_proj_{date}.csv")
    except FileNotFoundError:
        Vegas_projection = pd.DataFrame(columns=["Name", "Projection"])

    return DK_salaries, Vegas_projection, FFA_projections

def get_dst_projections(Print = False, date=date):
    DST_projections = get_weekly_salaries(date)[2]
    DST_projections = DST_projections[DST_projections['position'] == 'DST']
    DST_projections = DST_projections[['player', 'points']]
    DST_projections = DST_projections.rename(columns={'points': 'Projection', 'player': 'Name'})
    
    return DST_projections
    

def clean_weekly_data(DK_salaries, Vegas_projection, FFA_projections, Print=False):
    Vegas_projection['Name_Clean'] = Vegas_projection['Name'].apply(clean_name)
    DK_salaries['Name_Clean'] = DK_salaries['Name'].apply(clean_name)
    DK_salaries['Roster Position'] = DK_salaries['Position'].apply(clean_position)
    FFA_projections['Name_Clean'] = FFA_projections['player'].apply(clean_name)

    if Print:
        print(DK_salaries.head(1))
        print(Vegas_projection.head(1))
        print(FFA_projections.head(1))

    return DK_salaries, Vegas_projection, FFA_projections

def merge_weekly_data(DK_salaries, Vegas_projection, FFA_projections, DST_projections, Print=False):
    """Create a merged DataFrame containing DK salaries, Vegas projections, FFA projections, and DST projections."""
    merged_df = (
        DK_salaries
        .merge(Vegas_projection[['Name_Clean', 'Projection']], left_on='Name_Clean', right_on='Name_Clean', how='left')
        .merge(DST_projections, left_on='Name_Clean', right_on='Name', how='left')
        .merge(FFA_projections[['Name_Clean', 'points']], left_on='Name_Clean', right_on='Name_Clean', how='left')
    )
    
    # combine into a single Projection column (prefer Vegas proj, fall back to FFA proj, then DST proj for DST position)
    merged_df['Projection'] = merged_df['Projection_x'].fillna(merged_df['points'])  # Vegas -> FFA fallback
    merged_df['Projection'] = merged_df['Projection'].fillna(merged_df['Projection_y']) 

    return merged_df

def print_missing_projections(DK_salaries, merged_df):
    print(f"Original DK rows: {len(DK_salaries)}")
    print(f"Merged rows: {len(merged_df)}")
    print(f"Missing projections: {merged_df['Projection'].isna().sum()}")

    # Show all players from DK who don't have Vegas projections
    missing_projections = merged_df[merged_df['Projection'].isna()]

    print("Players missing projections:")
    print(missing_projections[['Name_Clean', 'Position', 'Salary']].to_string(index=False))

def add_value_calculations(merged_df):

    # Add value calculations to the merged dataframe
    merged_df['Points_Per_Dollar'] = merged_df['Projection'] / merged_df['Salary'] * 1000  # Points per $1000

    # Add value rank within each position
    merged_df['Value_Rank'] = merged_df.groupby('Position')['Points_Per_Dollar'].rank(ascending=False)

    # Show best values overall
    best_values = merged_df[merged_df['Projection'].notna()].sort_values('Points_Per_Dollar', ascending=False)

    print("Best values (Points per $1000):")
    print(best_values[['Name_Clean', 'Position', 'Salary', 'Projection', 'Points_Per_Dollar']].head(10).to_string(index=False))
    
    # save best values to a csv file with all players
    best_values.to_csv("best_values.csv", index=False)

    # Show best values by position
    print("\nBest values by position:")
    for pos in ['QB', 'RB', 'WR', 'TE', 'DST']:
        pos_values = best_values[best_values['Position'] == pos].head(10)
        if not pos_values.empty:
            print(f"\n{pos}:")
            print(pos_values[['Name_Clean', 'Salary', 'Projection', 'Points_Per_Dollar']].to_string(index=False))
            

    merged_df.to_csv(f"{DATA_DIR}/merged_df_2026-10-18.csv", index=False)

    return merged_df

# Load Data from csv samples 
DK_salaries, Vegas_projection, FFA_projections = get_weekly_salaries()
DK_salaries, Vegas_projection, FFA_projections = clean_weekly_data(DK_salaries, Vegas_projection, FFA_projections, Print=False)
dst_projections = get_dst_projections(Print=False)
merged_df = merge_weekly_data(DK_salaries, Vegas_projection, FFA_projections, dst_projections, Print=True)
merged_df = add_value_calculations(merged_df)

# ## Brute force algorithm to find best lineups
 
# Lineup constraints
# 1. Total salary for Draftkings must be under 50,000 and Fanduel max is 60,000
# 2. Lineup must consis of 1QB 2RB 3WR 1TE 1FLEX(RB | WR | TE), and a DST
# 
# Steps
# 1. Create player pools by position 
# 2. Alter data on players from a pandas dataframe to a numpy array (avoids looping calculations by using arrays)  
# 3. Generate all possible combinations of pair of RBs and trio of WRs
# 4. Build a grid of all combinations per position, and then a true flase boolean flag that covers the flex position per that positional combination. So a 2d grid for each position eg (1176x125), with combinations and true flase for each player idx. 


#Draftkings salary
max_salary = 50000

# If we want to see a lot of print statements
VERBOSE = False

def build_player_pools(merged_df, filter_top_players = False, n=20, filter_by_ppd = False):
    # Filter out players without projections and sort by value
    valid_players = merged_df[merged_df['Projection'].notna()].copy()
    
    qbs = valid_players[valid_players['Position'] == 'QB']
    rbs = valid_players[valid_players['Position'] == 'RB']
    wrs = valid_players[valid_players['Position'] == 'WR']
    tes = valid_players[valid_players['Position'] == 'TE']
    dsts = valid_players[valid_players['Position'] == 'DST']
    
    #qbs = qbs[(qbs["Favored_team"] == True)]
    #rbs = rbs[rbs["Salary"] > "5000"]
    #tes = tes[tes["Salary"] < "5000"]
    #dsts = dsts[(dsts["Favored_Team"] == True) & (dsts["Home"] == True)
    
    if filter_by_ppd:
        ppd_filter = valid_players["Points_Per_Dollar"] >= 1.5

        qbs, rbs, wrs, tes, dsts = (
            valid_players[
                (valid_players["Position"] == pos) & ppd_filter
            ]
            for pos in ("QB", "RB", "WR", "TE", "DST")
        )


    if filter_top_players:
        qbs = pd.concat([qbs, valid_players[valid_players['Position'] == 'QB'].nlargest(n, 'Points_Per_Dollar')]).drop_duplicates(subset='Name_Clean')
        rbs = pd.concat([rbs, valid_players[valid_players['Position'] == 'RB'].nlargest(n, 'Points_Per_Dollar')]).drop_duplicates(subset='Name_Clean')
        wrs = pd.concat([wrs, valid_players[valid_players['Position'] == 'WR'].nlargest(n, 'Points_Per_Dollar')]).drop_duplicates(subset='Name_Clean')
        tes = pd.concat([tes, valid_players[valid_players['Position'] == 'TE'].nlargest(n, 'Points_Per_Dollar')]).drop_duplicates(subset='Name_Clean')
        dsts = pd.concat([dsts, valid_players[valid_players['Position'] == 'DST'].nlargest(n, 'Points_Per_Dollar')]).drop_duplicates(subset='Name_Clean')

    # Just for fun
    total_combos = (len(qbs) * math.comb(len(rbs), 2) *
                math.comb(len(wrs), 3) * len(tes) * len(dsts) *
                (len(rbs) - 2 + len(wrs) - 3 + len(tes)))  # FLEX options


    print(f"Total possible lineups with expanded pools: {total_combos}")

    return qbs, rbs, wrs, tes, dsts

qbs, rbs, wrs, tes, dsts = build_player_pools(merged_df, filter_by_ppd=True)  # Assuming merged_df is defined earlier

# Convert a single column to a 1D NumPy array
# Repeat for each salary, projection, and name column in the DataFrame
def arrs(df):
    return (
        df["Salary"].to_numpy(np.int32),
        df["Projection"].to_numpy(np.float32),
        df["Name_Clean"].to_numpy(object),
    )

# Pools as arrays
qb_sal, qb_pts, qb_names   = arrs(qbs)
rb_sal, rb_pts, rb_names   = arrs(rbs)
wr_sal, wr_pts, wr_names   = arrs(wrs)
te_sal, te_pts, te_names   = arrs(tes)
dst_sal, dst_pts, dst_names= arrs(dsts)


# Number of players per position
n_qb, n_rb, n_wr, n_te, n_dst = len(qb_sal), len(rb_sal), len(wr_sal), len(te_sal), len(dst_sal)

print("VERBOSE =", VERBOSE)  # Debug check

if VERBOSE:
    from pprint import pprint

    print(qb_sal.shape)
    print(rb_sal.shape)
    print(wr_sal.shape)
    print(te_sal.shape)
    print(dst_sal.shape)
    print(qb_pts.shape)
    print(rb_pts.shape)
    print(wr_pts.shape)
    print(te_pts.shape)
    print(dst_pts.shape)
    print(qb_names.shape)
    print(rb_names.shape)
    print(wr_names.shape)
    print(te_names.shape)
    print(dst_names.shape)

    def show_pool(tag, sal, pts, names, k=5):
        print(f"[{tag}] n={len(sal)} | salary dtype={sal.dtype}, range=({sal.min()}-{sal.max()}) "
        f"| pts dtype={pts.dtype}, range=({pts.min():.2f}-{pts.max():.2f})")
        print("    sample names:", end=" "); pprint(list(names[:k]))

    print("Pool sizes (QB, RB, WR, TE, DST):", (n_qb, n_rb, n_wr, n_te, n_dst))
    show_pool("QB",  qb_sal, qb_pts, qb_names)
    show_pool("RB",  rb_sal, rb_pts, rb_names)
    show_pool("WR",  wr_sal, wr_pts, wr_names)
    show_pool("TE",  te_sal, te_pts, te_names)
    show_pool("DST", dst_sal, dst_pts, dst_names)

    base_total = n_qb * (n_rb*(n_rb-1)//2) * (n_wr*(n_wr-1)*(n_wr-2)//6) * n_te * n_dst
    print(f"Estimated base combos (Q × C(RB,2) × C(WR,3) × TE × DST): {base_total:,}")
# ...existing code...

# Precompute RB pairs and WR trios
# Because we need to select 2 RBs and 3 WRs, we can precompute all combinations
# and their combined salaries and points to speed up lineup generation
rb_pairs = np.array(list(combinations(np.arange(n_rb, dtype=np.int16), 2)), dtype=np.int16)  # (Crb,2)
wr_trios = np.array(list(combinations(np.arange(n_wr, dtype=np.int16), 3)), dtype=np.int16) # (Cwr,3)

Crb, Cwr = len(rb_pairs), len(wr_trios)

rb_pair_sal = rb_sal[rb_pairs].sum(axis=1).astype(np.int32)
rb_pair_pts = rb_pts[rb_pairs].sum(axis=1).astype(np.float32)

wr_trio_sal = wr_sal[wr_trios].sum(axis=1).astype(np.int32)
wr_trio_pts = wr_pts[wr_trios].sum(axis=1).astype(np.float32)

if VERBOSE:
    print(f"RB pairs: {len(rb_pairs):,}, WR trios: {len(wr_trios):,}")
    print(rb_pairs.shape)
    print("First 3 RB pairs (idx):", rb_pairs[:3].tolist())
    print("First 2 WR trios (idx):", wr_trios[:2].tolist())
    print("First 3 RB pair names:", [(rb_names[i], rb_names[j]) for i,j in rb_pairs[:3]])
    print("First 2 WR trio names:", [(wr_names[i], wr_names[j], wr_names[k]) for i,j,k in wr_trios[:2]])
 


# Build FLEX pool (RB + WR + TE) 
# Adding flex pools, so the lineup creating loop will consider them while it creates the base lineups, instead of after
# Build FLEX pool (RB + WR + TE) and track their indices and type flags
flex_salary = np.concatenate([rb_sal, wr_sal, te_sal]).astype(np.int32)
flex_points = np.concatenate([rb_pts, wr_pts, te_pts]).astype(np.float32)
flex_names  = np.concatenate([rb_names, wr_names, te_names])

# number of FLEX candidates
n_flex = len(flex_salary)

# Is the flex position an RB, WR, or TE?
# Start with np.zeros, set False for all and change the first n_rb to True for flex_is_rb, the next n_wr to True for flex_is_wr, and the remaining n_te to True for flex_is_te
flex_is_rb = np.zeros(n_flex, dtype=bool); flex_is_rb[:n_rb] = True
flex_is_wr = np.zeros(n_flex, dtype=bool); flex_is_wr[n_rb:n_rb+n_wr] = True
flex_is_te = np.zeros(n_flex, dtype=bool); flex_is_te[n_rb+n_wr:] = True

# We do this beacuse we need to know which player in the FLEX pool corresponds to which RB/WR/TE index 
# Fill th idx arrays with -1 
flex_rb_idx = np.full(n_flex, -1, dtype=np.int16); flex_rb_idx[:n_rb] = np.arange(n_rb, dtype=np.int16)
flex_wr_idx = np.full(n_flex, -1, dtype=np.int16); flex_wr_idx[n_rb:n_rb+n_wr] = np.arange(n_wr, dtype=np.int16)
flex_te_idx = np.full(n_flex, -1, dtype=np.int16); flex_te_idx[n_rb+n_wr:] = np.arange(n_te, dtype=np.int16)

if VERBOSE:
    print(flex_salary.shape)
    print(flex_points.shape)
    print(flex_names.shape)
    
    print("flex_is_rb:", flex_is_rb)
    print("flex_is_wr:", flex_is_wr)
    print("flex_is_te:", flex_is_te)
    
    
    print("flex_rb_idx:", flex_rb_idx)  # [ 0  1  2  3  4  5  6  7  8  9 -1 -1 -1 -1 -1 -1 -1 -1 -1 -1 -1 -1 -1 -1 -1]    
    print("flex_wr_idx:", flex_wr_idx)  # [-1 -1 -1 -1 -1 -1 -1 -1 -1 -1  0  1  2  3  4  5  6  7  8  9 -1 -1 -1 -1 -1]
    print("flex_te_idx:", flex_te_idx)  # [-1 -1 -1 -1 -1 -1 -1 -1 -1 -1 -1 -1 -1 -1 -1 -1 -1 -1 -1 -1  0  1  2  3  4]
    
    # Example: we already chose RB indices (0,1). Which FLEX slots are safe for RB duplication?
    chosen_rb_pair = np.array([0, 1], dtype=np.int16)
    is_duplicate_rb = np.isin(flex_rb_idx, chosen_rb_pair)  # True where FLEX is RB0 or RB1
    print("dup RB flags:", is_duplicate_rb)  # [ True  True False False False False]
    

# Precompute FLEX overlap masks versus RB-pairs / WR-trios / TE
# Shapes: (Crb, n_flex), (Cwr, n_flex), (n_te, n_flex)
# rb_flex_ok equals True where FLEX can be that position without duplication of already chosen RBs/WRs/TE
# This works by broadcasting the flex_idx arrays against the rb_pairs and wr_trios
#[None, :] adds a new axis for broadcasting against the FLEX pool

# [None, :] adds a dimension at the beginning, making a row. EG (89,) -> (1, 89)
# [:, None] adds a dimension at the end, making a column. EG (89,) -> (89, 1)

# OR and Boolean statement refresher: If one statement is true out of the options presented, then it will return a true. If all are flase, then it returns false. Fries or chips. If a baking list says coconut oil or olive oil, you can use either and be ok. If it says and, then u have to use both.
# Applied here, we are saying the RB flex is ok, if the position of the flex is not an rb, or not one of the RBs picked.
# THen we check the flex vs the other WR and TE positions.

# (~flex_is_rb) [[False False False False False False False False False False False False False False False False False False False False False False  True..... ]]
# This first or statement allows flex spots allow = true for all non RBs

#---------------------------------------------------
# MATRIX BROADCASTING EXPLANATION
# When performing an OR (|) between arrays of different shapes,
# NumPy broadcasts the smaller array, here (1, 89), to match
# the larger array (231, 89).
#
# The True/False values in each column are repeated down all
# 231 rows, like dragging a formula down in Excel.
#
# Now both arrays have a shape of (231, 89). NumPy compares
# corresponding cells using OR and returns a new Boolean
# matrix with shape (231, 89).
#---------------------------------------------------


rb_flex_ok = (~flex_is_rb)[None, :] | (
    
    # The second statement creates the 231,89 matrix 
    # It has an and statement, where both must be true 
    # flex_rb_idx[None,:] (1,89) [[0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,-1....]] must not equal rb_pairs (231,2) [[0, 1], [0, 2], [0, 3]...[20,21]] which is rb_pairs[:,None,0] means the first element, idx 0, of each pair creating a (231,1) matrix, 
    # which turns into (231,89) after broadcasting against flex_rb_idx[None, :]
    (flex_rb_idx[None, :] != rb_pairs[:, None, 0]) & # creates 
    (flex_rb_idx[None, :] != rb_pairs[:, None, 1])
)

wr_flex_ok = (~flex_is_wr)[None, :] | (
    (flex_wr_idx[None, :] != wr_trios[:, None, 0]) &
    (flex_wr_idx[None, :] != wr_trios[:, None, 1]) &
    (flex_wr_idx[None, :] != wr_trios[:, None, 2])
)

te_flex_ok = (~flex_is_te)[None, :] | (
    (flex_te_idx[None, :] != np.arange(n_te, dtype=np.int16)[:, None])
)

# The shape shows how many RB pairs, WR trios, and TEs we have versus the FLEX pool size
# A flex pool size eg 25 due to 10 RBs + 10 WRs + 5 TEs
if VERBOSE:
    print("RB-FLEX overlap mask shape:", rb_flex_ok.shape)
    print("WR-FLEX overlap mask shape:", wr_flex_ok.shape)
    print("TE-FLEX overlap mask shape:", te_flex_ok.shape)
    print(rb_flex_ok)
    print(~flex_is_rb[None,:])


# %%
import math
import numpy as np

min_lineup_salary = 45_000
max_lineup_salary = 50_000

dims = (n_qb, Crb, Cwr, n_te, n_dst)
total = math.prod(dims)

chunk_size = 20_000
top_k = 10_000  # Underscores separate digits; this is an integer.

min_flex_salary = flex_salary.min()
max_flex_salary = flex_salary.max()

# Store only the best complete lineups found so far.
keep_idx = np.empty(0, dtype=np.int64)
keep_iflex = np.empty(0, dtype=np.int32)
keep_points = np.empty(0, dtype=np.float32)
keep_salary = np.empty(0, dtype=np.int32)

for start in range(0, 1_000_000, chunk_size):
    end = min(start + chunk_size, total)
    flat_idx = np.arange(start, end, dtype=np.int64)

    # 1. Convert each flat index into its position-combination indexes.
    iq, irp, iwt, ite, idst = np.unravel_index(flat_idx, dims)

    # 2. Calculate base lineup salary and projection.
    base_salary = (
        qb_sal[iq]
        + rb_pair_sal[irp]
        + wr_trio_sal[iwt]
        + te_sal[ite]
        + dst_sal[idst]
    )

    base_points = (
        qb_pts[iq]
        + rb_pair_pts[irp]
        + wr_trio_pts[iwt]
        + te_pts[ite]
        + dst_pts[idst]
    )

    # 3. Discard base lineups that cannot possibly reach
    # the minimum salary or stay under the maximum salary.
    possible = (
        (base_salary + max_flex_salary >= min_lineup_salary)
        & (base_salary + min_flex_salary <= max_lineup_salary)
    )

    flat_idx = flat_idx[possible]
    iq, irp, iwt, ite, idst = (
        x[possible] for x in (iq, irp, iwt, ite, idst)
    )
    base_salary = base_salary[possible]
    base_points = base_points[possible]

    if flat_idx.size == 0:
        continue

    # 4. Check which FLEX players can join each base lineup.
    allowed = (
        rb_flex_ok[irp]
        & wr_flex_ok[iwt]
        & te_flex_ok[ite]
    )

    # Keep one representation of each group of players:
    # the FLEX player must have the highest index at their position.
    allowed &= (
        ~flex_is_rb[None, :]
        | (flex_rb_idx[None, :] > rb_pairs[irp, 1][:, None])
    )

    allowed &= (
        ~flex_is_wr[None, :]
        | (flex_wr_idx[None, :] > wr_trios[iwt, 2][:, None])
    )

    allowed &= (
        ~flex_is_te[None, :]
        | (flex_te_idx[None, :] > ite[:, None])
    )

    # 5. Enforce BOTH salary limits for each complete lineup.
    allowed &= (
        (base_salary + flex_salary.min()[:, None]
        if False else True)
    )
    
    # 6. Enforce the remaining salary constraints for each FLEX player.
    allowed &= (
    (flex_salary[None, :] >=
        (min_lineup_salary - base_salary)[:, None])
    & (flex_salary[None, :] <=
        (max_lineup_salary - base_salary)[:, None])
    )

    # 6. Get the row (base lineup) and column (FLEX player)
    # for every valid combination.
    rows, cols = np.where(allowed)

    if rows.size:
        pts = base_points[rows] + flex_points[cols]
        sal = base_salary[rows] + flex_salary[cols]
        idx = flat_idx[rows]

        # 7. Add this batch's candidates to the global top K.
        keep_idx = np.concatenate((keep_idx, idx))
        keep_iflex = np.concatenate((keep_iflex, cols.astype(np.int32)))
        keep_points = np.concatenate((keep_points, pts))
        keep_salary = np.concatenate((keep_salary, sal))

        # Discard everything except the best top K scores.
        if keep_points.size > top_k:
            best = np.argpartition(keep_points, -top_k)[-top_k:]

            keep_idx = keep_idx[best]
            keep_iflex = keep_iflex[best]
            keep_points = keep_points[best]
            keep_salary = keep_salary[best]

    if start % (chunk_size * 100) == 0:
        print(
            f"Processed {end:,}/{total:,} base combinations; "
            f"top K retained: {len(keep_points):,}"
        )

print(f"Finished. Complete lineups retained: {len(keep_points):,}")
    

# # View the lineups
# Convert the saved base indexes back into position indexes
sel_iq, sel_irp, sel_iwt, sel_ite, sel_idst = np.unravel_index(
    keep_idx, dims
)

# Decode the RB pairs and WR trios
rb_idx = rb_pairs[sel_irp]
wr_idx = wr_trios[sel_iwt]

# Build a readable DataFrame
top_lineups = pd.DataFrame({
    "Points": keep_points,
    "Salary": keep_salary,
    "Remaining": max_lineup_salary - keep_salary,
    "QB": qb_names[sel_iq],
    "RB1": rb_names[rb_idx[:, 0]],
    "RB2": rb_names[rb_idx[:, 1]],
    "WR1": wr_names[wr_idx[:, 0]],
    "WR2": wr_names[wr_idx[:, 1]],
    "WR3": wr_names[wr_idx[:, 2]],
    "TE": te_names[sel_ite],
    "FLEX": flex_names[keep_iflex],
    "DST": dst_names[sel_idst],
})

# Sort from highest to lowest projection
top_lineups = top_lineups.sort_values(
    "Points", ascending=False
).reset_index(drop=True)

# Add a rank column to the DataFrame
top_lineups.insert(0, "Rank", np.arange(1, len(top_lineups) + 1))

# View the top 20
print(top_lineups.head(20))

top_lineups.to_csv(f"{DATA_DIR}/top_10k_lineups.csv", index=False)

n_lineups = 20
max_exposure = 0.50

# Maximum number of selected lineups any player can appear in
max_player_count = int(np.floor(n_lineups * max_exposure))

player_cols = [
    "QB", "RB1", "RB2", "WR1", "WR2",
    "WR3", "TE", "FLEX", "DST"
]

# Start with the highest-projected lineups
candidates = top_lineups.sort_values("Points", ascending=False)

selected = []
exposure = {}

for idx, lineup in candidates.iterrows():
    players = lineup[player_cols].tolist()

    # Skip this lineup if any player has reached the exposure cap
    if any(exposure.get(player, 0) >= max_player_count
        for player in players):
        continue

    # Accept the lineup and update exposure counts
    selected.append(idx)

    for player in players:
        exposure[player] = exposure.get(player, 0) + 1

    if len(selected) == n_lineups:
        break

# Final selected lineups
final_lineups = top_lineups.loc[selected].copy().reset_index(drop=True)
final_lineups["Rank"] = np.arange(1, len(final_lineups) + 1)

final_lineups.to_csv(f"{DATA_DIR}/top_lineups.csv", index=False)

print(f"Selected {len(final_lineups)} lineups")
print(final_lineups)

player_exposure = (
    final_lineups[player_cols]
    .melt(value_name="Player")["Player"]
    .value_counts()
    .rename("Lineups")
    .to_frame()
)

player_exposure["Exposure"] = (
    player_exposure["Lineups"] / len(final_lineups)
)

print(player_exposure.sort_values("Exposure", ascending=False))


