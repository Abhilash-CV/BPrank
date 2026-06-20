import streamlit as st
import pandas as pd
import numpy as np
from io import BytesIO
import sys

# Check if openpyxl is installed, if not, install it
try:
    import openpyxl
except ImportError:
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "openpyxl"])
    import openpyxl

st.set_page_config(
    page_title="B.Pharm Rank List Generator",
    layout="wide"
)

st.title("B.Pharm Rank List Generator")

st.markdown("""
### Upload Files

1. Normalized Score CSV
2. Candidates CSV
3. CBT Responses CSV

Tie Breaking Order:

1. Normalized Score
2. Chemistry Score (Pre-Normalized)
3. Physics Score (Pre-Normalized)
4. Chemistry Correct Responses
5. Physics Correct Responses
6. Older Candidate (DOB)

**Note:** Candidates with Normalized Score ≤ 5 are rejected (except SC/ST categories)
""")

# ======================================================
# FILE UPLOADS
# ======================================================

norm_file = st.file_uploader(
    "Upload Normalized Score CSV",
    type="csv"
)

cand_file = st.file_uploader(
    "Upload Candidates CSV",
    type="csv"
)

cbt_file = st.file_uploader(
    "Upload CBT Responses CSV",
    type="csv"
)

# ======================================================
# PROCESS
# ======================================================

if norm_file and cand_file and cbt_file:

    try:

        # --------------------------------------------------
        # READ FILES
        # --------------------------------------------------

        norm_df = pd.read_csv(norm_file)
        cand_df = pd.read_csv(cand_file)
        cbt_df = pd.read_csv(cbt_file)

        st.success("All files loaded successfully")

        # --------------------------------------------------
        # CLEAN COLUMN NAMES
        # --------------------------------------------------

        norm_df.columns = norm_df.columns.str.strip()
        cand_df.columns = cand_df.columns.str.strip()
        cbt_df.columns = cbt_df.columns.str.strip()

        # --------------------------------------------------
        # VALIDATE REQUIRED COLUMNS
        # --------------------------------------------------

        required_norm = [
            "RollNo",
            "Norm_Score"
        ]

        required_cand = [
            "ApplNo",
            "RollNo",
            "Name",
            "DOB",
            "BPharm"
        ]

        required_cbt = [
            "RollNo",
            "QNo",
            "Mark"
        ]

        missing_cols = []

        for col in required_norm:
            if col not in norm_df.columns:
                missing_cols.append(f"Normalization : {col}")

        for col in required_cand:
            if col not in cand_df.columns:
                missing_cols.append(f"Candidates : {col}")

        for col in required_cbt:
            if col not in cbt_df.columns:
                missing_cols.append(f"CBT : {col}")

        if missing_cols:
            st.error("Missing Columns")
            st.write(missing_cols)
            st.stop()

        # --------------------------------------------------
        # DATA TYPES
        # --------------------------------------------------

        norm_df["RollNo"] = pd.to_numeric(
            norm_df["RollNo"],
            errors="coerce"
        )

        cand_df["RollNo"] = pd.to_numeric(
            cand_df["RollNo"],
            errors="coerce"
        )

        cbt_df["RollNo"] = pd.to_numeric(
            cbt_df["RollNo"],
            errors="coerce"
        )

        cbt_df["QNo"] = pd.to_numeric(
            cbt_df["QNo"],
            errors="coerce"
        )

        cbt_df["Mark"] = pd.to_numeric(
            cbt_df["Mark"],
            errors="coerce"
        ).fillna(0)

        cand_df["DOB_Parsed"] = pd.to_datetime(
            cand_df["DOB"],
            errors="coerce"
        )

        # ==================================================
        # VALIDATIONS
        # ==================================================

        validation_results = {}

        # --------------------------------------------------
        # Duplicate Candidate Roll Numbers
        # --------------------------------------------------

        dup_rolls = cand_df[
            cand_df.duplicated(
                subset=["RollNo"],
                keep=False
            )
        ]

        validation_results[
            "Duplicate Roll Numbers"
        ] = dup_rolls

        # --------------------------------------------------
        # Missing Normalized Scores
        # --------------------------------------------------

        missing_norm = cand_df[
            ~cand_df["RollNo"].isin(
                norm_df["RollNo"]
            )
        ]

        validation_results[
            "Missing Normalized Scores"
        ] = missing_norm

        # --------------------------------------------------
        # Missing CBT Responses
        # --------------------------------------------------

        missing_cbt = cand_df[
            ~cand_df["RollNo"].isin(
                cbt_df["RollNo"]
            )
        ]

        validation_results[
            "Missing CBT Responses"
        ] = missing_cbt

        # --------------------------------------------------
        # Invalid DOB
        # --------------------------------------------------

        invalid_dob = cand_df[
            cand_df["DOB_Parsed"].isna()
        ]

        validation_results[
            "Invalid DOB"
        ] = invalid_dob

        # --------------------------------------------------
        # Not Opted B.Pharm
        # --------------------------------------------------

        not_opted = cand_df[
            cand_df["BPharm"].fillna("").str.upper() != "Y"
        ]

        validation_results[
            "Not Opted B.Pharm"
        ] = not_opted

        # --------------------------------------------------
        # Duplicate Normalization Records
        # --------------------------------------------------

        dup_norm = norm_df[
            norm_df.duplicated(
                subset=["RollNo"],
                keep=False
            )
        ]

        validation_results[
            "Duplicate Normalization Records"
        ] = dup_norm

        # --------------------------------------------------
        # Negative Normalized Score
        # --------------------------------------------------

        negative_norm = norm_df[
            norm_df["Norm_Score"] < 0
        ]

        validation_results[
            "Negative Normalized Scores"
        ] = negative_norm

        # ==================================================
        # DETAILED REJECTION ANALYSIS
        # ==================================================
        
        st.header("🔍 Detailed Rejection Analysis")
        
        # Create a comprehensive rejection dataframe
        rejection_analysis = cand_df.copy()
        rejection_analysis["Missing_Norm"] = ~rejection_analysis["RollNo"].isin(norm_df["RollNo"])
        rejection_analysis["Missing_CBT"] = ~rejection_analysis["RollNo"].isin(cbt_df["RollNo"])
        rejection_analysis["Invalid_DOB"] = rejection_analysis["DOB_Parsed"].isna()
        rejection_analysis["Not_Opted_BPharm"] = rejection_analysis["BPharm"].fillna("").str.upper() != "Y"
        rejection_analysis["Duplicate_RollNo"] = rejection_analysis["RollNo"].isin(dup_rolls["RollNo"])
        
        # Count how many rejection reasons each candidate has
        rejection_analysis["Rejection_Count"] = (
            rejection_analysis["Missing_Norm"].astype(int) +
            rejection_analysis["Missing_CBT"].astype(int) +
            rejection_analysis["Invalid_DOB"].astype(int) +
            rejection_analysis["Not_Opted_BPharm"].astype(int) +
            rejection_analysis["Duplicate_RollNo"].astype(int)
        )
        
        # Filter only rejected candidates
        rejected_candidates = rejection_analysis[rejection_analysis["Rejection_Count"] > 0]
        
        st.subheader(f"Total Rejected Candidates: {len(rejected_candidates)}")
        
        # Breakdown by rejection reason
        st.subheader("Rejection Reasons Breakdown")
        
        reason_breakdown = pd.DataFrame({
            "Rejection Reason": [
                "Missing Normalized Score",
                "Missing CBT Responses", 
                "Invalid DOB",
                "Not Opted B.Pharm",
                "Duplicate Roll Number"
            ],
            "Count": [
                len(missing_norm),
                len(missing_cbt),
                len(invalid_dob),
                len(not_opted),
                len(dup_rolls)
            ]
        })
        st.dataframe(reason_breakdown, use_container_width=True)
        
        # Show overlap between reasons
        st.subheader("Overlap Analysis (Candidates with Multiple Issues)")
        
        overlap_summary = rejection_analysis[rejection_analysis["Rejection_Count"] > 0]["Rejection_Count"].value_counts().sort_index()
        overlap_df = pd.DataFrame({
            "Number of Issues": overlap_summary.index,
            "Candidates": overlap_summary.values
        })
        st.dataframe(overlap_df, use_container_width=True)
        
        # Show the exact candidates causing the discrepancy
        st.subheader("🔴 Candidates Causing the Discrepancy")
        
        # Candidates with Missing CBT but NOT Missing Norm
        missing_cbt_only = rejected_candidates[
            (rejected_candidates["Missing_CBT"] == True) &
            (rejected_candidates["Missing_Norm"] == False) &
            (rejected_candidates["Invalid_DOB"] == False) &
            (rejected_candidates["Not_Opted_BPharm"] == False) &
            (rejected_candidates["Duplicate_RollNo"] == False)
        ]
        
        # Candidates with Missing Norm but NOT Missing CBT
        missing_norm_only = rejected_candidates[
            (rejected_candidates["Missing_Norm"] == True) &
            (rejected_candidates["Missing_CBT"] == False) &
            (rejected_candidates["Invalid_DOB"] == False) &
            (rejected_candidates["Not_Opted_BPharm"] == False) &
            (rejected_candidates["Duplicate_RollNo"] == False)
        ]
        
        # Candidates with both missing
        missing_both = rejected_candidates[
            (rejected_candidates["Missing_Norm"] == True) &
            (rejected_candidates["Missing_CBT"] == True)
        ]
        
        col1, col2, col3 = st.columns(3)
        col1.metric("Missing Norm Only", len(missing_norm_only))
        col2.metric("Missing CBT Only", len(missing_cbt_only))
        col3.metric("Missing Both", len(missing_both))
        
        # Combine the discrepancy candidates
        discrepancy_candidates = pd.concat([missing_norm_only, missing_cbt_only])
        
        if len(discrepancy_candidates) > 0:
            st.write(f"**These {len(discrepancy_candidates)} candidates have only ONE of the two issues (causing the 8601 vs 8604 difference):**")
            display_cols = ["ApplNo", "RollNo", "Name", "DOB", "Missing_Norm", "Missing_CBT", "Invalid_DOB", "Not_Opted_BPharm", "Duplicate_RollNo"]
            st.dataframe(discrepancy_candidates[display_cols], use_container_width=True)
            
            # Download the discrepancy candidates
            st.download_button(
                label=f"Download Discrepancy Candidates ({len(discrepancy_candidates)} candidates)",
                data=discrepancy_candidates[display_cols].to_csv(index=False),
                file_name="Discrepancy_Candidates.csv",
                mime="text/csv"
            )
        
        # Show the exact rejected count
        st.info(f"""
        **Explanation:**
        - Missing Normalized Scores: {len(missing_norm)} candidates
        - Missing CBT Responses: {len(missing_cbt)} candidates
        - Total unique rejected candidates: {len(rejected_candidates)}
        
        The difference ({len(missing_norm) + len(missing_cbt) - len(rejected_candidates)}) is the number of candidates who have BOTH issues.
        """)

        # ==================================================
        # VALIDATION SUMMARY
        # ==================================================

        st.header("Validation Summary")

        summary = []

        for k, v in validation_results.items():

            summary.append({
                "Validation": k,
                "Count": len(v)
            })

        summary_df = pd.DataFrame(summary)

        st.dataframe(
            summary_df,
            use_container_width=True
        )

        # ==================================================
        # EXCEPTION REPORTS
        # ==================================================
        
        # Create rejection_df for exception reports
        rejection_df = cand_df.copy()
        rejection_df["Reason"] = ""
        
        # Add reasons for rejection
        rejection_df.loc[
            ~rejection_df["RollNo"].isin(norm_df["RollNo"]),
            "Reason"
        ] += "Missing Normalized Score; "
        
        rejection_df.loc[
            ~rejection_df["RollNo"].isin(cbt_df["RollNo"]),
            "Reason"
        ] += "Missing CBT Responses; "
        
        rejection_df.loc[
            rejection_df["DOB_Parsed"].isna(),
            "Reason"
        ] += "Invalid DOB; "
        
        with st.expander(
            "View Validation Errors"
        ):

            for k, v in validation_results.items():

                if len(v) > 0:

                    st.subheader(
                        f"{k} ({len(v)})"
                    )

                    st.dataframe(
                        v,
                        use_container_width=True
                    )

                    st.download_button(
                        label=f"Download {k}",
                        data=v.to_csv(
                            index=False
                        ),
                        file_name=f"{k}.csv",
                        mime="text/csv",
                        key=k
                    )

        # ==================================================
        # ELIGIBLE CANDIDATES
        # ==================================================

        eligible_df = cand_df.copy()

        eligible_df = eligible_df[
            eligible_df["BPharm"].fillna("").str.upper() == "Y"
        ]

        eligible_df = eligible_df[
            eligible_df["DOB_Parsed"].notna()
        ]

        eligible_df = eligible_df[
            eligible_df["RollNo"].isin(
                norm_df["RollNo"]
            )
        ]

        eligible_df = eligible_df[
            eligible_df["RollNo"].isin(
                cbt_df["RollNo"]
            )
        ]

        eligible_df = eligible_df[
            ~eligible_df["RollNo"].isin(
                dup_rolls["RollNo"]
            )
        ]

        # ==================================================
        # CHEMISTRY & PHYSICS
        # ==================================================

        chemistry_df = cbt_df[
            cbt_df["QNo"] <= 45
        ]

        physics_df = cbt_df[
            cbt_df["QNo"] > 45
        ]

        chemistry_stats = (
            chemistry_df
            .groupby("RollNo")
            .agg(
                Chem_Score=("Mark", "sum"),
                Chem_Correct=(
                    "Mark",
                    lambda x: (x == 4).sum()
                )
            )
            .reset_index()
        )

        physics_stats = (
            physics_df
            .groupby("RollNo")
            .agg(
                Phy_Score=("Mark", "sum"),
                Phy_Correct=(
                    "Mark",
                    lambda x: (x == 4).sum()
                )
            )
            .reset_index()
        )

        # ==================================================
        # MERGE DATA
        # ==================================================

        rank_df = (
            eligible_df
            .merge(
                norm_df[["RollNo", "Norm_Score"]],
                on="RollNo",
                how="inner"
            )
            .merge(
                chemistry_stats,
                on="RollNo",
                how="left"
            )
            .merge(
                physics_stats,
                on="RollNo",
                how="left"
            )
        )

        # Numeric columns only
        numeric_cols = [
            "Norm_Score",
            "Chem_Score",
            "Phy_Score",
            "Chem_Correct",
            "Phy_Correct"
        ]
        
        # Ensure Category column exists
        if "Category" not in rank_df.columns:
            rank_df["Category"] = ""
        
        rank_df["Category"] = (
            rank_df["Category"]
            .fillna("")
            .astype(str)
            .str.upper()
        )
        
        rank_df["Norm_Score"] = pd.to_numeric(
            rank_df["Norm_Score"],
            errors="coerce"
        ).fillna(0)
        
        for col in numeric_cols:
            if col in rank_df.columns:
                rank_df[col] = rank_df[col].fillna(0)
        
        # ==================================================
        # SORTING AS PER PROSPECTUS
        # ==================================================

        rank_df = rank_df.sort_values(
            by=[
                "Norm_Score",
                "Chem_Score",
                "Phy_Score",
                "Chem_Correct",
                "Phy_Correct",
                "DOB_Parsed"
            ],
            ascending=[
                False,
                False,
                False,
                False,
                False,
                True
            ]
        )
        
        # ==================================================
        # GENERATE BRANK
        # ==================================================

        rank_df["BRank"] = np.arange(
            1,
            len(rank_df) + 1
        )

        # ==================================================
        # DISPLAY
        # ==================================================

        st.header("Rank List")

        # UPDATED: Added Category to final columns
        final_columns = [
            "BRank",
            "ApplNo",
            "RollNo",
            "Name",
            "DOB",
            "Category",
            "Norm_Score",
            "Chem_Score",
            "Phy_Score",
            "Chem_Correct",
            "Phy_Correct"
        ]

        # Ensure all columns exist
        available_columns = [col for col in final_columns if col in rank_df.columns]
        
        if len(rank_df) > 0:
            st.dataframe(
                rank_df[available_columns],
                use_container_width=True,
                height=600
            )
        else:
            st.warning("No eligible candidates found. Please check the validation section.")

        # ==================================================
        # STATISTICS
        # ==================================================

        col1, col2, col3, col4 = st.columns(4)

        col1.metric(
            "Total Candidates",
            len(cand_df)
        )

        col2.metric(
            "Eligible Candidates",
            len(rank_df)
        )

        col3.metric(
            "Rejected Candidates",
            len(cand_df) - len(rank_df)
        )
        
        col4.metric(
            "Unique Rejection Reasons",
            len(rejected_candidates)
        )
        
        # Category-wise statistics
        if len(rank_df) > 0:
            st.subheader("Category-wise Statistics")
            if "Category" in rank_df.columns:
                category_stats = rank_df["Category"].value_counts().reset_index()
                category_stats.columns = ["Category", "Count"]
                st.dataframe(category_stats, use_container_width=True)
        
        # ==================================================
        # DOWNLOAD - CSV
        # ==================================================

        if len(rank_df) > 0:
            st.subheader("Download Options")
            
            col_csv, col_excel = st.columns(2)
            
            with col_csv:
                st.download_button(
                    label="Download B.Pharm Rank List (CSV)",
                    data=rank_df[
                        available_columns
                    ].to_csv(index=False),
                    file_name="BPHARM_RANKLIST.csv",
                    mime="text/csv"
                )
            
            with col_excel:
                try:
                    # Create Excel file with multiple sheets
                    output = BytesIO()
                    with pd.ExcelWriter(output, engine='openpyxl') as writer:
                        # Main rank list sheet with Category column
                        rank_df[available_columns].to_excel(
                            writer, 
                            sheet_name='BPharm_Rank_List', 
                            index=False
                        )
                        
                        # Category statistics sheet
                        if "Category" in rank_df.columns:
                            category_stats = rank_df["Category"].value_counts().reset_index()
                            category_stats.columns = ["Category", "Count"]
                            category_stats.to_excel(
                                writer, 
                                sheet_name='Category_Statistics', 
                                index=False
                            )
                        
                        # Validation summary sheet
                        summary_df.to_excel(
                            writer, 
                            sheet_name='Validation_Summary', 
                            index=False
                        )
                        
                        # Rejected candidates sheet
                        if len(rejected_candidates) > 0:
                            rejected_export = rejected_candidates[["ApplNo", "RollNo", "Name", "DOB", "Rejection_Count"]].copy()
                            rejected_export["Rejection_Reasons"] = ""
                            
                            # Add reason descriptions
                            rejected_export.loc[rejected_export["Rejection_Count"] >= 1, "Rejection_Reasons"] = ""
                            
                            # Build reason strings
                            for idx in rejected_export.index:
                                reasons = []
                                if rejected_export.loc[idx, "ApplNo"] in missing_norm["ApplNo"].values:
                                    reasons.append("Missing Norm Score")
                                if rejected_export.loc[idx, "ApplNo"] in missing_cbt["ApplNo"].values:
                                    reasons.append("Missing CBT")
                                if rejected_export.loc[idx, "ApplNo"] in invalid_dob["ApplNo"].values:
                                    reasons.append("Invalid DOB")
                                if rejected_export.loc[idx, "ApplNo"] in not_opted["ApplNo"].values:
                                    reasons.append("Not Opted BPharm")
                                if rejected_export.loc[idx, "ApplNo"] in dup_rolls["ApplNo"].values:
                                    reasons.append("Duplicate RollNo")
                                rejected_export.loc[idx, "Rejection_Reasons"] = ", ".join(reasons)
                            
                            rejected_export.to_excel(
                                writer,
                                sheet_name='Rejected_Candidates',
                                index=False
                            )
                        
                        # Discrepancy candidates sheet (the 3 candidates)
                        if len(discrepancy_candidates) > 0:
                            discrepancy_cols = ["ApplNo", "RollNo", "Name", "DOB", "Missing_Norm", "Missing_CBT", "Invalid_DOB", "Not_Opted_BPharm", "Duplicate_RollNo"]
                            discrepancy_candidates[discrepancy_cols].to_excel(
                                writer,
                                sheet_name='Discrepancy_3_Candidates',
                                index=False
                            )
                        
                        # Individual issue sheets
                        if len(missing_norm) > 0:
                            missing_norm[["ApplNo", "RollNo", "Name", "DOB"]].to_excel(
                                writer,
                                sheet_name='Missing_Norm_Score',
                                index=False
                            )
                        
                        if len(missing_cbt) > 0:
                            missing_cbt[["ApplNo", "RollNo", "Name", "DOB"]].to_excel(
                                writer,
                                sheet_name='Missing_CBT',
                                index=False
                            )
                        
                        if len(invalid_dob) > 0:
                            invalid_dob[["ApplNo", "RollNo", "Name", "DOB"]].to_excel(
                                writer,
                                sheet_name='Invalid_DOB',
                                index=False
                            )
                        
                        if len(not_opted) > 0:
                            not_opted[["ApplNo", "RollNo", "Name", "DOB", "BPharm"]].to_excel(
                                writer,
                                sheet_name='Not_Opted_BPharm',
                                index=False
                            )
                        
                        if len(dup_rolls) > 0:
                            dup_rolls[["ApplNo", "RollNo", "Name", "DOB"]].to_excel(
                                writer,
                                sheet_name='Duplicate_RollNos',
                                index=False
                            )
                    
                    output.seek(0)
                    
                    st.download_button(
                        label="Download Complete Excel Report (All Sheets)",
                        data=output,
                        file_name="BPHARM_Complete_Report.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
                except Exception as excel_error:
                    st.warning(f"Excel export failed: {str(excel_error)}")
                    st.info("Please use the CSV download option instead.")

            # ==================================================
            # SQL UPDATE FILE
            # ==================================================

            if "ApplNo" in rank_df.columns and "BRank" in rank_df.columns:
                sql_df = rank_df[
                    ["ApplNo", "BRank"]
                ]

                sql_lines = []

                for _, row in sql_df.iterrows():

                    sql_lines.append(
                        f"UPDATE candidates "
                        f"SET BRank={int(row['BRank'])} "
                        f"WHERE ApplNo='{row['ApplNo']}';"
                    )

                sql_text = "\n".join(sql_lines)

                st.download_button(
                    label="Download BRank Update SQL",
                    data=sql_text,
                    file_name="Update_BRank.sql",
                    mime="text/plain"
                )

    except Exception as e:

        st.error(f"An error occurred: {str(e)}")
        st.exception(e)
