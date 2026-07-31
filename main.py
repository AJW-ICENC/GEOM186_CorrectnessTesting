"""

Gaps and Overlaps Beta Testing: Automated Dual Testing Script

This Script assesses the Beta Infrastructure of the Gaps and Overlaps project against Live process
It does this by:
    comparing CWI registered records, attribution and geometry against the DMD and QGIS.
    Comparing Created overlap records, attribution and geometry

"""

# Author: Alex Wallage
# Version: 2
# Date: 15/10/2025

## Enhanced with AI



## --------Import packages----------

import os
import pyodbc
import pandas as pd
import geopandas as gpd
from datetime import datetime
from shapely import wkt
from shapely.geometry import MultiPolygon, GeometryCollection
import configparser


## ---------Utility Functions---------

# change geometry
def geometry_collection_to_multipolygon(geom):
    if isinstance(geom, GeometryCollection):
        # Extract only Polygon and MultiPolygon geometries
        polygons = [g for g in geom.geoms if g.geom_type in ['Polygon', 'MultiPolygon']]
        # Flatten MultiPolygons into individual Polygons
        flat_polygons = []
        for poly in polygons:
            if poly.geom_type == 'Polygon':
                flat_polygons.append(poly)
            elif poly.geom_type == 'MultiPolygon':
                flat_polygons.extend(poly.geoms)
        return MultiPolygon(flat_polygons) if flat_polygons else None
    return geom  # Return original if not a GeometryCollection


# -----------------Geodataframe Comparison Functions-----------------------

def compare_databases(df_DMD, gdf_GaO, gdf_qgis, timestamp, output_dir, output_dir_2):
    """
    Compare databases and generate detailed report of issues
    """

    print("\n" + "="*50)
    print("Beginning Comparison of Gaps and Overlaps Beta to DMD and QGIS project shapefiles")
    print("="*50 + "\n")

    

    # Initialise results dics and lists
    results = {}
    issues_report = []
    
    # Filter QGIS data to last 7 days
    if gdf_qgis is not None: 
        if not pd.api.types.is_datetime64_any_dtype(gdf_qgis["DATE_ADDED"]):
            gdf_qgis["DATE_ADDED"] = pd.to_datetime(gdf_qgis["DATE_ADDED"], errors="coerce")
        today = pd.Timestamp(datetime.now().date())
        seven_days_ago = today - pd.Timedelta(days=7)
        
        gdf_qgis["DATE_ADDED"] = gdf_qgis["DATE_ADDED"].ffill().bfill()
        
        gdf_qgis = gdf_qgis[
            (gdf_qgis["DATE_ADDED"].dt.date >= seven_days_ago.date()) &
            (gdf_qgis["DATE_ADDED"].dt.date <= today.date())
        ]
    
    if df_DMD is not None:
        # ============ DATA PREPARATION ============
        # Standardize ID columns for comparison
        df_DMD_prep = df_DMD.copy()
        df_DMD_prep = df_DMD_prep.rename(columns={"ID": "CellWorkItemID", "Name": "CellName"})
        df_DMD_prep["CellName"] = df_DMD_prep["CellName"].str[:8]
        
        gdf_GaO_prep = gdf_GaO.copy()
        
        if gdf_qgis is not None:
            gdf_qgis_prep = gdf_qgis.copy()
            if 'DMD_ID' in gdf_qgis_prep.columns:
                gdf_qgis_prep = gdf_qgis_prep.rename(columns={"DMD_ID": "CellWorkItemID"})
        
        # Record counts
        print(f"DMD CWIs registered this week: {len(df_DMD_prep)}")
        results["CWIs IN DMD"] = len(df_DMD_prep)
        
        #print(f"CWIs in QGIS registered this week: {len(gdf_qgis)}")
        #results["CWIs in QGIS"] = len(gdf_qgis)
        
        print(f"CWIs in beta registered this week: {len(gdf_GaO_prep)}")
        results["CWIs in Beta"] = len(gdf_GaO_prep)
        


        # ============ 1. CHECK FOR MISSING RECORDS ============
        print("\n=== Checking for missing records ===")
        
        dmd_ids = set(df_DMD_prep['CellWorkItemID'].values)
        gao_ids = set(gdf_GaO_prep['CellWorkItemID'].values)
        
        missing_in_gao = dmd_ids - gao_ids
        extra_in_gao = gao_ids - dmd_ids
        
        if missing_in_gao:
            print(f"WARNING: {len(missing_in_gao)} records missing in GaO")
            results['Missing_in_GaO_Count'] = len(missing_in_gao)
            for missing_id in missing_in_gao:
                missing_row = df_DMD_prep[df_DMD_prep['CellWorkItemID'] == missing_id].iloc[0]
                issues_report.append({
                    'Issue_Type': 'Missing in GaO',
                    'CellWorkItemID': missing_id,
                    'CellName': missing_row.get('CellName', 'N/A'),
                    'Expected_Scale': missing_row.get('Scale', 'N/A'),
                    'Expected_UsageBand': missing_row.get('UsageBand', 'N/A'),
                    'Expected_Edition': missing_row.get('Edition', 'N/A'),
                    'Actual_Value': 'MISSING',
                    'Details': 'Record exists in DMD but not in GaO'
                })
        
        if extra_in_gao:
            print(f"WARNING: {len(extra_in_gao)} extra records in GaO")
            results['Extra_in_GaO_Count'] = len(extra_in_gao)
            for extra_id in extra_in_gao:
                extra_row = gdf_GaO_prep[gdf_GaO_prep['CellWorkItemID'] == extra_id].iloc[0]
                issues_report.append({
                    'Issue_Type': 'Extra in GaO',
                    'CellWorkItemID': extra_id,
                    'CellName': extra_row.get('CellName', 'N/A'),
                    'Expected_Scale': 'N/A',
                    'Expected_UsageBand': 'N/A',
                    'Expected_Edition': 'N/A',
                    'Actual_Value': 'EXTRA RECORD',
                    'Details': 'Record exists in GaO but not in DMD'
                })
        
        # ============ 2. COMPARE ATTRIBUTION ============
        print("\n=== Checking attribution differences ===")
        
        # Drop geometry and internal columns from GaO for comparison
        gdf_GaO_comp = gdf_GaO_prep.drop(columns=["OverlapsCreated", "ValidationStatusID", "geometry"], errors='ignore')
        
        # Select comparison columns
        compare_cols = ['CellWorkItemID', 'CellName', 'Scale', 'UsageBand', 'ModificationID', 'Edition']
        df_DMD_comp = df_DMD_prep[compare_cols]
        gdf_GaO_comp = gdf_GaO_comp[compare_cols]
        
        # Sort by ID for alignment
        df_DMD_comp = df_DMD_comp.sort_values(by="CellWorkItemID").reset_index(drop=True)
        gdf_GaO_comp = gdf_GaO_comp.sort_values(by="CellWorkItemID").reset_index(drop=True)
        
        # Merge on CellWorkItemID to compare matching records
        merged = pd.merge(
            df_DMD_comp, 
            gdf_GaO_comp, 
            on='CellWorkItemID', 
            how='inner',
            suffixes=('_DMD', '_GaO')
        )
        
        # Compare each attribute column
        attr_columns = ['CellName', 'Scale', 'UsageBand', 'ModificationID', 'Edition']
        attr_issues_count = 0

        
        for col in attr_columns:
            dmd_col = f"{col}_DMD"
            gao_col = f"{col}_GaO"
            
            if dmd_col in merged.columns and gao_col in merged.columns:
                # Find mismatches
                mismatches = merged[merged[dmd_col] != merged[gao_col]]
                
                if len(mismatches) > 0:
                    attr_issues_count += len(mismatches)
                    print(f"  {col}: {len(mismatches)} mismatches found")
                    
                    for idx, row in mismatches.iterrows():
                        issues_report.append({
                            'Issue_Type': 'Attribution Mismatch',
                            'CellWorkItemID': row['CellWorkItemID'],
                            'CellName': row[dmd_col] if col != 'CellName' else row[dmd_col],
                            'Attribute': col,
                            'Expected_Value': row[dmd_col],
                            'Actual_Value': row[gao_col],
                            'Details': f'{col} differs: Expected="{row[dmd_col]}", Got="{row[gao_col]}"'
                        })
        
        results['Attribution_Issues_Count'] = attr_issues_count
        print(f"Total attribution issues: {attr_issues_count}")
        
        # ============ 3. COMPARE GEOMETRY ============
        print("\n=== Checking geometry differences ===")
        
        if gdf_qgis is not None and len(gdf_qgis) > 0:
            # Prepare QGIS data with standardized ID column
            gdf_qgis_geom = gdf_qgis.copy()
            if 'DMD_ID' in gdf_qgis_geom.columns:
                gdf_qgis_geom = gdf_qgis_geom.rename(columns={"DMD_ID": "CellWorkItemID"})
            
            # Ensure both GeoDataFrames have the same CRS
            if gdf_GaO.crs != gdf_qgis_geom.crs:
                print(f"  Reprojecting QGIS data from {gdf_qgis_geom.crs} to {gdf_GaO.crs}")
                gdf_qgis_geom = gdf_qgis_geom.to_crs(gdf_GaO.crs)
            
            # Match records by CellWorkItemID
            geom_issues_count = 0
            
            for idx, qgis_row in gdf_qgis_geom.iterrows():
                qgis_id = qgis_row.get('CellWorkItemID')
                
                if pd.isna(qgis_id):
                    continue
                
                # Find matching record in GaO
                gao_match = gdf_GaO[gdf_GaO['CellWorkItemID'] == qgis_id]
                
                if len(gao_match) == 0:
                    continue
                
                gao_geom = gao_match.iloc[0]['geometry']
                qgis_geom = qgis_row['geometry']
                
                # Check if geometries are valid
                if not qgis_geom.is_valid:
                    qgis_geom = qgis_geom.buffer(0)
                if not gao_geom.is_valid:
                    gao_geom = gao_geom.buffer(0)
                
                # Compare geometries using various metrics
                area_diff = abs(gao_geom.area - qgis_geom.area)
                area_pct_diff = (area_diff / qgis_geom.area * 100) if qgis_geom.area > 0 else 0
                
                # Check if geometries are nearly equal (within tolerance)
                geoms_equal = gao_geom.equals(qgis_geom)
                geoms_almost_equal = gao_geom.equals_exact(qgis_geom, tolerance=0.01)
                
                # Calculate IoU (Intersection over Union)
                try:
                    intersection = gao_geom.intersection(qgis_geom).area
                    union = gao_geom.union(qgis_geom).area
                    iou = intersection / union if union > 0 else 0
                except:
                    iou = 0
                
                # Flag geometry issues
                if not geoms_almost_equal and (area_pct_diff > 1 or iou < 0.95):
                    geom_issues_count += 1
                    issues_report.append({
                        'Issue_Type': 'Geometry Mismatch',
                        'CellWorkItemID': qgis_id,
                        'CellName': gao_match.iloc[0].get('CellName', 'N/A'),
                        'Area_Difference': f"{area_diff:.2f}",
                        'Area_Pct_Difference': f"{area_pct_diff:.2f}%",
                        'IoU_Score': f"{iou:.4f}",
                        'Details': f"Geometry differs: Area diff={area_pct_diff:.2f}%, IoU={iou:.4f}"
                    })
            
            results['Geometry_Issues_Count'] = geom_issues_count
            print(f"Total geometry issues: {geom_issues_count}")
        else:
            print("  No QGIS data available for geometry comparison")
            results['Geometry_Issues_Count'] = 'N/A - No QGIS data'
        
        # ============ 4. GENERATE REPORTS ============
        print("\n=== Generating reports ===")
        
        # Convert issues to DataFrame
        if issues_report:
            issues_df = pd.DataFrame(issues_report)
            
            # Save detailed issues report
            issues_file = f"{output_dir}/DataReg_Issues_Report.csv"
            issues_df.to_csv(issues_file, index=False)
            print(f"Detailed issues report saved to: {issues_file}")
            
            # Create summary by issue type
            summary = issues_df.groupby('Issue_Type').size()
            print("\nIssues Summary:")
            print(summary)
        else:
            print("No issues found! All databases are in sync.")
        
        # Save summary results
        results_df = pd.DataFrame([results]).T
        results_df.columns = ['Result']
        results_df.index.name = 'Metric'
        results_file = f"{output_dir}/DataReg_Comparison_Summary.csv"
        results_df.to_csv(results_file)
        print(f"Summary results saved to: {results_file}")
        
        # Save comparison dataframes for reference
        df_DMD_comp.to_csv(f"{output_dir_2}/df_DMD_comparison.csv", index=False)
        gdf_GaO_comp.to_csv(f"{output_dir_2}/gdf_GaO_comparison.csv", index=False)

        if gdf_qgis is not None:

            gdf_qgis_comp = gdf_qgis_prep[['CellWorkItemID', 'CELLNAME', 'DATE_ADDED']].copy() if 'gdf_qgis_prep' in locals() else gdf_qgis.copy()
            # Rename DMD_ID to CellWorkItemID if it exists
            if 'DMD_ID' in gdf_qgis_comp.columns:
                gdf_qgis_comp = gdf_qgis_comp.rename(columns={"DMD_ID": "CellWorkItemID"})

            # Drop geometry column for CSV
            if 'geometry' in gdf_qgis_comp.columns:
                gdf_qgis_comp = gdf_qgis_comp.drop(columns=['geometry'])

            gdf_qgis_comp.to_csv(f"{output_dir_2}/gdf_QGIS_comparison.csv", index=False)
        
        return results, issues_df if issues_report else None, output_dir
    
    else:
        print("No Data Loaded")
        return None, None







def compare_overlaps_databases(gdf_qgis, gdf_GaO, df_DMD, timestamp, output_dir, output_dir_2):
    """
    Compare QGIS and GaO overlap databases and generate detailed report
    
    Parameters:
    -----------
    gdf_qgis : GeoDataFrame
        QGIS shapefile data (POTENTIAL_OVERLAPS.shp)
    gdf_GaO : GeoDataFrame
        GaO database overlaps data
    df_DMD : DataFrame
        DMD data for filtering
    timestamp : str
        Timestamp for file naming
    output_dir : str
        Primary output directory
    output_dir_2 : str
        Secondary output directory
    
    Returns:
    --------
    tuple : (results_dict, issues_dataframe, output_directory)
    """
    
    print("\n" + "="*50)
    print("Beginning Comparison of Overlaps: QGIS vs GaO Beta")
    print("="*50 + "\n")
    
    # Initialize results and issues tracking
    results = {}
    issues_report = []
    
    # ============ DATA PREPARATION ============
    print("=== Preparing data ===")
    
    gdf_qgis_prep = gdf_qgis.copy()
    gdf_GaO_prep = gdf_GaO.copy()
    
    # Create OverlapID for matching (more specific than NAMEJOIN)
    gdf_qgis_prep['OverlapID'] = (gdf_qgis_prep['CellWorkItemID_1'].astype(str) + '_' +
                                   gdf_qgis_prep['CellName_1'].astype(str) + '_' + 
                                   gdf_qgis_prep['Edition_1'].astype(str) + '_' + 
                                   gdf_qgis_prep['CellName_2'].astype(str) + '_' + 
                                   gdf_qgis_prep['Edition_2'].astype(str))
    gdf_GaO_prep['OverlapID'] = (gdf_GaO_prep['CellWorkItemID_1'].astype(str) + '_' +
                                  gdf_GaO_prep['CellName_1'].astype(str) + '_' + 
                                  gdf_GaO_prep['Edition_1'].astype(str) + '_' + 
                                  gdf_GaO_prep['CellName_2'].astype(str) + '_' + 
                                  gdf_GaO_prep['Edition_2'].astype(str))
    
    # Filter to autoclassified records in QGIS (REP_RECOM = "NO ACTION")
    if 'REP_RECOM' in gdf_qgis_prep.columns:
        gdf_qgis_auto = gdf_qgis_prep[gdf_qgis_prep['REP_RECOM'] == 'NO ACTION'].copy()
        print(f"QGIS autoclassified records (REP_RECOM='NO ACTION'): {len(gdf_qgis_auto)}")
    else:
        gdf_qgis_auto = gdf_qgis_prep.copy()
        print(f"Warning: REP_RECOM column not found, using all QGIS records: {len(gdf_qgis_auto)}")
    
    # All GaO records are autoclassified
    print(f"GaO records (all autoclassified): {len(gdf_GaO_prep)}")
    
    # Record counts
    results['Total_QGIS_Overlaps'] = len(gdf_qgis_prep)
    results['QGIS_Autoclassified_Overlaps'] = len(gdf_qgis_auto)
    results['GaO_Overlaps'] = len(gdf_GaO_prep)
    
    print(f"\nTotal overlaps in QGIS: {len(gdf_qgis_prep)}")
    print(f"Autoclassified overlaps in QGIS: {len(gdf_qgis_auto)}")
    print(f"Total overlaps in GaO: {len(gdf_GaO_prep)}")
    
    # ============ 1. CHECK FOR MISSING/EXTRA RECORDS ============
    print("\n=== Checking for missing/extra overlap records ===")
    
    qgis_overlapids = set(gdf_qgis_auto['OverlapID'].values)
    gao_overlapids = set(gdf_GaO_prep['OverlapID'].values)
    
    missing_in_gao = qgis_overlapids - gao_overlapids
    extra_in_gao = gao_overlapids - qgis_overlapids
    
    if missing_in_gao:
        print(f"WARNING: {len(missing_in_gao)} overlap records missing in GaO")
        results['Missing_in_GaO_Count'] = len(missing_in_gao)
        for missing_id in missing_in_gao:
            #missing_row = gdf_qgis_auto[gdf_qgis_auto['OverlapID'] == missing_id].iloc[0]

            
            subset = gdf_qgis_auto[gdf_qgis_auto['OverlapID'] == missing_id]
            if subset.empty:
                issues_report.append({
                    'Issue_Type': 'Missing in GaO',
                    'OverlapID': missing_id,
                    'CellName_1': 'N/A',
                    'Edition_1': 'N/A',
                    'CellName_2': 'N/A',
                    'Edition_2': 'N/A',
                    'Expected_OverlapStatus': 'N/A',
                    'Actual_Value': 'MISSING',
                    'Details': 'OverlapID missing in QGIS autoclassified subset'
                })
                continue

            missing_row = subset.iloc[0]

            issues_report.append({
                'Issue_Type': 'Missing in GaO',
                'OverlapID': missing_id,
                'CellName_1': missing_row.get('CellName_1', 'N/A'),
                'Edition_1': missing_row.get('Edition_1', 'N/A'),
                'CellName_2': missing_row.get('CellName_2', 'N/A'),
                'Edition_2': missing_row.get('Edition_2', 'N/A'),
                'Expected_OverlapStatus': missing_row.get('OverlapStatus', 'N/A'),
                'Actual_Value': 'MISSING',
                'Details': 'Overlap exists in QGIS but not in GaO'
            })
    else:
        results['Missing_in_GaO_Count'] = 0
    
    if extra_in_gao:
        print(f"WARNING: {len(extra_in_gao)} extra overlap records in GaO")
        results['Extra_in_GaO_Count'] = len(extra_in_gao)
        for extra_id in extra_in_gao:
            extra_row = gdf_GaO_prep[gdf_GaO_prep['OverlapID'] == extra_id].iloc[0]
            issues_report.append({
                'Issue_Type': 'Extra in GaO',
                'OverlapID': extra_id,
                'CellName_1': extra_row.get('CellName_1', 'N/A'),
                'Edition_1': extra_row.get('Edition_1', 'N/A'),
                'CellName_2': extra_row.get('CellName_2', 'N/A'),
                'Edition_2': extra_row.get('Edition_2', 'N/A'),
                'Expected_OverlapStatus': 'N/A',
                'Actual_Value': extra_row.get('OverlapStatus', 'N/A'),
                'Details': 'Overlap exists in GaO but not in QGIS'
            })
    else:
        results['Extra_in_GaO_Count'] = 0
    
    # ============ 2. COMPARE OVERLAP CLASSIFICATION (OverlapStatus) ============
    print("\n=== Comparing OverlapStatus classification ===")
    
    # Merge on OverlapID to compare matching records
    merged = pd.merge(
        gdf_qgis_auto[['OverlapID', 'OverlapStatus', 'CellName_1', 'Edition_1', 'CellName_2', 'Edition_2']],
        gdf_GaO_prep[['OverlapID', 'OverlapStatus', 'CellName_1', 'Edition_1', 'CellName_2', 'Edition_2']],
        on='OverlapID',
        how='inner',
        suffixes=('_QGIS', '_GaO')
    )
    
    results['Matched_Overlaps'] = len(merged)
    print(f"Matched overlaps for comparison: {len(merged)}")
    
    # Filter out OverlapStatuses that are allowed to be different
    qgis_statuses_to_exclude = ['POTENTIAL', 'CANCEL/REPLACEMENT', 'CLIPPED/ADDITIONAL']
    merged_filtered = merged[~merged['OverlapStatus_QGIS'].isin(qgis_statuses_to_exclude)].copy()
    
    excluded_count = len(merged) - len(merged_filtered)
    if excluded_count > 0:
        print(f"Excluded {excluded_count} records with QGIS OverlapStatus: {', '.join(qgis_statuses_to_exclude)}")
    
    # Standardize OverlapStatus values for comparison
    print("Standardizing OverlapStatus values...")
    overlap_status_mapping = {
        'POTENTIAL - 1M ACCEPT': 'POTENTIAL - ACCEPT <1m',
        'POTENTIAL - 5M ACCEPT': 'POTENTIAL - ACCEPT <5m'
    }
    
    merged_filtered['OverlapStatus_QGIS_Standardized'] = merged_filtered['OverlapStatus_QGIS'].replace(overlap_status_mapping)
    
    # Compare OverlapStatus after filtering and standardization
    status_mismatches = merged_filtered[
        merged_filtered['OverlapStatus_QGIS_Standardized'] != merged_filtered['OverlapStatus_GaO']
    ]
    
    if len(status_mismatches) > 0:
        print(f"WARNING: {len(status_mismatches)} OverlapStatus mismatches found (after filtering and standardization)")
        results['OverlapStatus_Mismatches'] = len(status_mismatches)
        results['OverlapStatus_Excluded_From_Comparison'] = excluded_count
        
        for idx, row in status_mismatches.iterrows():
            issues_report.append({
                'Issue_Type': 'OverlapStatus Mismatch',
                'OverlapID': row['OverlapID'],
                'CellName_1': row['CellName_1_QGIS'],
                'Edition_1': row['Edition_1_QGIS'],
                'CellName_2': row['CellName_2_QGIS'],
                'Edition_2': row['Edition_2_QGIS'],
                'Attribute': 'OverlapStatus',
                'Expected_Value': row['OverlapStatus_QGIS_Standardized'],
                'Actual_Value': row['OverlapStatus_GaO'],
                'Details': f'OverlapStatus differs: Expected="{row["OverlapStatus_QGIS_Standardized"]}" (original: "{row["OverlapStatus_QGIS"]}"), Got="{row["OverlapStatus_GaO"]}"'
            })
    else:
        results['OverlapStatus_Mismatches'] = 0
        results['OverlapStatus_Excluded_From_Comparison'] = excluded_count
        print("All OverlapStatus values match (after filtering and standardization)!")
    
    # ============ 3. COMPARE ATTRIBUTION ============
    print("\n=== Comparing attribution of overlaps ===")
    
    # Determine common columns for comparison (excluding geometry and system columns)
    exclude_cols = ['geometry', 'OverlapID', 'OverlapStatus']
    qgis_cols = set(gdf_qgis_auto.columns) - set(exclude_cols)
    gao_cols = set(gdf_GaO_prep.columns) - set(exclude_cols)
    common_cols = list(qgis_cols.intersection(gao_cols))
    
    print(f"Comparing {len(common_cols)} common attributes")
    
    # ============ DYNAMICALLY STANDARDIZE DATA TYPES ============
    print("\n=== Standardizing data types ===")
    
    for col in common_cols:
        if col in gdf_qgis_auto.columns and col in gdf_GaO_prep.columns:
            qgis_dtype = gdf_qgis_auto[col].dtype
            gao_dtype = gdf_GaO_prep[col].dtype
            
            # Check if column contains numeric data
            if pd.api.types.is_numeric_dtype(qgis_dtype) or pd.api.types.is_numeric_dtype(gao_dtype):
                # Try to convert both to numeric
                gdf_qgis_auto[col] = pd.to_numeric(gdf_qgis_auto[col], errors='coerce')
                gdf_GaO_prep[col] = pd.to_numeric(gdf_GaO_prep[col], errors='coerce')
                print(f"  {col}: Standardized to numeric")
            
            # Check if column contains datetime data
            elif pd.api.types.is_datetime64_any_dtype(qgis_dtype) or pd.api.types.is_datetime64_any_dtype(gao_dtype):
                # Try to convert both to datetime
                gdf_qgis_auto[col] = pd.to_datetime(gdf_qgis_auto[col], errors='coerce')
                gdf_GaO_prep[col] = pd.to_datetime(gdf_GaO_prep[col], errors='coerce')
                print(f"  {col}: Standardized to datetime")
            
            else:
                # Convert to string and strip whitespace for text fields
                gdf_qgis_auto[col] = gdf_qgis_auto[col].astype(str).str.strip().str.upper()
                gdf_GaO_prep[col] = gdf_GaO_prep[col].astype(str).str.strip().str.upper()
                print(f"  {col}: Standardized to string (uppercase, trimmed)")
    
    # ============ COMPARE ATTRIBUTES AFTER STANDARDIZATION ============
    attr_issues_count = 0
    
    for col in common_cols:
        # Create a merged dataframe for this specific column
        col_merged = pd.merge(
            gdf_qgis_auto[['OverlapID', col]],
            gdf_GaO_prep[['OverlapID', col]],
            on='OverlapID',
            how='inner',
            suffixes=('_QGIS', '_GaO')
        )
        
        # Find mismatches (handling NaN values)
        qgis_col = f"{col}_QGIS"
        gao_col = f"{col}_GaO"
        
        # Compare, treating NaN as equal
        mismatches = col_merged[
            (col_merged[qgis_col] != col_merged[gao_col]) &
            ~(col_merged[qgis_col].isna() & col_merged[gao_col].isna())
        ]
        
        if len(mismatches) > 0:
            attr_issues_count += len(mismatches)
            print(f"  {col}: {len(mismatches)} mismatches found")
            
            for idx, row in mismatches.iterrows():
                issues_report.append({
                    'Issue_Type': 'Attribution Mismatch',
                    'OverlapID': row['OverlapID'],
                    'Attribute': col,
                    'Expected_Value': row[qgis_col],
                    'Actual_Value': row[gao_col],
                    'Details': f'{col} differs: Expected="{row[qgis_col]}", Got="{row[gao_col]}"'
                })
    
    results['Attribution_Issues_Count'] = attr_issues_count
    print(f"Total attribution issues: {attr_issues_count}")
    
    # ============ 4. COMPARE GEOMETRY ============
    print("\n=== Comparing geometry of overlaps ===")
    
    # Ensure both GeoDataFrames have the same CRS
    if gdf_GaO_prep.crs != gdf_qgis_auto.crs:
        print(f"  Reprojecting QGIS data from {gdf_qgis_auto.crs} to {gdf_GaO_prep.crs}")
        gdf_qgis_auto = gdf_qgis_auto.to_crs(gdf_GaO_prep.crs)
    
    geom_issues_count = 0
    
    for idx, qgis_row in gdf_qgis_auto.iterrows():
        overlapid = qgis_row['OverlapID']
        
        # Find matching record in GaO
        gao_match = gdf_GaO_prep[gdf_GaO_prep['OverlapID'] == overlapid]
        
        if len(gao_match) == 0:
            continue
        
        gao_geom = gao_match.iloc[0]['geometry']
        qgis_geom = qgis_row['geometry']
        
        # Check if geometries are valid
        if not qgis_geom.is_valid:
            qgis_geom = qgis_geom.buffer(0)
        if not gao_geom.is_valid:
            gao_geom = gao_geom.buffer(0)
        
        # Compare geometries using various metrics
        area_diff = abs(gao_geom.area - qgis_geom.area)
        area_pct_diff = (area_diff / qgis_geom.area * 100) if qgis_geom.area > 0 else 0
        
        # Check if geometries are nearly equal (within tolerance)
        geoms_almost_equal = gao_geom.equals_exact(qgis_geom, tolerance=0.01)
        
        # Calculate IoU (Intersection over Union)
        try:
            intersection = gao_geom.intersection(qgis_geom).area
            union = gao_geom.union(qgis_geom).area
            iou = intersection / union if union > 0 else 0
        except Exception as e:
            iou = 0
        
        # Flag geometry issues (less than 95% IoU or >1% area difference)
        if not geoms_almost_equal and (area_pct_diff > 1 or iou < 0.95):
            geom_issues_count += 1
            issues_report.append({
                'Issue_Type': 'Geometry Mismatch',
                'OverlapID': overlapid,
                'CellName_1': qgis_row['CellName_1'],
                'Edition_1': qgis_row['Edition_1'],
                'CellName_2': qgis_row['CellName_2'],
                'Edition_2': qgis_row['Edition_2'],
                'Area_Difference': f"{area_diff:.2f}",
                'Area_Pct_Difference': f"{area_pct_diff:.2f}%",
                'IoU_Score': f"{iou:.4f}",
                'Details': f"Geometry differs: Area diff={area_pct_diff:.2f}%, IoU={iou:.4f}"
            })
    
    results['Geometry_Issues_Count'] = geom_issues_count
    print(f"Total geometry issues: {geom_issues_count}")
    
    # ============ 5. GENERATE REPORTS ============
    print("\n=== Generating reports ===")
    
    # Convert issues to DataFrame
    if issues_report:
        issues_df = pd.DataFrame(issues_report)
        
        # Save detailed issues report
        issues_file = f"{output_dir}/Overlaps_Issues_Report.csv"
        issues_df.to_csv(issues_file, index=False)
        print(f"Detailed issues report saved to: {issues_file}")
        
        # Create summary by issue type
        summary = issues_df.groupby('Issue_Type').size()
        print("\nIssues Summary:")
        print(summary)
    else:
        issues_df = pd.DataFrame()
    
    # Save overall results
    results_df = pd.DataFrame([results]).T
    results_df.columns = ['Count']
    results_df.index.name = 'Metric'
    results_file = f"{output_dir}/Overlaps_Comparison_Summary.csv"
    results_df.to_csv(results_file)
    print(f"Summary results saved to: {results_file}")
    
    # Save comparison dataframes for reference (without geometry)
    qgis_comp = gdf_qgis_auto.drop(columns=['geometry'], errors='ignore')
    gao_comp = gdf_GaO_prep.drop(columns=['geometry'], errors='ignore')
    
    qgis_comp.to_csv(f"{output_dir_2}/QGIS_overlaps_comparison_{timestamp}.csv", index=False)
    gao_comp.to_csv(f"{output_dir_2}/GaO_overlaps_comparison_{timestamp}.csv", index=False)
    print(f"Reference data saved to: {output_dir_2}")
    
    # Calculate and display overall match percentage
    if results['Matched_Overlaps'] > 0:
        total_issues = (results.get('Missing_in_GaO_Count', 0) + 
                       results.get('Extra_in_GaO_Count', 0) +
                       results.get('OverlapStatus_Mismatches', 0) +
                       results.get('Attribution_Issues_Count', 0) +
                       results.get('Geometry_Issues_Count', 0))
        
        match_rate = ((results['Matched_Overlaps'] - results.get('OverlapStatus_Mismatches', 0)) / 
                      results['Matched_Overlaps'] * 100)
        
        print(f"\n{'='*50}")
        print(f"Overall Match Rate (OverlapStatus): {match_rate:.2f}%")
        print(f"Total Issues Found: {total_issues}")
        print(f"{'='*50}\n")
    
    return results, issues_df, output_dir



## ---------- Validator functions ------------

def data_registration_validator(timestamp, output_dir, output_dir_2):

    ## -------Import Data----------

    ## ---------Query db set-up------------

    # Read database parameters
    config = configparser.ConfigParser()
    config.read("config.ini")

    server = config["database"]["server"]
    database = config["database"]["database"]
    username = config["database"]["username"]
    password = config["database"]["password"]


    # DMD dbo.CellWorkItems Connection
    driver = '{ODBC Driver 17 for SQL Server}'  # or 18 if installed

    DMDconnection_string = f'''
        DRIVER={driver};
        SERVER={server};
        DATABASE={database};
        UID={username};
        PWD={password};
        Encrypt=yes;
        TrustServerCertificate=no;
        Connection Timeout=30;
    '''


    # GapsAndOverlaps S57CellWorkItem Connection
    database = 'GapsAndOverlaps-UAT'

    GaOsconnection_string = f'''
        DRIVER={driver};
        SERVER={server};
        DATABASE={database};
        UID={username};
        PWD={password};
        Encrypt=yes;
        TrustServerCertificate=no;
        Connection Timeout=30;
    '''

    # SQL Query
    query_DMD = '''
    SELECT 
        [ID], 
        [Name], 
        [UsageBand], 
        [ModificationID], 
        [Scale], 
        [Edition], 
        [RegisteredAt] 
    FROM dbo.CellWorkItem 
    WHERE 
        ModificationID <> 3
    	AND CellStandardID = 1
        AND CAST(RegisteredAt AS DATE) >= CAST(DATEADD(DAY, -7, GETDATE()) AS DATE)
        AND CAST(RegisteredAt AS DATE) < CAST(GETDATE() AS DATE);

    '''
    query_GaO = """
    SELECT [ID]
      ,[CellWorkItemID]
      ,[CellName]
      ,[Scale]
      ,[UsageBand]
      ,[ModificationID]
      ,[Edition]
      ,[ValidationStatusID]
      ,[RegisteredAt]
      ,[OverlapsCreated]
      ,shape.STAsText() as geometry_wkt
	  ,shape.STSrid as srid
    FROM [dbo].[S57CellWorkItem]
    WHERE 
        CAST(RegisteredAt AS DATE) >= CAST(DATEADD(DAY, -7, GETDATE()) AS DATE)
        AND CAST(RegisteredAt AS DATE) < CAST(GETDATE() AS DATE);
    """

    
    # initialize dfs
    df_DMD = None
    df_GaO = None
    gdf_qgis = None

    
    # Connect to dbs
    try:
        # Establish SQL db connections for DMD and GaOs
        with pyodbc.connect(DMDconnection_string) as conn_DMD, \
            pyodbc.connect(GaOsconnection_string) as conn_GaO:

            #query and Read to Dataframes
            df_DMD = pd.read_sql(query_DMD, conn_DMD)
            df_GaO = pd.read_sql(query_GaO, conn_GaO)

            # convert wkt shapely object
            df_GaO['geometry'] = df_GaO['geometry_wkt'].apply(wkt.loads)

            # Get the SRID from the first row
            if 'srid' in df_GaO.columns and not df_GaO.empty:
                srid = df_GaO['srid'].iloc[0]
                # print(f"Detected SRID: {srid}")
            else:
                srid = None
                print("Warning: SRID not found in data")
                raise("df_GaO is empty")
            
            # Drop unnecessary columns
            df_GaO = df_GaO.drop(columns=['geometry_wkt', 'shape', 'srid'], errors='ignore')
            
            # Create GeoDataFrame
            gdf_GaO = gpd.GeoDataFrame(df_GaO, geometry='geometry')

            # Set CRS based on SRID from SQL Server
            if srid:
                try:
                    gdf_GaO.set_crs(epsg=srid, inplace=True)
                    # print(f"CRS set to EPSG:{srid}")
                except Exception as e:
                    print(f"Could not set CRS for EPSG:{srid} - {e}")
                    print("You may need to set it manually")
            else:
                print("WARNING: No CRS set. Set it manually if you know the coordinate system:")

            # Redefine geometry from geometry collection to mulipolygon
            gdf_GaO['geometry'] = gdf_GaO['geometry'].apply(geometry_collection_to_multipolygon)

            
            print("Read completed")

    except Exception as e:
        raise("Connection failed:", e)
    


    ## ------------Load Live process shapefiles (QGIS)----------------

    pathQgisInputArchive = r"V:\MANAGEMENT\IC-ENC Graphical Catalogue\In work\Model Inputs\INPUT_ARCHIVE.shp"

    gdf_qgis = gpd.read_file(pathQgisInputArchive)


    ##---------Compare Datasets-----------------

    # Perform comparison
    results, issues_df, output_dir = compare_databases(df_DMD, gdf_GaO, gdf_qgis, timestamp, output_dir, output_dir_2)
    
    ## -------------------Save outputs for testing - enable if required-------------------------
    #gdf_qgis.to_file(f"{output_dir}/gdf_qgis.shp", driver="ESRI Shapefile")
    #df_DMD.to_csv(f"{output_dir}/df_DMD.csv", index=False)
    #gdf_GaO.to_file(f"{output_dir}/gdf_GaO.shp", driver="ESRI Shapefile")
    


def potential_overlap_validator(timestamp, output_dir, output_dir_2, start_datetime=None, end_datetime=None):
    """
    Validates potential overlaps. Optional start/end datetime arguments override
    the default 7 day lookback period for SQL queries.
    The custom date range behaves exactly like the default:
        - Start date inclusive
        - End date exclusive
        - Whole-day comparison using CAST(... AS DATE)
    """

    ## -------Import Data----------

    # ---------Query db set-up------------

    # Read database parameters
    config = configparser.ConfigParser()
    config.read("config.ini")

    server = config["database"]["server"]
    database = config["database"]["database"]
    username = config["database"]["username"]
    password = config["database"]["password"]
    driver = '{ODBC Driver 17 for SQL Server}'

    # DMD SQL connection string
    DMDconnection_string = f'''
        DRIVER={driver};
        SERVER={server};
        DATABASE={database};
        UID={username};
        PWD={password};
        Encrypt=yes;
        TrustServerCertificate=no;
        Connection Timeout=30;
    '''

    # Switch to GaO database
    database = 'GapsAndOverlaps-UAT'

    # GaOs SQL connection string
    GaOsconnection_string = f'''
        DRIVER={driver};
        SERVER={server};
        DATABASE={database};
        UID={username};
        PWD={password};
        Encrypt=yes;
        TrustServerCertificate=no;
        Connection Timeout=30;
    '''

    # ----- DATE FILTER BUILDER -----
    # SAME behaviour as the default 7-day logic:
    # Start = inclusive, End = exclusive, whole-day comparison
    if start_datetime is not None and end_datetime is not None:
        date_filter = f"""
            AND CAST(RegisteredAt AS DATE) >= CAST('{start_datetime}' AS DATE)
            AND CAST(RegisteredAt AS DATE) < CAST('{end_datetime}' AS DATE)
        """
    else:
        date_filter = """
            AND CAST(RegisteredAt AS DATE) >= CAST(DATEADD(DAY, -7, GETDATE()) AS DATE)
            AND CAST(RegisteredAt AS DATE) < CAST(GETDATE() AS DATE)
        """

    # SQL Query — DMD
    query_DMD = f'''
    SELECT 
        [ID], 
        [Name], 
        [UsageBand], 
        [ModificationID], 
        [Scale], 
        [Edition], 
        [RegisteredAt] 
    FROM dbo.CellWorkItem 
    WHERE 
        ModificationID <> 3
        AND CellStandardID = 1
        {date_filter};
    '''

    # SQL Query — GaO
    query_GaO = """
    SELECT [ID]
        ,[CellWorkItemID_1]
        ,[CellName_1]
        ,[Scale_1]
        ,[UsageBand_1]
        ,[ModificationID_1]
        ,[Edition_1]
        ,[CellWorkItemID_2]
        ,[CellName_2]
        ,[Scale_2]
        ,[UsageBand_2]
        ,[ModificationID_2]
        ,[Edition_2]
        ,[NameJoin]
        ,[OverlapID]
        ,[OverlapStatus]
        ,[Comments]
        ,shape.STAsText() as geometry_wkt
        ,shape.STSrid as srid
    FROM [GapsAndOverlaps-UAT].[dbo].[S57Overlaps]
    """

    # initialise dfs
    df_DMD = None
    df_GaO = None
    gdf_qgis = None

    # read QGIS shapefile
    gdf_qgis = gpd.read_file(
        r"V:\MANAGEMENT\IC-ENC Graphical Catalogue\In work\Model Inputs\POTENTIAL_OVERLAPS.shp"
    )

    # Connect to dbs
    try:
        with pyodbc.connect(DMDconnection_string) as conn_DMD, \
             pyodbc.connect(GaOsconnection_string) as conn_GaO:

            df_DMD = pd.read_sql(query_DMD, conn_DMD)
            df_GaO = pd.read_sql(query_GaO, conn_GaO)

            # convert wkt to geometry
            df_GaO['geometry'] = df_GaO['geometry_wkt'].apply(wkt.loads)

            # detect SRID
            if 'srid' in df_GaO.columns and not df_GaO.empty:
                srid = df_GaO['srid'].iloc[0]
            else:
                raise Exception("df_GaO is empty or missing SRID")

            # Clean GaO table
            df_GaO = df_GaO.drop(columns=['geometry_wkt', 'shape', 'srid'], errors='ignore')

            gdf_GaO = gpd.GeoDataFrame(df_GaO, geometry='geometry')

            # Set CRS
            try:
                gdf_GaO.set_crs(epsg=srid, inplace=True)
            except Exception as e:
                print(f"Could not set CRS for EPSG:{srid} - {e}")

            # convert geometry collections to multipolygons
            gdf_GaO['geometry'] = gdf_GaO['geometry'].apply(
                geometry_collection_to_multipolygon
            )

            print("Read completed")

    except Exception as e:
        raise Exception("Connection failed:", e)

    # Filter GaO/QGIS to only overlap DMD IDs
    gdf_GaO = gdf_GaO[gdf_GaO['CellWorkItemID_1'].isin(df_DMD['ID'])]
    gdf_qgis = gdf_qgis[gdf_qgis['DMD_ID'].isin(df_DMD['ID'])]

    # Data cleaning — QGIS
    qgis_rename = {
        'DMD_ID': 'CellWorkItemID_1',
        'CELLNAME': 'CellName_1',
        'ED_NO': 'Edition_1',
        'SCALE': 'Scale_1',
        'CELLNAME_2': 'CellName_2',
        'SCALE_2': 'Scale_2',
        'DMD_ID_2': 'CellWorkItem_2',
        'ED_NO_2': 'Edition_2',
        'MODIFIC': 'ModificationID_1',
        'MODIFIC_2': 'ModificationID_2',
        'STATUS': 'OverlapStatus',
        'NAV_BAND': 'UsageBand_1',
        'NAV_BAND_2': 'UsageBand_2'
    }

    qgis_drop = [
        'layer', 'OVAREA', 'NAMEJOIN', 'area', 'perimeter', 'RES_DATE',
        'NEW_SUM__1', 'SUM_STATUS'
    ]

    gdf_qgis = gdf_qgis.rename(columns=qgis_rename)
    gdf_qgis = gdf_qgis.drop(columns=qgis_drop)

    # Clean GaO
    gdf_GaO = gdf_GaO.drop(columns=['NameJoin', 'OverlapID', 'Comments'])

    # Map UsageBands
    navbandMapping = {
        '1': 'OVERVIEW',
        '2': 'GENERAL',
        '3': 'COASTAL',
        '4': 'APPROACHES',
        '5': 'HARBOUR',
        '6': 'BERTHING'
    }

    gdf_qgis['UsageBand_1'] = gdf_qgis['UsageBand_1'].astype(str).map(navbandMapping)
    gdf_qgis['UsageBand_2'] = gdf_qgis['UsageBand_2'].astype(str).map(navbandMapping)

    # Run comparison
    results, issues_df, output_dir = compare_overlaps_databases(
        gdf_qgis=gdf_qgis,
        gdf_GaO=gdf_GaO,
        df_DMD=df_DMD,
        timestamp=timestamp,
        output_dir=output_dir,
        output_dir_2=output_dir_2
    )

    return results, issues_df, output_dir




def main(timestamp, output_dir, output_dir_2):

    print("\n===========Data Registration Analysis===========")
    data_registration_validator(timestamp, output_dir, output_dir_2)
    print("\n===========Potential Overlap Analysis===========")
    potential_overlap_validator(timestamp, output_dir, output_dir_2)



if __name__ == "__main__":

    # Create timestamped output directory
    timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    output_dir = f"output/GaO_Beta_Dual_Test_{timestamp}"
    
    os.makedirs(output_dir, exist_ok=True)
    print(f"Output directory created: {output_dir}\n")

    output_dir_2 = f"{output_dir}/comparisons" 
    os.makedirs(output_dir_2, exist_ok=True)

    main(timestamp, output_dir, output_dir_2)
    print("\n" + "="*50)
    print("Script Completed: please continue with Working Practice")
    print("="*50)

# end of script